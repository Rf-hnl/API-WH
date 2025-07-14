# app.py

from flask import Flask, request, jsonify, render_template, g
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import json
from datetime import datetime
from models_prisma.client import Prisma
from models_prisma.models import Tenant

import functools
import asyncio # Importar asyncio para manejar operaciones asíncronas

app = Flask(__name__)

@app.before_request
async def before_request():
    g.prisma = Prisma()
    await g.prisma.connect()

@app.teardown_appcontext
async def teardown_appcontext(exception):
    if hasattr(g, 'prisma'):
        try:
            await g.prisma.disconnect()
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                # This happens when the application is shutting down and the event loop is already closed.
                # It's safe to ignore in this context.
                pass
            else:
                # Re-raise other RuntimeErrors
                raise

# Decorador de autenticación simulado con JWT (para multi-tenancy real)
# NOTA: En un entorno de producción, JWT_SECRET debe ser una variable de entorno segura
# y el token se generaría en un endpoint de login/autenticación.
def require_jwt(f):
    @functools.wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Authentication required: Bearer token missing"}), 401

        token = auth_header.replace("Bearer ", "")
        try:
            # Aquí deberías usar una clave secreta real de tu .env
            # payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
            # g.tenant_id = payload["tenant_id"]

            # Por ahora, simulamos la obtención del tenant_id directamente de la cabecera X-Tenant-ID
            # Esto DEBE ser reemplazado por una validación JWT real en producción.
            tenant_id = request.headers.get('X-Tenant-ID')
            if not tenant_id:
                return jsonify({"success": False, "error": "Authentication required: X-Tenant-ID header missing (simulated JWT)"}), 401

            # Recuperar el objeto Tenant de la base de datos
            # La conexión de Prisma ya está abierta globalmente
            tenant = await g.prisma.tenant.find_unique(where={"id": tenant_id})
            if not tenant:
                return jsonify({"success": False, "error": "Unauthorized: Invalid Tenant ID"}), 401
            
            g.tenant = tenant # Almacenar el objeto tenant en el contexto de la petición
            g.tenant_id = tenant.id # También el ID para consistencia

        except Exception as e: # Captura genérica para errores de JWT o búsqueda de tenant
            print(f"Error en autenticación JWT/Tenant: {e}")
            return jsonify({"success": False, "error": f"Authentication failed: {str(e)}"}), 401
        
        return await f(*args, **kwargs)
    return decorated_function

@app.route('/')
async def index():
    try:
        # Obtener estadísticas
        total_tenants = await g.prisma.tenant.count()
        
        # Crear el diccionario de estadísticas
        stats = {
            'total_tenants': total_tenants
        }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        print(f"Error al obtener estadísticas: {e}")
        return render_template('dashboard.html', stats={'total_tenants': 0})

@app.route('/dashboard')
def dashboard():
    # Fetch statistics for the dashboard
    # Create a new Prisma client instance for this synchronous function
    # and manage its lifecycle within the function.
    # This is a workaround for the "Event loop is closed" error with Flask's dev server.
    async def get_stats():
        client = Prisma()
        await client.connect()
        try:
            total_tenants = await client.tenant.count()
            total_conversations = await client.whatsappmessage.count() # Assuming all messages are part of conversations
        finally:
            await client.disconnect()
        
        return {
            "total_tenants": total_tenants,
            "total_conversations": total_conversations,
            "total_messages_sent": total_conversations, # For now, assuming 1 message = 1 conversation entry
        }

    stats = asyncio.run(get_stats())
    return render_template('dashboard.html', stats=stats)

@app.route('/conversations')
def conversations():
    return render_template('conversations.html')

@app.route('/send_message')
def send_message_page():
    return render_template('send_message.html')

@app.route('/tenants')
def tenants_page():
    return render_template('tenants.html')

# Endpoints CRUD para Tenants (Recomendación 1.2)
@app.route('/tenants', methods=['POST'])
async def create_tenant():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "Invalid JSON"}), 400
        
        name = data.get('name')
        twilio_account_sid = data.get('twilio_account_sid')
        twilio_auth_token = data.get('twilio_auth_token')

        if not all([name, twilio_account_sid, twilio_auth_token]):
            return jsonify({"success": False, "error": "Missing required fields: name, twilio_account_sid, twilio_auth_token"}), 400

        tenant = await g.prisma.tenant.create(
            data={
                "name": name,
                "twilioAccountSid": twilio_account_sid,
                "twilioAuthToken": twilio_auth_token
            }
        )
        return jsonify({"success": True, "tenant": tenant.dict()}), 201
    except Exception as e:
        print(f"Error al crear tenant: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {e}"}), 500

@app.route('/tenants/<tenant_id>', methods=['GET'])
@require_jwt # Proteger este endpoint
async def get_tenant(tenant_id):
    try:
        # Asegurarse de que el tenant_id solicitado coincide con el tenant_id autenticado
        if g.tenant_id != tenant_id:
            return jsonify({"success": False, "error": "Unauthorized: Cannot access other tenant's data"}), 403

        tenant = await g.prisma.tenant.find_unique(where={"id": tenant_id})
        if not tenant:
            return jsonify({"success": False, "error": "Tenant not found"}), 404
        return jsonify({"success": True, "tenant": tenant.dict()}), 200
    except Exception as e:
        print(f"Error al obtener tenant: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {e}"}), 500

# Puedes añadir más endpoints PUT y DELETE para tenants

