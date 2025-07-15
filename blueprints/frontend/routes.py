# blueprints/frontend/routes.py

from flask import Blueprint, render_template
from models import Tenant, Conversation, Message
from sqlalchemy import func
from datetime import datetime, timedelta

frontend_bp = Blueprint('frontend_bp', __name__)

@frontend_bp.route('/')
@frontend_bp.route('/dashboard')
def dashboard():
    total_tenants = Tenant.query.count()
    active_conversations = Conversation.query.filter_by(status='active').count()
    
    today = datetime.utcnow().date()
    messages_today = Message.query.filter(func.date(Message.timestamp) == today).count()
    total_messages = Message.query.count()

    recent_conversations = Conversation.query.order_by(Conversation.last_message_at.desc()).limit(5).all()

    stats = {
        'total_tenants': total_tenants,
        'active_conversations': active_conversations,
        'messages_today': messages_today,
        'total_messages': total_messages
    }
    return render_template('dashboard.html', stats=stats, recent_conversations=recent_conversations)

@frontend_bp.route('/conversations')
def conversations():
    return render_template('conversations.html')

@frontend_bp.route('/send_message')
def send_message_page():
    return render_template('send_message.html')

@frontend_bp.route('/tenants')
def tenants_page():
    return render_template('tenants.html')

@frontend_bp.route('/create-tenant')
def create_tenant_form():
    return render_template('create_tenant.html')
