# blueprints/auth/routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash
from db import query_db

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Autentica a un tenant y devuelve un token JWT.
    """
    data = request.get_json()
    username = data.get('username', None)
    password = data.get('password', None)

    if not username or not password:
        return jsonify({"error": "Faltan el nombre de usuario o la contraseña"}), 400

    tenant = query_db('SELECT * FROM tenants WHERE username = %s', [username], one=True)

    if not tenant or not check_password_hash(tenant['password'], password):
        return jsonify({"error": "Nombre de usuario o contraseña incorrectos"}), 401

    # El 'identity' del token será el UUID del tenant
    access_token = create_access_token(identity=str(tenant['id']))
    return jsonify(access_token=access_token)
