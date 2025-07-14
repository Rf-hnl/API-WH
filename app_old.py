import os
import uuid  # Necesario si usas UUIDs para IDs
from flask import Flask, request, jsonify, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno desde .env

# Importa tus modelos de base de datos
from models import db, Tenant, Conversation, Message

app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key_very_insecure')

# Inicializa la base de datos con la aplicación Flask
db.init_app(app)

# Credenciales de Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')  # Número de tu Twilio Sandbox/Producción

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- Funciones de Utilidad ---

def get_tenant_by_whatsapp_number(whatsapp_number):
    """
    Busca un inquilino por su número de WhatsApp.
    Este número debe coincidir con el 'To' del webhook de Twilio.
    """
    # Eliminar "whatsapp:" si es necesario, dependiendo de cómo lo almacenes en la DB
    # Asegúrate de que el formato en la DB y el de Twilio sean consistentes
    return Tenant.query.filter_by(twilio_whatsapp_number=whatsapp_number).first()

def get_tenant_by_api_key(api_key):
    """
    Busca un inquilino por su API Key para la autenticación de la API.
    """
    return Tenant.query.filter_by(api_key=api_key).first()

def authenticate_tenant():
    """
    Función decoradora/utilidad para autenticar solicitudes API.
    Espera una cabecera 'X-API-Key'.
    """
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        abort(401, description="Autenticación requerida: X-API-Key no proporcionada.")
    tenant = get_tenant_by_api_key(api_key)
    if not tenant:
        abort(403, description="Acceso denegado: API Key inválida.")
    return tenant

# --- Webhook de Twilio para Mensajes Entrantes ---

@app.route('/webhook/twilio', methods=['POST'])
def twilio_webhook():
    """
    Endpoint para recibir mensajes entrantes de WhatsApp desde Twilio.
    """
    # Twilio envía los datos del mensaje en el cuerpo de la solicitud POST
    message_body = request.form.get('Body', '')
    from_whatsapp_number = request.form.get('From', '')  # El número del usuario de WhatsApp
    to_whatsapp_number = request.form.get('To', '')    # Tu número de Twilio (para identificar al inquilino)
    message_sid = request.form.get('MessageSid', '')
    num_media = int(request.form.get('NumMedia', 0))
    media_url = None
    if num_media > 0:
        # Twilio proporciona una URL temporal para los medios. Debes descargarla y almacenarla.
        media_url = request.form.get('MediaUrl0')

    print(f"Mensaje recibido de {from_whatsapp_number} a {to_whatsapp_number}: {message_body}")

    # 1. Identificar el inquilino
    tenant = get_tenant_by_whatsapp_number(to_whatsapp_number)
    if not tenant:
        print(f"Error: No se encontró inquilino para el número de Twilio: {to_whatsapp_number}")
        # Aunque no tenemos un inquilino, podemos responder con un mensaje genérico.
        resp = MessagingResponse()
        resp.message("Lo sentimos, no pudimos identificar a qué servicio pertenece su mensaje. Por favor, revise el número.")
        return str(resp)

    # 2. Encontrar o crear la conversación
    conversation = Conversation.query.filter_by(
        tenant_id=tenant.id,
        whatsapp_user_id=from_whatsapp_number
    ).first()

    if not conversation:
        conversation = Conversation(
            tenant_id=tenant.id,
            whatsapp_user_id=from_whatsapp_number,
            last_message_at=datetime.utcnow()
        )
        db.session.add(conversation)
        db.session.commit()  # Commit para obtener el ID de la conversación antes de usarlo
        print(f"Nueva conversación creada para inquilino {tenant.name} y usuario {from_whatsapp_number}")

    # 3. Guardar el mensaje entrante
    new_message = Message(
        conversation_id=conversation.id,
        tenant_id=tenant.id,  # Denormalizado para facilitar consultas
        message_sid=message_sid,
        sender_type='user',
        body=message_body,
        media_url=media_url,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_message)

    # Actualizar last_message_at de la conversación
    conversation.last_message_at = datetime.utcnow()
    db.session.commit()

    # 4. Lógica de respuesta del bot (ejemplo básico)
    resp = MessagingResponse()
    if message_body.lower() == 'hola':
        resp.message(f"¡Hola! Soy el bot de {tenant.name}. ¿En qué puedo ayudarte?")
    elif message_body.lower() == 'ayuda':
        resp.message("Puedes preguntar sobre nuestros servicios o productos.")
    else:
        # Aquí es donde podrías integrar con un modelo de IA, un sistema de tickets, etc.
        resp.message("Gracias por tu mensaje. Un agente te responderá pronto.")

    return str(resp)  # Twilio espera una respuesta TwiML

# --- API RESTful para Gestión (Multi-Inquilino) ---

