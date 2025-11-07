# app.py - Updated for Render deployment
from flask import Flask, render_template
from config import Config

# Import blueprints
from routes.main_routes import main_bp
from routes.quiz_routes import quiz_bp
from routes.result_routes import result_bp

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(result_bp)

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