@app.route('/send_whatsapp', methods=['POST'])
@require_jwt # Proteger este endpoint con autenticación JWT/Tenant
async def send_whatsapp():
    """
    Endpoint para enviar mensajes de WhatsApp usando Twilio.
    Gestiona la autenticación multi-tenant y registra el mensaje en Supabase.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "Invalid JSON"}), 400

        # Las credenciales de Twilio NO se reciben del frontend (Recomendación 2.1)
        # Se obtienen del tenant autenticado (Recomendación 2.3)
        tenant = g.tenant # Acceder al objeto tenant del contexto de la petición
        account_sid = tenant.twilioAccountSid
        auth_token = tenant.twilioAuthToken
        
        twilio_number = data.get('twilio_number')
        content_sid = data.get('content_sid')
        content_variables_str = data.get('content_variables', '{}')
        to_number = data.get('to_number')

        # Validaciones básicas
        if not all([twilio_number, content_sid, to_number]): # account_sid y auth_token ya no son necesarios aquí
            return jsonify({"success": False, "error": "Missing required fields: twilio_number, content_sid, to_number"}), 400

        try:
            content_variables = json.loads(content_variables_str)
        except json.JSONDecodeError:
            return jsonify({"success": False, "error": "Invalid JSON for content_variables"}), 400

        client = Client(account_sid, auth_token)

        message_sid = None
        try:
            message = client.messages.create(
                from_=twilio_number,
                content_sid=content_sid,
                content_variables=content_variables,
                to=to_number
            )
            message_sid = message.sid
            success = True
            error_message = None
        except TwilioRestException as e: # Manejo de errores más específico (Recomendación 3)
            success = False
            error_message = str(e)
            print(f"Error de Twilio: {e}")
            # Ejemplo de manejo de error 63007
            if e.code == 63007:
                error_message = "Error 63007: From no válido o plantilla no aprobada."
                return jsonify({"success": False, "error": error_message}), 400
            else:
                return jsonify({"success": False, "error": f"Twilio error {e.code}: {e.msg}"}), 400
        except Exception as e: # Para otros errores inesperados
            success = False
            error_message = str(e)
            print(f"Error inesperado al enviar Twilio: {e}")
            return jsonify({"success": False, "error": f"Internal server error: {e}"}), 500

        # Registrar el mensaje (la conexión de Prisma ya está abierta)
        try:
            await g.prisma.whatsappmessage.create(
                data={
                    "tenantId": tenant.id, # Usar el ID del tenant autenticado
                    "messageSid": message_sid,
                    "fromNumber": twilio_number,
                    "toNumber": to_number,
                    "contentSid": content_sid,
                    "contentVariables": content_variables_str,
                    "status": "sent" if success else "failed",
                    "errorMessage": error_message,
                    "createdAt": datetime.now()
                }
            )
        except Exception as db_e:
            print(f"Error al guardar en la base de datos: {db_e}")
            # Aunque falle la DB, si Twilio envió el mensaje, reportamos éxito de Twilio.
            if success:
                return jsonify({"success": True, "message_sid": message_sid, "db_error": str(db_e)}), 200
            else:
                return jsonify({"success": False, "error": f"DB Error: {db_e}, Twilio Error: {error_message}"}), 500

        if success:
            return jsonify({"success": True, "message_sid": message_sid}), 200
        else:
            return jsonify({"success": False, "error": error_message}), 500

    except Exception as e:
        print(f"Error inesperado en send_whatsapp: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {e}"}), 500

# Webhook de Twilio (Recomendación 6)
@app.route('/webhook/twilio', methods=['POST'])
# @require_jwt # Si el webhook de Twilio puede incluir un token JWT para identificar el tenant
def twilio_webhook():
    # Twilio envía datos en application/x-www-form-urlencoded
    message_sid = request.form.get('MessageSid')
    message_status = request.form.get('MessageStatus') # e.g., 'delivered', 'read', 'failed'
    from_number = request.form.get('From')
    to_number = request.form.get('To')
    message_body = request.form.get('Body') # Para mensajes entrantes

    print(f"Webhook Twilio recibido: SID={message_sid}, Status={message_status}, From={from_number}, To={to_number}, Body={message_body}")

    # Aquí deberías identificar el tenant_id asociado a este webhook.
    # Esto podría ser a través de un parámetro en la URL del webhook configurado en Twilio,
    # o buscando el tenant_id en tu DB usando el twilio_number o message_sid.
    # Por simplicidad, usaremos un tenant_id por defecto o el del g.tenant si se usa JWT.
    tenant_id = g.get('tenant_id', 'default_webhook_tenant_id') # Si no hay JWT, usar un default

    # Actualizar el estado del mensaje en la base de datos
    # Nota: Prisma Client Python no soporta await fuera de funciones async.
    # Si este endpoint no es async, necesitarías usar un loop de eventos o
    # ejecutar la operación de Prisma de forma síncrona si es posible,
    # o usar un framework ASGI como Quart.
    # Para este ejemplo, asumimos que Flask está configurado para manejar async.
    try:
        # await prisma.whatsappmessage.update( # Esto requiere un contexto async
        #     where={"messageSid": message_sid},
        #     data={"status": message_status}
        # )
        print(f"Actualizando mensaje {message_sid} a estado {message_status} para tenant {tenant_id}")
    except Exception as e:
        print(f"Error al actualizar estado de mensaje en DB desde webhook: {e}")

    return ("", 204) # Twilio espera una respuesta 200 OK o 204 No Content

if __name__ == '__main__':
    app.run(debug=True, port=5000)
