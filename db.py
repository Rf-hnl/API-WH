from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
# Usar la URL directa de la base de datos
DIRECT_URL = os.getenv('DIRECT_URL')
if not DIRECT_URL:
    raise ValueError("DIRECT_URL no está configurado en las variables de entorno")

engine = create_engine(DIRECT_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    twilio_whatsapp_number = Column(String, unique=True)
    api_key = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    conversations = relationship("Conversation", back_populates="tenant")
    messages = relationship("Message", back_populates="tenant")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"))
    whatsapp_user_id = Column(String)
    last_message_at = Column(DateTime)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    __table_args__ = (UniqueConstraint('tenant_id', 'whatsapp_user_id', name='_tenant_whatsapp_user_uc'),)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    message_sid = Column(String, unique=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    tenant_id = Column(String, ForeignKey("tenants.id"))
    content = Column(String)
    timestamp = Column(DateTime)
    
    conversation = relationship("Conversation", back_populates="messages")
    tenant = relationship("Tenant", back_populates="messages")

# Función para obtener una sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
