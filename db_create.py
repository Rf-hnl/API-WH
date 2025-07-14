from app import app, db
from models import Tenant, Conversation, Message

with app.app_context():
    db.create_all()
    print("Base de datos y tablas creadas.")

    # Opcional: Descomenta si quieres crear un inquilino de prueba automáticamente
    # from uuid import uuid4
    # test_tenant_api_key = str(uuid4()) # Generar una API Key para el inquilino de prueba
    # # ASEGÚRATE DE QUE ESTE NÚMERO COINCIDA CON TU TWILIO_WHATSAPP_NUMBER DEL .env
    # test_tenant_whatsapp_number = "whatsapp:+14155238886"
    #
    # # Verificar si el inquilino ya existe para evitar duplicados
    # existing_tenant = Tenant.query.filter_by(twilio_whatsapp_number=test_tenant_whatsapp_number).first()
    # if not existing_tenant:
    #     test_tenant = Tenant(
    #         name="Mi Tienda de Ropa Virtual",
    #         twilio_whatsapp_number=test_tenant_whatsapp_number,
    #         api_key=test_tenant_api_key
    #     )
    #     db.session.add(test_tenant)
    #     db.session.commit()
    #     print(f"Inquilino de prueba 'Mi Tienda de Ropa Virtual' creado con API Key: {test_tenant_api_key}")
    # else:
    #     print(f"Inquilino de prueba para {test_tenant_whatsapp_number} ya existe.")

