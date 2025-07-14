# Blueprint: Multi-Tenant WhatsApp Backend with Flask and Twilio

## Project Overview

This project implements a multi-tenant backend for a WhatsApp bot using Flask and Twilio. It is designed to manage conversations and messages for multiple distinct clients (tenants) through a single application instance.

Key functionalities include receiving incoming WhatsApp messages via webhooks, sending outgoing messages programmatically, managing conversation history per tenant, and providing a RESTful API for external integration.

## Technologies

*   **Python 3.x:** Core programming language.
*   **Flask:** Web micro-framework for building the API.
*   **Twilio WhatsApp API:** For sending and receiving WhatsApp messages.
*   **SQLAlchemy / Flask-SQLAlchemy:** ORM for database interaction.
*   **python-dotenv:** For managing environment variables.
*   **Ngrok:** (Development) For exposing the local server to the internet for webhooks.
*   **SQLite:** (Development/Example) Database.

## File Structure

```
.
├── .env
├── requirements.txt
├── app.py
├── models.py
└── db_create.py
```
## Database Models

Uses Flask-SQLAlchemy to define the database schema.

### Tenant

Represents a client/customer.

*   `id`: Primary Key (UUID).
*   `name`: Tenant name (String).
*   `twilio_whatsapp_number`: Twilio WhatsApp number assigned to the tenant (String, Unique).
*   `api_key`: API key for tenant authentication (String).
*   `created_at`, `updated_at`: Timestamps.

### Conversation

Represents an interaction between a WhatsApp user and a tenant.

*   `id`: Primary Key (UUID).
*   `tenant_id`: Foreign Key to `Tenant`.
*   `whatsapp_user_id`: WhatsApp user ID (String).
*   `last_message_at`: Timestamp of the last message.
*   `status`: Conversation status (e.g., 'open', 'closed').
*   Unique constraint on `tenant_id` and `whatsapp_user_id`.

### Message

Represents a single message within a conversation.

*   `id`: Primary Key (UUID).
*   `conversation_id`: Foreign Key to `Conversation`.
*   `tenant_id`: Foreign Key to `Tenant` (Denormalized).
*   `message_sid`: Twilio Message SID (String, Unique).
*   `sender_type`: 'user' or 'bot' (String).
*   `body`: Message text content (Text).
*   `media_url`: URL of media if included (String).
*   `timestamp`: Message timestamp.

## API Endpoints

All API endpoints require authentication via `X-API-Key` header.

*   `POST /api/tenants`: Create a new tenant.
    *   Requires `name`, `twilio_whatsapp_number`, `api_key`.
*   `POST /api/send_message`: Send an outgoing message from a tenant to a WhatsApp user.
    *   Requires `to` (WhatsApp user ID), `body`. Optional `media_url`.
*   `GET /api/conversations`: List conversations for the authenticated tenant.
*   `GET /api/conversations/<uuid:conversation_id>/messages`: Get messages for a specific conversation belonging to the authenticated tenant.

## Twilio Webhook

*   `POST /webhook/twilio`: Receives incoming messages from Twilio.
    *   Identifies the tenant based on the 'To' WhatsApp number.
    *   Finds or creates a Conversation.
    *   Saves the incoming Message.
    *   Generates a TwiML response.

## Development/Production Considerations

*   **.env:** Use `.env` for local configuration, but secure secret management for production.
*   **Dependencies:** Install via `pip install -r requirements.txt`.
*   **Database:** Use SQLite for development; migrate to PostgreSQL/MySQL for production. Utilize Flask-Migrate for schema changes.
*   **Ngrok:** Essential for local testing of Twilio webhooks during development.
*   **Security:**
    *   Do not hardcode credentials.
    *   Hash and salt API keys in production.
    *   Implement Twilio Request Validation.
    *   Sanitize and validate all user input.
*   **Scalability:**
    *   Use a production WSGI server (Gunicorn, Uvicorn) with a reverse proxy (Nginx).
    *   Consider database solutions like AWS RDS or GCP Cloud SQL.
    *   Implement task queues (Celery, Redis/RabbitMQ) for background tasks.
    *   Dockerize the application.
*   **WhatsApp Business Policies:** Adhere to Twilio and WhatsApp guidelines, especially regarding the 24-hour messaging window and template messages.
*   **Logging and Monitoring:** Implement robust logging and use monitoring tools.
*   **Error Handling:** Implement sophisticated error handling.
*   **Twilio Subaccounts:** Consider for advanced multi-tenancy management (billing, rate limits).