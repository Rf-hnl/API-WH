# app.py

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from twilio.base.exceptions import TwilioRestException
import os
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from blueprints.auth.routes import auth_bp
from blueprints.api.routes import api_bp
from blueprints.frontend.routes import frontend_bp
from models import db # Import the db instance

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.environ.get('FLASK_SECRET_KEY')
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DIRECT_URL')
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # Suppress a warning

    # Initialize extensions
    jwt = JWTManager(app)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"]
    )
    db.init_app(app) # Initialize SQLAlchemy with the app

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(frontend_bp, url_prefix='/')

    # ==============================================================================
    # == Manejo de Errores
    # ==============================================================================

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "No encontrado"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Error interno del servidor"}), 500

    @app.errorhandler(TwilioRestException)
    def handle_twilio_error(error):
        return jsonify({"error": f"Error de Twilio: {error.msg}", "code": error.code}), 400

    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        return jsonify({"error": "Acceso no autorizado", "reason": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Token inválido", "details": str(error)}), 422

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
