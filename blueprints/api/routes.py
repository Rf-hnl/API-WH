# blueprints/api/routes.py

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from flask_restx import Api, Resource, fields, Namespace
import re
import uuid
import psycopg2
from db import query_db, get_db_connection

api_bp = Blueprint('api_bp', __name__)

# Initialize Flask-RESTx
api = Api(api_bp, 
    title='WhatsApp Bot API',
    version='1.0',
    description='API para el Bot de WhatsApp multi-tenant con Twilio',
    doc='/docs/',
    prefix='/api'
)

# Namespaces
whatsapp_ns = Namespace('whatsapp', description='Operaciones de WhatsApp')
tenants_ns = Namespace('tenants', description='Gestión de inquilinos')
messages_ns = Namespace('messages', description='Historial de mensajes')

api.add_namespace(whatsapp_ns)
api.add_namespace(tenants_ns)
api.add_namespace(messages_ns)

def is_valid_uuid(uuid_string):
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

# Swagger Models
whatsapp_message_model = api.model('WhatsAppMessage', {
    'to_number': fields.String(required=True, description='Número de teléfono destino en formato E.164', example='+50763116918'),
    'message_body': fields.String(required=True, description='Contenido del mensaje', example='Hola, este es un mensaje de prueba')
})

tenant_model = api.model('Tenant', {
    'name': fields.String(required=True, description='Nombre del inquilino', example='Mi Empresa'),
    'twilio_account_sid': fields.String(required=True, description='Account SID de Twilio', example='ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    'twilio_auth_token': fields.String(required=True, description='Token de autenticación de Twilio'),
    'twilio_whatsapp_number': fields.String(required=True, description='Número de WhatsApp de Twilio', example='whatsapp:+17869461491')
})

tenant_response_model = api.model('TenantResponse', {
    'id': fields.String(description='ID único del inquilino'),
    'name': fields.String(description='Nombre del inquilino'),
    'twilio_account_sid': fields.String(description='Account SID de Twilio'),
    'twilio_auth_token': fields.String(description='Token de autenticación de Twilio'),
    'twilio_whatsapp_number': fields.String(description='Número de WhatsApp de Twilio'),
    'api_key': fields.String(description='Clave API (igual al ID del inquilino)'),
    'created_at': fields.DateTime(description='Fecha de creación'),
    'updated_at': fields.DateTime(description='Fecha de última actualización')
})

tenant_create_response_model = api.model('TenantCreateResponse', {
    'success': fields.Boolean(description='Indica si la operación fue exitosa'),
    'message': fields.String(description='Mensaje de confirmación'),
    'tenant_id': fields.String(description='ID del inquilino creado'),
    'api_key': fields.String(description='Clave API generada')
})

message_response_model = api.model('MessageResponse', {
    'success': fields.Boolean(description='Indica si el mensaje fue enviado exitosamente'),
    'message_sid': fields.String(description='SID del mensaje de Twilio')
})

message_model = api.model('Message', {
    'id': fields.String(description='ID del mensaje'),
    'conversation_id': fields.String(description='ID de la conversación'),
    'tenant_id': fields.String(description='ID del inquilino'),
    'message_sid': fields.String(description='SID del mensaje de Twilio'),
    'sender_type': fields.String(description='Tipo de remitente (user/bot)'),
    'body': fields.String(description='Contenido del mensaje'),
    'to_number': fields.String(description='Número de teléfono destino'),
    'media_url': fields.String(description='URL de medios adjuntos'),
    'timestamp': fields.DateTime(description='Fecha y hora del mensaje'),
    'created_at': fields.DateTime(description='Fecha de creación'),
    'updated_at': fields.DateTime(description='Fecha de actualización')
})

error_model = api.model('Error', {
    'error': fields.String(description='Descripción del error')
})

success_model = api.model('Success', {
    'success': fields.Boolean(description='Indica si la operación fue exitosa'),
    'message': fields.String(description='Mensaje de confirmación')
})

@whatsapp_ns.route('/send')
class SendWhatsAppMessage(Resource):
    @whatsapp_ns.doc('send_whatsapp_message')
    @whatsapp_ns.expect(whatsapp_message_model)
    @whatsapp_ns.marshal_with(message_response_model, code=200)
    @whatsapp_ns.marshal_with(error_model, code=400)
    @whatsapp_ns.marshal_with(error_model, code=404)
    @whatsapp_ns.marshal_with(error_model, code=500)
    @whatsapp_ns.response(200, 'Mensaje enviado exitosamente')
    @whatsapp_ns.response(400, 'Datos inválidos o tenant no encontrado')
    @whatsapp_ns.response(404, 'Tenant no encontrado')
    @whatsapp_ns.response(500, 'Error interno del servidor')
    @whatsapp_ns.header('X-Tenant-ID', 'ID del tenant (opcional, usa el primero si no se proporciona)', required=False)
    def post(self):
        """
        Envía un mensaje de WhatsApp usando las credenciales del tenant.
        
        Utiliza el header X-Tenant-ID para especificar el tenant, o usa el primero disponible.
        """
        tenant_id_from_header = request.headers.get('X-Tenant-ID')
        current_tenant_id = None

        if tenant_id_from_header and is_valid_uuid(tenant_id_from_header):
            current_tenant_id = tenant_id_from_header
        else:
            first_tenant = query_db('SELECT id FROM tenants LIMIT 1', one=True)
            if first_tenant:
                current_tenant_id = first_tenant['id']
            else:
                return {"error": "No hay tenants configurados. Por favor, cree uno primero."}, 400

        tenant = query_db('SELECT * FROM tenants WHERE id = %s', [current_tenant_id], one=True)
        if not tenant:
            return {"error": "Tenant no encontrado"}, 404

        data = request.get_json()
        to_number = data.get('to_number')
        message_body = data.get('message_body')

        if not to_number or not message_body:
            return {"error": "Faltan los campos 'to_number' o 'message_body'"}, 400

        if not re.match(r'^\+?[1-9]\d{1,14}$', to_number):
            return {"error": "Formato de número de teléfono inválido. Debe estar en formato E.164."}, 400

        try:
            account_sid = tenant['twilio_account_sid']
            auth_token = tenant['twilio_auth_token']
            twilio_whatsapp_number = tenant['twilio_whatsapp_number']

            if not account_sid or not auth_token or not twilio_whatsapp_number:
                return {"error": "Credenciales de Twilio no configuradas para este tenant."}, 500

            client = Client(account_sid, auth_token)
            
            if not to_number.startswith('whatsapp:'):
                to_number = 'whatsapp:' + to_number

            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to_number,
                body=message_body
            )

            conn = get_db_connection()
            cur = conn.cursor()

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
                conversation_id = conversation[0]
                cur.execute(
                    """
                    UPDATE conversations
                    SET last_message_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (conversation_id,)
                )
            else:
                conversation_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO conversations (id, tenant_id, whatsapp_user_id, last_message_at, status)
                    VALUES (%s, %s, %s, NOW(), 'active')
                    """,
                    (conversation_id, current_tenant_id, whatsapp_user_id_clean)
                )
            
            cur.execute(
                """
                INSERT INTO messages (id, conversation_id, tenant_id, message_sid, sender_type, body, to_number, timestamp)
                VALUES (%s, %s, %s, %s, 'bot', %s, %s, NOW())
                """,
                (str(uuid.uuid4()), conversation_id, current_tenant_id, message.sid, message_body, to_number)
            )
            conn.commit()
            cur.close()
            conn.close()

            return {"success": True, "message_sid": message.sid}, 200

        except TwilioRestException as e:
            return {"error": f"Error de Twilio: {e.msg}"}, 500
        except Exception as e:
            return {"error": f"Error interno del servidor: {str(e)}"}, 500

