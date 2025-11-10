# app.py - Updated for Render deployment
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError, generate_csrf
from dotenv import load_dotenv
from config import Config, DB_PATH
from models import db, User
from pathlib import Path
from sqlalchemy import text, inspect
import logging
import os

# Import blueprints
from routes.main_routes import main_bp
from routes.quiz_routes import quiz_bp
from routes.result_routes import result_bp
from routes.auth_routes import auth_bp

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    # Use Session.get to avoid SQLAlchemy 2.x deprecation warnings
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

def create_app(test_config: dict | None = None):
    # Load environment variables from .env when running via python app.py
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates", 
                instance_path=Config.INSTANCE_PATH)
    app.config.from_object(Config)

    # Allow overriding config for testing
    if test_config:
        app.config.update(test_config)
        # Disable CSRF in tests to simplify form posting
        if app.config.get('TESTING'):
            app.config['WTF_CSRF_ENABLED'] = False

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    csrf = CSRFProtect(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Migration / schema safety:
    #  - For local SQLite: auto-create tables if missing.
    #  - For Postgres/other: if tables missing, attempt alembic upgrade once.
    with app.app_context():
        inspector = inspect(db.engine)
        uri = app.config['SQLALCHEMY_DATABASE_URI']
        has_user = inspector.has_table('user')
        has_score = inspector.has_table('score')

        if uri.startswith('sqlite:///'):
            if not (has_user and has_score):
                try:
                    db.create_all()
                    print("(Local) SQLite database initialized.")
                except Exception:
                    pass
        else:
            # Non-sqlite (likely Postgres). If tables missing, run alembic upgrade.
            if not (has_user and has_score):
                try:
                    from flask_migrate import upgrade
                    print("[migration-check] Detected missing tables; running alembic upgrade...")
                    upgrade()
                    # re-inspect after upgrade
                    inspector = inspect(db.engine)
                    if not (inspector.has_table('user') and inspector.has_table('score')):
                        raise RuntimeError("Migration upgrade ran but required tables still missing.")
                    print("[migration-check] Tables present after upgrade.")
                except Exception as e:
                    # Fail fast so 500 errors don't occur mid-request later
                    raise RuntimeError(f"Database schema incomplete and automatic migration failed: {e}")

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(auth_bp)

    # Inject csrf_token() helper for templates without FlaskForm
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Unhandled server error")
        return render_template("500.html"), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Prefer UX-friendly redirect with flash when possible
        try:
            flash('Your session expired or the form is invalid. Please try again.', 'error')
            return redirect(request.referrer or url_for('main.index'))
        except Exception:
            return render_template("500.html"), 400

    # Health check endpoint for uptime monitoring
    @app.route('/healthz', methods=['GET'])
    def healthz():
        import time as _t
        status = {"status": "ok", "db": False}
        # Try up to 2 short attempts in case of transient SSL/idle connection issues
        attempts = 2
        for i in range(attempts):
            try:
                db.session.execute(text("SELECT 1"))
                status["db"] = True
                break
            except Exception as e:
                # Log a concise warning for health check noise; full trace not needed each time
                app.logger.warning("healthz db ping failed (attempt %s/%s): %s", i+1, attempts, str(e))
                # brief backoff before the next attempt
                _t.sleep(0.4)
                try:
                    # dispose engine to force new connections in next attempt
                    db.engine.dispose()
                except Exception:
                    pass
        # By default, return 200 with db=false for transient issues to avoid flapping
        # Set HEALTHZ_STRICT=1 to return 503 when db is unreachable
        strict = os.environ.get("HEALTHZ_STRICT", "0") == "1"
        code = 200 if (status["db"] or not strict) else 503
        return status, code

    # Basic security headers & proxy fix
    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        # Simple CSP (adjust as needed)
        resp.headers.setdefault('Content-Security-Policy', "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net https://cdn.jsdelivr.net/npm/bootstrap@5.3.0 'unsafe-inline'; script-src 'self' https://cdn.jsdelivr.net https://cdn.jsdelivr.net/npm/bootstrap@5.3.0 'unsafe-inline'; img-src 'self' data:;")
        return resp

    # Respect X-Forwarded-Proto for HTTPS redirects behind Render proxy
    @app.before_request
    def _detect_proxy_scheme():
        xf_proto = request.headers.get('X-Forwarded-Proto')
        if xf_proto:
            request.environ['wsgi.url_scheme'] = xf_proto

    # Basic logging configuration with LOG_LEVEL override
    log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
    level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    app.logger.info("startup log_level=%s db_url_scheme=%s", log_level_name, app.config['SQLALCHEMY_DATABASE_URI'].split(':')[0])

    return app

# 🔹 Create module-level app for Gunicorn
app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render assigns PORT dynamically
    # Never enable debug automatically in production. Use FLASK_DEBUG env var locally.
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
