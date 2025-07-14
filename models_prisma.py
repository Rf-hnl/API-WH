import asyncio
from datetime import datetime
from typing import List, Optional
from prisma import Prisma
from prisma.models import Tenant, Conversation, Message

# Global Prisma client instance
prisma = Prisma()

async def connect_db():
    """Connect to the database"""
    await prisma.connect()

async def disconnect_db():
    """Disconnect from the database"""
    await prisma.disconnect()

# Tenant operations
async def create_tenant(name: str, twilio_whatsapp_number: str, api_key: str) -> Tenant:
    """Create a new tenant"""
    return await prisma.tenant.create(
        data={
            'name': name,
            'twilio_whatsapp_number': twilio_whatsapp_number,
            'api_key': api_key
        }
    )

async def get_tenant_by_api_key(api_key: str) -> Optional[Tenant]:
    """Get tenant by API key"""
    return await prisma.tenant.find_unique(
        where={'api_key': api_key}
    )

async def get_tenant_by_whatsapp_number(whatsapp_number: str) -> Optional[Tenant]:
    """Get tenant by WhatsApp number"""
    return await prisma.tenant.find_unique(
        where={'twilio_whatsapp_number': whatsapp_number}
    )

async def get_all_tenants() -> List[Tenant]:
    """Get all tenants"""
    return await prisma.tenant.find_many()

# Conversation operations
async def create_conversation(tenant_id: str, whatsapp_user_id: str) -> Conversation:
    """Create a new conversation"""
    return await prisma.conversation.create(
        data={
            'tenant_id': tenant_id,
            'whatsapp_user_id': whatsapp_user_id,
            'last_message_at': datetime.utcnow()
        }
    )

async def get_conversation(tenant_id: str, whatsapp_user_id: str) -> Optional[Conversation]:
    """Get conversation by tenant and user"""
    return await prisma.conversation.find_unique(
        where={
            'tenant_id_whatsapp_user_id': {
                'tenant_id': tenant_id,
                'whatsapp_user_id': whatsapp_user_id
            }
        }
    )

async def get_conversation_by_id(conversation_id: str) -> Optional[Conversation]:
    """Get conversation by ID"""
    return await prisma.conversation.find_unique(
        where={'id': conversation_id},
        include={'tenant': True}
    )

async def get_conversations_by_tenant(tenant_id: str) -> List[Conversation]:
    """Get all conversations for a tenant"""
    return await prisma.conversation.find_many(
        where={'tenant_id': tenant_id},
        include={'tenant': True},
        order={'last_message_at': 'desc'}
    )

async def get_recent_conversations(limit: int = 10) -> List[Conversation]:
    """Get recent conversations across all tenants"""
    return await prisma.conversation.find_many(
        include={'tenant': True},
        order={'last_message_at': 'desc'},
        take=limit
    )

async def update_conversation_last_message(conversation_id: str, timestamp: datetime) -> Conversation:
    """Update last message timestamp for conversation"""
    return await prisma.conversation.update(
        where={'id': conversation_id},
        data={'last_message_at': timestamp}
    )

# Message operations
async def create_message(
    conversation_id: str,
    tenant_id: str,
    message_sid: str,
    sender_type: str,
    body: Optional[str] = None,
    media_url: Optional[str] = None
) -> Message:
    """Create a new message"""
    return await prisma.message.create(
        data={
            'conversation_id': conversation_id,
            'tenant_id': tenant_id,
            'message_sid': message_sid,
            'sender_type': sender_type,
            'body': body,
            'media_url': media_url,
            'timestamp': datetime.utcnow()
        }
    )

async def get_messages_by_conversation(conversation_id: str) -> List[Message]:
    """Get all messages for a conversation"""
    return await prisma.message.find_many(
        where={'conversation_id': conversation_id},
        order={'timestamp': 'asc'}
    )

async def get_recent_messages(limit: int = 10) -> List[Message]:
    """Get recent messages across all conversations"""
    return await prisma.message.find_many(
        order={'timestamp': 'desc'},
        take=limit
    )

async def get_messages_today() -> List[Message]:
    """Get messages from today"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return await prisma.message.find_many(
        where={'timestamp': {'gte': today}}
    )

# Statistics operations
async def get_stats():
    """Get dashboard statistics"""
    total_tenants = await prisma.tenant.count()
    active_conversations = await prisma.conversation.count(
        where={'status': 'open'}
    )
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    messages_today = await prisma.message.count(
        where={'timestamp': {'gte': today}}
    )
    
    total_messages = await prisma.message.count()
    
    return {
        'total_tenants': total_tenants,
        'active_conversations': active_conversations,
        'messages_today': messages_today,
        'total_messages': total_messages
    }

# Helper functions for Flask integration
def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Sync wrappers for Flask compatibility
def create_tenant_sync(name: str, twilio_whatsapp_number: str, api_key: str) -> Tenant:
    return run_async(create_tenant(name, twilio_whatsapp_number, api_key))

def get_tenant_by_api_key_sync(api_key: str) -> Optional[Tenant]:
    return run_async(get_tenant_by_api_key(api_key))

def get_tenant_by_whatsapp_number_sync(whatsapp_number: str) -> Optional[Tenant]:
    return run_async(get_tenant_by_whatsapp_number(whatsapp_number))

def get_all_tenants_sync() -> List[Tenant]:
    return run_async(get_all_tenants())

def create_conversation_sync(tenant_id: str, whatsapp_user_id: str) -> Conversation:
    return run_async(create_conversation(tenant_id, whatsapp_user_id))

def get_conversation_sync(tenant_id: str, whatsapp_user_id: str) -> Optional[Conversation]:
    return run_async(get_conversation(tenant_id, whatsapp_user_id))

def get_conversation_by_id_sync(conversation_id: str) -> Optional[Conversation]:
    return run_async(get_conversation_by_id(conversation_id))

def get_conversations_by_tenant_sync(tenant_id: str) -> List[Conversation]:
    return run_async(get_conversations_by_tenant(tenant_id))

def get_recent_conversations_sync(limit: int = 10) -> List[Conversation]:
    return run_async(get_recent_conversations(limit))

def update_conversation_last_message_sync(conversation_id: str, timestamp: datetime) -> Conversation:
    return run_async(update_conversation_last_message(conversation_id, timestamp))

def create_message_sync(
    conversation_id: str,
    tenant_id: str,
    message_sid: str,
    sender_type: str,
    body: Optional[str] = None,
    media_url: Optional[str] = None
) -> Message:
    return run_async(create_message(conversation_id, tenant_id, message_sid, sender_type, body, media_url))

def get_messages_by_conversation_sync(conversation_id: str) -> List[Message]:
    return run_async(get_messages_by_conversation(conversation_id))

def get_recent_messages_sync(limit: int = 10) -> List[Message]:
    return run_async(get_recent_messages(limit))

def get_messages_today_sync() -> List[Message]:
    return run_async(get_messages_today())

def get_stats_sync():
    return run_async(get_stats())

def connect_db_sync():
    return run_async(connect_db())

def disconnect_db_sync():
    return run_async(disconnect_db())