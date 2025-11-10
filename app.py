# app.py - Updated for Render deployment
from flask import Flask, render_template
from flask_login import LoginManager
from config import Config, DB_PATH
from models import db, User
from pathlib import Path

# Import blueprints
from routes.main_routes import main_bp
from routes.quiz_routes import quiz_bp
from routes.result_routes import result_bp
from routes.auth_routes import auth_bp

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(test_config: dict | None = None):
    app = Flask(__name__, static_folder="static", template_folder="templates", 
                instance_path=Config.INSTANCE_PATH)
    app.config.from_object(Config)

    # Allow overriding config for testing
    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Create database tables only if database doesn't exist (for file DB)
    with app.app_context():
        if not Path(DB_PATH).exists():
            db.create_all()
            print("Database initialized successfully!")

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(auth_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    return app

# 🔹 Create module-level app for Gunicorn
app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render assigns PORT dynamically
    app.run(host="0.0.0.0", port=port, debug=True)
