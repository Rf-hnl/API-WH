# blueprints/api/routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import re
import uuid # Import the uuid module
from db import query_db, get_db_connection

api_bp = Blueprint('api_bp', __name__)

def is_valid_uuid(uuid_string):
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

@api_bp.route('/send_whatsapp', methods=['POST'])
# @jwt_required() # Descomentar para habilitar autenticación
def send_whatsapp_message():
    """
    Envía un mensaje de WhatsApp.
    """
    # current_tenant_id = get_jwt_identity() # Usar cuando la autenticación esté activa
    
    # Para propósitos de prueba sin autenticación, usar un tenant_id fijo o el primero disponible
    # En un entorno real, el tenant_id vendría de la sesión o token JWT
    tenant_id_from_header = request.headers.get('X-Tenant-ID')
    current_tenant_id = None

    if tenant_id_from_header and is_valid_uuid(tenant_id_from_header):
        current_tenant_id = tenant_id_from_header
    else:
        # Fallback para desarrollo: usar el primer tenant si no se proporciona X-Tenant-ID o es inválido
        first_tenant = query_db('SELECT id FROM tenants LIMIT 1', one=True)
        if first_tenant:
            current_tenant_id = first_tenant['id']
        else:
            return jsonify({"error": "No hay tenants configurados. Por favor, cree uno primero."}), 400

    # Obtener credenciales del tenant desde la base de datos
    tenant = query_db('SELECT * FROM tenants WHERE id = %s', [current_tenant_id], one=True)
    if not tenant:
        return jsonify({"error": "Tenant no encontrado"}), 404

    data = request.get_json()
    to_number = data.get('to_number')
    message_body = data.get('message_body')

    if not to_number or not message_body:
        return jsonify({"error": "Faltan los campos 'to_number' o 'message_body'"}), 400

    # Validar el formato del número de teléfono (E.164)
    if not re.match(r'^\+?[1-9]\d{1,14}$', to_number):
        return jsonify({"error": "Formato de número de teléfono inválido. Debe estar en formato E.164."}), 400

    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_whatsapp_number = tenant['twilio_whatsapp_number']

        if not account_sid or not auth_token or not twilio_whatsapp_number:
            return jsonify({"error": "Credenciales de Twilio o número de WhatsApp del tenant no configurados."}), 500

        client = Client(account_sid, auth_token)
        
        # Ensure 'to_number' has the 'whatsapp:' prefix for Twilio
        if not to_number.startswith('whatsapp:'):
            to_number = 'whatsapp:' + to_number

        message = client.messages.create(
            from_=twilio_whatsapp_number,
            to=to_number,
            body=message_body
        )

        # Guardar el mensaje en la base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO messages (tenant_id, message_sid, sender_type, body, to_number)
            VALUES (%s, %s, 'bot', %s, %s)
            """,
            (current_tenant_id, message.sid, message_body, to_number)
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "message_sid": message.sid}), 200

    except TwilioRestException as e:
        return jsonify({"error": f"Error de Twilio: {e.msg}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@api_bp.route('/messages', methods=['GET'])
@jwt_required()
def get_messages():
    """
    Obtiene el historial de mensajes para el tenant autenticado.
    """
    current_tenant_id = get_jwt_identity()
    messages = query_db('SELECT * FROM messages WHERE tenant_id = %s ORDER BY timestamp DESC', [current_tenant_id])
    return jsonify(messages)
