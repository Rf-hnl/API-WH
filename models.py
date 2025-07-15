import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    twilio_whatsapp_number = db.Column(db.String(20), unique=True, nullable=False)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = db.relationship('Conversation', backref='tenant', lazy=True)
    messages = db.relationship('Message', backref='tenant', lazy=True)

class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    whatsapp_user_id = db.Column(db.String(50), nullable=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='open') # Optional status field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('tenant_id', 'whatsapp_user_id', name='_tenant_user_uc'),)

    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False) # Denormalized
    message_sid = db.Column(db.String(50), unique=True, nullable=False) # Twilio message SID
    sender_type = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    body = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    twilio_whatsapp_number = db.Column(db.String(20), unique=True, nullable=False)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = db.relationship('Conversation', backref='tenant', lazy=True)
    messages = db.relationship('Message', backref='tenant', lazy=True)

class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    whatsapp_user_id = db.Column(db.String(50), nullable=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='open') # Optional status field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('tenant_id', 'whatsapp_user_id', name='_tenant_user_uc'),)

    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False) # Denormalized
    message_sid = db.Column(db.String(50), unique=True, nullable=False) # Twilio message SID
    sender_type = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    body = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
