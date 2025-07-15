#!/usr/bin/env python3
"""
Script para crear las tablas de la base de datos usando psycopg2
"""

import os
import psycopg2
from dotenv import load_dotenv
import uuid
from werkzeug.security import generate_password_hash

# Cargar variables de entorno
load_dotenv()

def create_database_tables():
    """Crear todas las tablas necesarias en la base de datos"""
    
    # Obtener URL de la base de datos
    database_url = os.getenv('DIRECT_URL')
    
    if not database_url:
        print("❌ Error: No se encontró DATABASE_URL en las variables de entorno")
        return False
    
    # Verificar que no tenga placeholder
    if '[YOUR-PASSWORD]' in database_url:
        print("❌ Error: Debes reemplazar [YOUR-PASSWORD] con tu contraseña real de Supabase")
        return False
    
    conn = None
    try:
        # Conectar a la base de datos
        print("🔄 Conectando a la base de datos...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Eliminar tablas existentes
        print("🔄 Eliminando tablas existentes...")
        cursor.execute("""
            DROP TABLE IF EXISTS messages CASCADE;
            DROP TABLE IF EXISTS conversations CASCADE;
            DROP TABLE IF EXISTS tenants CASCADE;
        """)
        conn.commit()
        
        # Crear tablas
        print("🔄 Creando tablas...")
        cursor.execute("""
        -- Tabla de inquilinos/tenants
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            twilio_whatsapp_number VARCHAR(30) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Tabla de conversaciones
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            whatsapp_user_id VARCHAR(50) NOT NULL,
            last_message_at TIMESTAMP DEFAULT NOW(),
            status VARCHAR(50) DEFAULT 'open',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tenant_id, whatsapp_user_id)
        );
        
        -- Tabla de mensajes
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            message_sid VARCHAR(50) UNIQUE NOT NULL,
            sender_type VARCHAR(10) NOT NULL CHECK (sender_type IN ('user', 'bot')),
            body TEXT,
            media_url VARCHAR(500),
            timestamp TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Índices para mejorar el rendimiento
        CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_tenant_id ON messages(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
        
        -- Función para actualizar updated_at automáticamente
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Triggers para actualizar updated_at
        DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;
        CREATE TRIGGER update_tenants_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
        CREATE TRIGGER update_conversations_updated_at
            BEFORE UPDATE ON conversations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS update_messages_updated_at ON messages;
        CREATE TRIGGER update_messages_updated_at
            BEFORE UPDATE ON messages
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)
        
        # Insertar inquilino de prueba
        test_tenant_uuid = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO tenants (id, name, username, password, twilio_whatsapp_number)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            test_tenant_uuid,
            "Empresa Demo",
            "demo",
            generate_password_hash("password"), # In a real application, this should be a hashed password
            "whatsapp:+14155238886"
        ))
        
        conn.commit()
        print("✅ Base de datos configurada exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error al configurar la base de datos: {e}")
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    print("🚀 Configurando base de datos para Bot WhatsApp Manager...")
    success = create_database_tables()
    if not success:
        print("\n💡 Asegúrate de:")
        print("   1. Tener las credenciales correctas en .env")
        print("   2. Que Supabase esté funcionando")
        print("   3. Que la URL de base de datos sea correcta")
        exit(1)
    else:
        print("\n✅ Todo listo para usar!")
