# app.py - application factory and blueprint registration
from flask import Flask, render_template
from config import Config

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # register blueprints
    from routes.main_routes import main_bp
    from routes.quiz_routes import quiz_bp
    from routes.result_routes import result_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(result_bp)

    # error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    # Listen on all interfaces (0.0.0.0) so Ngrok can access
    app.run(host="0.0.0.0", port=5000, debug=True)

