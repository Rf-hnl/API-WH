# API Multi-Tenant de WhatsApp con Flask, Supabase y Twilio

Este proyecto proporciona una API RESTful en **Flask** para el envío y recepción de mensajes de WhatsApp mediante **Twilio**, con persistencia de datos en **Supabase** (PostgreSQL) y acceso a la base de datos a través de **Prisma**. Dispone también de una interfaz web mínima en HTML/JS para pruebas y demos.

---

## 📂 Estructura del Repositorio

```
.
├── .env                  # Variables de entorno (no versionar)
├── .gitignore            # Archivos ignorados por Git
├── README.md             # Documentación del proyecto
├── app.py                # Núcleo de la API Flask
├── prisma/
│   └── schema.prisma     # Esquema de base de datos Prisma
├── models_prisma.py      # Cliente Prisma generado
├── requirements.txt      # Dependencias Python
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── edit_tenant.html
    ├── send_message.html # Formulario de envío de WhatsApp
    └── tenants.html
```

> **Nota**: Elimina los archivos obsoletos listados en la sección “Limpieza de Repositorio” para mantenerlo ordenado.

---

## ⚙️ Instalación y Configuración

1.  **Clona el repositorio**  
    ```bash
    git clone <URL_DEL_REPO>
    cd TWILIO-WH-MAR-IA
    ```
2.  **Entorno Virtual (recomendado)**
    ```bash
    python3 -m venv venv
    source venv/bin/activate   # macOS/Linux
    # venv\Scripts\activate    # Windows
    ```
3.  **Instala dependencias**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Variables de entorno**
    Crea un archivo `.env` en la raíz con solo:
    ```dotenv
    DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
    # e.g.: postgresql://postgres:miPassword@db.mi-supabase.supabase.co:5432/postgres
    ```
    **Importante**: En producción, las credenciales de Twilio (Account SID y Auth Token) **no deben provenir del frontend ni almacenarse en `.env` en la app cliente**. Deben gestionarse en el backend o en un servicio de secretos.

5.  **Prisma**
    ```bash
    npx prisma generate
    npx prisma migrate dev --name init
    ```

---

## 🚀 Ejecución

```bash
python3 app.py
```

Luego abre `http://127.0.0.1:5000/` para ver la interfaz de prueba.

---

## 🔗 Endpoints

### 1. `POST /send_whatsapp`

Envía un mensaje de WhatsApp y lo registra en Supabase.

**Headers**

-   `Content-Type`: `application/json`
-   `X-Tenant-ID`: `<ID_DEL_TENANT>`

**Body (JSON):**

```json
{
  "account_sid": "ACxxxxxxxxxxxxxxxxxxxx",
  "auth_token": "tu_auth_token",
  "twilio_number": "whatsapp:+14155238886",
  "content_sid": "HXxxxxxxxxxxxxxxxxxxxx",
  "content_variables": "{\"1\":\"Valor1\",\"2\":\"Valor2\"}",
  "to_number": "whatsapp:+50763116918"
}
```

**Respuesta Exitosa (200):**

```json
{
  "success": true,
  "message_sid": "SMxxxxxxxxxxxxxxxxxxxx"
}
```

**Error (4xx/5xx):**

```json
{
  "success": false,
  "error": "Descripción del error"
}
```

**Ejemplo con curl**

```bash
curl -X POST http://127.0.0.1:5000/send_whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant_123" \
  -d '{
        "account_sid":"ACxxx",
        "auth_token":"tokxxx",
        "twilio_number":"whatsapp:+14155238886",
        "content_sid":"HXxxx",
        "content_variables":"{\"1\":\"12/1\",\"2\":\"3pm\"}",
        "to_number":"whatsapp:+50763116918"
      }'
```

### 2. `POST /webhook/twilio` (Stub)

Recibe notificaciones de estado o mensajes entrantes de Twilio.

```python
@app.route('/webhook/twilio', methods=['POST'])
def twilio_webhook():
    # Procesar request.form['MessageStatus'], 'From', 'Body', etc.
    return ("", 204)
```

---

## 🧹 Limpieza de Repositorio

Eliminar archivos ya no usados para evitar confusiones:

-   `app_old.py`
-   `blueprint.md`
-   `create_db.py`
-   `create_tables.sql`
-   `db_create.py`
-   `devserver.sh`
-   `index.html` (raíz)
-   `main.py`
-   `models.py`
-   `init_db.py`
-   `start_server.py`
-   `start.sh`
-   `src/index.html`

---

## 📈 Buenas Prácticas y Futuras Mejoras

1.  **Seguridad de Credenciales**: Gestionar SID/AuthToken en backend o secreto central.
2.  **Autenticación Real**: Sustituir `X-Tenant-ID` simulado por JWT u OAuth.
3.  **Webhooks Completos**: Implementar lógica para estados de entrega y mensajes entrantes.
4.  **Validación de Esquemas**: Usar Pydantic o Marshmallow.
5.  **Logging y Monitoring**: Añadir logs estructurados y alertas.
6.  **Tests**: Unitarios e integración para Twilio y Prisma.
7.  **Docker**: Conteneriza la app y la DB para despliegue.

---

## 🤝 Contribuciones

Todas las contribuciones son bienvenidas.

-   Abre un [Issue en GitHub](https://github.com/Rf-hnl/TWILIO-WH/issues) para discutir tu propuesta.
-   Realiza un [Pull Request](https://github.com/Rf-hnl/TWILIO-WH/pulls) con descripciones claras.
-   Sigue las Guías de Contribución.

---
*MIT License*