@tenants_ns.route('/')
class TenantList(Resource):
    @tenants_ns.doc('create_tenant')
    @tenants_ns.expect(tenant_model)
    @tenants_ns.marshal_with(tenant_create_response_model, code=201)
    @tenants_ns.marshal_with(error_model, code=400)
    @tenants_ns.marshal_with(error_model, code=409)
    @tenants_ns.marshal_with(error_model, code=500)
    @tenants_ns.response(201, 'Tenant creado exitosamente')
    @tenants_ns.response(400, 'Faltan campos obligatorios')
    @tenants_ns.response(409, 'El número de WhatsApp ya existe')
    @tenants_ns.response(500, 'Error interno del servidor')
    def post(self):
        """
        Crea un nuevo inquilino con credenciales de Twilio.
        
        La API Key se genera automáticamente y es igual al ID del tenant (inmutable).
        """
        data = request.get_json()
        name = data.get('name')
        twilio_account_sid = data.get('twilio_account_sid')
        twilio_auth_token = data.get('twilio_auth_token')
        twilio_whatsapp_number = data.get('twilio_whatsapp_number')

        if not all([name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number]):
            return {"error": "Faltan campos obligatorios: name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number"}, 400

        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            tenant_id = str(uuid.uuid4())
            api_key = tenant_id
            
            cur.execute(
                """
                INSERT INTO tenants (id, name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number, api_key)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (tenant_id, name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number, api_key)
            )
            conn.commit()
            cur.close()
            conn.close()
            return {"success": True, "message": "Tenant creado exitosamente", "tenant_id": tenant_id, "api_key": api_key}, 201
        except psycopg2.IntegrityError as e:
            if conn:
                conn.rollback()
                conn.close()
            if "duplicate key value violates unique constraint" in str(e):
                return {"error": "El número de WhatsApp o API key ya existe."}, 409
            return {"error": f"Error de base de datos: {str(e)}"}, 500
        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return {"error": f"Error interno del servidor: {str(e)}"}, 500

    @tenants_ns.doc('get_tenants')
    @tenants_ns.marshal_list_with(tenant_response_model)
    @tenants_ns.response(200, 'Lista de tenants obtenida exitosamente')
    def get(self):
        """
        Obtiene la lista de todos los inquilinos registrados.
        """
        tenants = query_db('SELECT id, name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number, api_key, created_at, updated_at FROM tenants ORDER BY created_at DESC')
        return tenants

@tenants_ns.route('/<string:tenant_id>')
class TenantDetail(Resource):
    @tenants_ns.doc('get_tenant')
    @tenants_ns.marshal_with(tenant_response_model)
    @tenants_ns.marshal_with(error_model, code=400)
    @tenants_ns.marshal_with(error_model, code=404)
    @tenants_ns.response(200, 'Tenant obtenido exitosamente')
    @tenants_ns.response(400, 'ID de tenant inválido')
    @tenants_ns.response(404, 'Tenant no encontrado')
    def get(self, tenant_id):
        """
        Obtiene los detalles de un inquilino específico.
        """
        if not is_valid_uuid(tenant_id):
            return {"error": "ID de tenant inválido"}, 400
        
        tenant = query_db('SELECT id, name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number, api_key, created_at, updated_at FROM tenants WHERE id = %s', [tenant_id], one=True)
        if not tenant:
            return {"error": "Tenant no encontrado"}, 404
        
        return tenant

    @tenants_ns.doc('update_tenant')
    @tenants_ns.expect(tenant_model)
    @tenants_ns.marshal_with(success_model)
    @tenants_ns.marshal_with(error_model, code=400)
    @tenants_ns.marshal_with(error_model, code=404)
    @tenants_ns.marshal_with(error_model, code=409)
    @tenants_ns.marshal_with(error_model, code=500)
    @tenants_ns.response(200, 'Tenant actualizado exitosamente')
    @tenants_ns.response(400, 'ID de tenant inválido o datos faltantes')
    @tenants_ns.response(404, 'Tenant no encontrado')
    @tenants_ns.response(409, 'El número de WhatsApp ya existe')
    @tenants_ns.response(500, 'Error interno del servidor')
    def put(self, tenant_id):
        """
        Actualiza los detalles de un inquilino específico.
        
        La API Key NO se puede actualizar (es inmutable).
        """
        if not is_valid_uuid(tenant_id):
            return {"error": "ID de tenant inválido"}, 400
        
        data = request.get_json()
        name = data.get('name')
        twilio_account_sid = data.get('twilio_account_sid')
        twilio_auth_token = data.get('twilio_auth_token')
        twilio_whatsapp_number = data.get('twilio_whatsapp_number')

        if not any([name, twilio_account_sid, twilio_auth_token, twilio_whatsapp_number]):
            return {"error": "Debe proporcionar al menos un campo para actualizar"}, 400

        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT id FROM tenants WHERE id = %s', (tenant_id,))
            if not cur.fetchone():
                return {"error": "Tenant no encontrado"}, 404
            
            update_fields = []
            update_values = []
            
            if name:
                update_fields.append("name = %s")
                update_values.append(name)
            if twilio_account_sid:
                update_fields.append("twilio_account_sid = %s")
                update_values.append(twilio_account_sid)
            if twilio_auth_token:
                update_fields.append("twilio_auth_token = %s")
                update_values.append(twilio_auth_token)
            if twilio_whatsapp_number:
                update_fields.append("twilio_whatsapp_number = %s")
                update_values.append(twilio_whatsapp_number)
            
            update_fields.append("updated_at = NOW()")
            update_values.append(tenant_id)
            
            query = f"UPDATE tenants SET {', '.join(update_fields)} WHERE id = %s"
            cur.execute(query, update_values)
            conn.commit()
            cur.close()
            conn.close()
            
            return {"success": True, "message": "Tenant actualizado exitosamente"}, 200
        except psycopg2.IntegrityError as e:
            if conn:
                conn.rollback()
                conn.close()
            if "duplicate key value violates unique constraint" in str(e):
                return {"error": "El número de WhatsApp o API key ya existe."}, 409
            return {"error": f"Error de base de datos: {str(e)}"}, 500
        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return {"error": f"Error interno del servidor: {str(e)}"}, 500

    @tenants_ns.doc('delete_tenant')
    @tenants_ns.marshal_with(success_model)
    @tenants_ns.marshal_with(error_model, code=400)
    @tenants_ns.marshal_with(error_model, code=404)
    @tenants_ns.marshal_with(error_model, code=500)
    @tenants_ns.response(200, 'Tenant eliminado exitosamente')
    @tenants_ns.response(400, 'ID de tenant inválido')
    @tenants_ns.response(404, 'Tenant no encontrado')
    @tenants_ns.response(500, 'Error interno del servidor')
    def delete(self, tenant_id):
        """
        Elimina un inquilino específico.
        
        También elimina todas las conversaciones y mensajes relacionados (CASCADE).
        """
        if not is_valid_uuid(tenant_id):
            return {"error": "ID de tenant inválido"}, 400
        
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT id FROM tenants WHERE id = %s', (tenant_id,))
            if not cur.fetchone():
                return {"error": "Tenant no encontrado"}, 404
            
            cur.execute('DELETE FROM tenants WHERE id = %s', (tenant_id,))
            conn.commit()
            cur.close()
            conn.close()
            
            return {"success": True, "message": "Tenant eliminado exitosamente"}, 200
        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return {"error": f"Error interno del servidor: {str(e)}"}, 500

@messages_ns.route('/')
class MessageList(Resource):
    @messages_ns.doc('get_messages')
    @messages_ns.marshal_list_with(message_model)
    @messages_ns.response(200, 'Historial de mensajes obtenido exitosamente')
    @jwt_required()
    def get(self):
        """
        Obtiene el historial de mensajes para el tenant autenticado.
        
        Requiere autenticación JWT.
        """
        current_tenant_id = get_jwt_identity()
        messages = query_db('SELECT * FROM messages WHERE tenant_id = %s ORDER BY timestamp DESC', [current_tenant_id])
        return messages