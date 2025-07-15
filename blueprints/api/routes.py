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

        # Find or create conversation
        whatsapp_user_id_clean = to_number.replace('whatsapp:', '')
        
        cur.execute(
            """
            SELECT id FROM conversations
            WHERE tenant_id = %s AND whatsapp_user_id = %s
            """,
            (current_tenant_id, whatsapp_user_id_clean)
        )
        conversation = cur.fetchone()

        conversation_id = None
        if conversation:
            conversation_id = conversation['id']
            # Update last_message_at for existing conversation
            cur.execute(
                """
                UPDATE conversations
                SET last_message_at = NOW(), updated_at = NOW()
                WHERE id = %s
                """,
                (conversation_id,)
            )
        else:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO conversations (id, tenant_id, whatsapp_user_id, last_message_at, status)
                VALUES (%s, %s, %s, NOW(), 'open')
                """,
                (conversation_id, current_tenant_id, whatsapp_user_id_clean)
            )
        
        # Insert the message
        cur.execute(
            """
            INSERT INTO messages (id, conversation_id, tenant_id, message_sid, sender_type, body, timestamp, to_number)
            VALUES (%s, %s, %s, %s, 'bot', %s, NOW(), %s)
            """,
            (str(uuid.uuid4()), conversation_id, current_tenant_id, message.sid, message_body, to_number)
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "message_sid": message.sid}), 200

    except TwilioRestException as e:
        return jsonify({"error": f"Error de Twilio: {e.msg}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@api_bp.route('/create_tenant', methods=['POST'])
def create_tenant():
    data = request.get_json()
    name = data.get('name')
    username = data.get('username')
    password = data.get('password')
    twilio_whatsapp_number = data.get('twilio_whatsapp_number')
    api_key = data.get('api_key')

    if not all([name, username, password, twilio_whatsapp_number, api_key]):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    hashed_password = generate_password_hash(password)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tenants (id, name, username, password, twilio_whatsapp_number, api_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), name, username, hashed_password, twilio_whatsapp_number, api_key)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "Tenant creado exitosamente"}), 201
    except psycopg2.IntegrityError as e:
        if "duplicate key value violates unique constraint" in str(e):
            return jsonify({"error": "El nombre de usuario o número de WhatsApp ya existe."}), 409
        return jsonify({"error": f"Error de base de datos: {str(e)}"}), 500
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
