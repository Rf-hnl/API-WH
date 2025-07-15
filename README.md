# TWILIO-WH-MAR-IA

API multi-tenant para mensajería de WhatsApp (Twilio), usando Flask, Supabase y JWT.

## Características

*   **Multi-tenancy:** Cada tenant tiene sus propias credenciales y números de teléfono de Twilio.
*   **Autenticación JWT:** Los endpoints de la API están protegidos con JSON Web Tokens.
*   **Rate Limiting:** Protección contra ataques de fuerza bruta y abuso.
*   **Manejo de Errores Centralizado:** Respuestas de error JSON consistentes.
*   **Estructura Modular:** Código organizado con Flask Blueprints.

## Configuración

1.  **Clonar el repositorio:**

    ```bash
    git clone https://github.com/Rf-hnl/API-WH.git
    cd TWILIO-WH-MAR-IA
    ```

2.  **Crear un entorno virtual e instalar dependencias:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configurar las variables de entorno:**

    Crea un archivo `.env` a partir del ejemplo `.env.example` y rellena los valores:

    ```bash
    cp .env.example .env
    ```

    *   `DATABASE_URL`: La URL de conexión directa a tu base de datos de Supabase.
    *   `TWILIO_ACCOUNT_SID`: Tu Account SID de Twilio.
    *   `TWILIO_AUTH_TOKEN`: Tu Auth Token de Twilio.
    *   `FLASK_SECRET_KEY`: Una clave secreta segura para firmar los tokens JWT.

4.  **Crear las tablas de la base de datos:**

    ```bash
    python3 create_db.py
    ```

5.  **Ejecutar la aplicación:**

    ```bash
    flask run
    ```

## Uso

1.  **Obtener un token JWT:**

    Envía una petición `POST` a `/auth/login` con el `username` y `password` del tenant:

    ```json
    {
        "username": "demo",
        "password": "password"
    }
    ```

2.  **Enviar un mensaje:**

    Envía una petición `POST` a `/api/send` con el número de teléfono de destino y el cuerpo del mensaje. Incluye el token JWT en la cabecera `Authorization`:

    ```json
    {
        "to_number": "whatsapp:+15551234567",
        "body": "¡Hola desde la API!"
    }
    ```

    **Cabecera:** `Authorization: Bearer <tu_token_jwt>`

3.  **Obtener historial de mensajes:**

    Envía una petición `GET` a `/api/messages` con el token JWT en la cabecera `Authorization`.

## Colección de Postman

Se incluye un archivo `postman_collection.json` que puedes importar en Postman para probar los endpoints de la API.