# Endpoint para crear un nuevo inquilino (solo para administración inicial)
@app.route('/api/tenants', methods=['POST'])
def create_tenant():
    # En un sistema real, este endpoint estaría altamente protegido,
    # quizás solo accesible internamente o por un administrador.
    data = request.get_json()
    name = data.get('name')
    twilio_whatsapp_number = data.get('twilio_whatsapp_number')
    api_key = data.get('api_key')

    if not all([name, twilio_whatsapp_number, api_key]):
        return jsonify({"error": "Faltan datos requeridos (name, twilio_whatsapp_number, api_key)"}), 400

    existing_tenant = Tenant.query.filter_by(twilio_whatsapp_number=twilio_whatsapp_number).first()
    if existing_tenant:
        return jsonify({"error": "Número de WhatsApp ya en uso por otro inquilino"}), 409

    new_tenant = Tenant(
        name=name,
        twilio_whatsapp_number=twilio_whatsapp_number,
        api_key=api_key  # En producción, hash y salta esta clave
    )
    db.session.add(new_tenant)
    db.session.commit()
    return jsonify({
        "message": "Inquilino creado exitosamente",
        "tenant_id": new_tenant.id,
        "name": new_tenant.name
    }), 201

# Endpoint para enviar un mensaje saliente
@app.route('/api/send_message', methods=['POST'])
def send_message_api():
    tenant = authenticate_tenant()  # Autentica al inquilino

    data = request.get_json()
    to_whatsapp_number = data.get('to')  # El número del usuario de WhatsApp al que enviar
    message_body = data.get('body')
    media_url = data.get('media_url')  # URL del medio (imagen, video)

    if not all([to_whatsapp_number, message_body]):
        return jsonify({"error": "Número de destino ('to') y cuerpo del mensaje ('body') son requeridos"}), 400

    try:
        # Busca la conversación existente o crea una nueva
        conversation = Conversation.query.filter_by(
            tenant_id=tenant.id,
            whatsapp_user_id=to_whatsapp_number
        ).first()

        if not conversation:
            conversation = Conversation(
                tenant_id=tenant.id,
                whatsapp_user_id=to_whatsapp_number,
                last_message_at=datetime.utcnow()
            )
            db.session.add(conversation)
            db.session.commit()  # Commit para obtener el ID de la conversación

        # Enviar mensaje usando el cliente de Twilio
        message = twilio_client.messages.create(
            from_=tenant.twilio_whatsapp_number,  # Usar el número de WhatsApp del inquilino
            to=to_whatsapp_number,
            body=message_body,
            media_url=[media_url] if media_url else None
        )
        print(f"Mensaje enviado con SID: {message.sid}")

        # Guardar el mensaje saliente en la base de datos
        new_message = Message(
            conversation_id=conversation.id,
            tenant_id=tenant.id,
            message_sid=message.sid,
            sender_type='bot',
            body=message_body,
            media_url=media_url,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_message)
        conversation.last_message_at = datetime.utcnow()  # Actualizar last_message_at
        db.session.commit()

        return jsonify({
            "message": "Mensaje enviado exitosamente",
            "twilio_message_sid": message.sid,
            "conversation_id": conversation.id
        }), 200

    except Exception as e:
        print(f"Error al enviar mensaje: {e}")
        return jsonify({"error": f"Error al enviar mensaje: {str(e)}"}), 500

# Endpoint para listar conversaciones de un inquilino
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    tenant = authenticate_tenant()  # Autentica al inquilino

    conversations = Conversation.query.filter_by(tenant_id=tenant.id).order_by(Conversation.last_message_at.desc()).all()
    result = []
    for conv in conversations:
        # Obtener el último mensaje para mostrar un snippet
        # Cuidado: Esto puede ser ineficiente para muchas conversaciones. Considera una consulta JOIN o un campo denormalizado en Conversation.
        last_msg = Message.query.filter_by(conversation_id=conv.id).order_by(Message.timestamp.desc()).first()
        result.append({
            "id": conv.id,
            "whatsapp_user_id": conv.whatsapp_user_id,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "last_message_body": last_msg.body if last_msg else None,
            "status": conv.status  # Si lo implementas
        })
    return jsonify(result), 200

# Endpoint para obtener el historial de mensajes de una conversación específica
@app.route('/api/conversations/<uuid:conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    tenant = authenticate_tenant()  # Autentica al inquilino

    conversation = Conversation.query.filter_by(id=conversation_id, tenant_id=tenant.id).first()
    if not conversation:
        return jsonify({"error": "Conversación no encontrada o no pertenece a este inquilino"}), 404

    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp.asc()).all()
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_type": msg.sender_type,
            "body": msg.body,
            "media_url": msg.media_url,
            "timestamp": msg.timestamp.isoformat()
        })
    return jsonify(result), 200


if __name__ == '__main__':
    # Este bloque solo se ejecuta cuando app.py se ejecuta directamente.
    # Para la creación de la base de datos, es mejor usar db_create.py por separado.
    # Si quieres que se cree automáticamente en el primer run (solo para desarrollo MUY inicial):
    # with app.app_context():
    #     db.create_all()
    #     print("Base de datos y tablas creadas (desde app.py).")
    app.run(debug=True, port=5000)