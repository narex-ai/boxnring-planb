# Glovy API Documentation

FastAPI-based REST API for the Glovy AI Agent backend.

## Base URL

```
http://localhost:8000
```

## Endpoints

### Root

**GET** `/`

Returns basic API information.

**Response:**
```json
{
  "message": "Glovy AI Agent API",
  "status": "running",
  "version": "1.0.0"
}
```

### Health Check

**GET** `/health`

Check the health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "supabase_connected": true,
  "subscription_active": true,
  "environment": "development"
}
```

### Status

**GET** `/status`

Get detailed status of the Glovy service.

**Response:**
```json
{
  "running": true,
  "supabase_connected": true,
  "subscription_active": true,
  "environment": "development",
  "glovy_persona": "glovy"
}
```

### Webhook (Supabase)

**POST** `/webhook/message`

Webhook endpoint for receiving message events from Supabase. Can be configured in Supabase Dashboard → Database → Webhooks.

**Request Body:**
```json
{
  "type": "INSERT",
  "record": {
    "id": "uuid",
    "match_id": "uuid",
    "sender_id": "uuid",
    "sender_role": "A",
    "body": "Message content",
    "message_type": "text",
    "is_whisper": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Response:**
```json
{
  "status": "accepted",
  "message_id": "uuid"
}
```

### Process Message (Manual)

**POST** `/process-message`

Manually trigger message processing (useful for testing).

**Request Body:**
```json
{
  "id": "uuid",
  "match_id": "uuid",
  "sender_id": "uuid",
  "sender_role": "A",
  "body": "Message content",
  "message_type": "text",
  "is_whisper": false
}
```

**Response:**
```json
{
  "status": "processing",
  "message_id": "uuid"
}
```

## Real-time Processing

The service automatically subscribes to Supabase real-time changes on the `messages` table. When a new message is inserted:

1. The real-time subscription receives the event
2. Message is processed asynchronously
3. Glovy generates a response if needed
4. Response is inserted back into Supabase

## Frontend Integration

### Option 1: Real-time Subscription (Recommended)

The backend automatically listens to Supabase real-time events. No API calls needed from the frontend.

### Option 2: Webhook

Configure Supabase webhook to call `/webhook/message` when messages are inserted.

### Option 3: Manual Processing

Frontend can call `/process-message` to manually trigger processing (not recommended for production).

## CORS Configuration

The API is configured to allow CORS from all origins in development. For production, update the CORS middleware in `app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid payload)
- `500` - Internal Server Error
- `503` - Service Unavailable (processor not initialized)

## Testing

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Status
curl http://localhost:8000/status

# Process message manually
curl -X POST http://localhost:8000/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-id",
    "match_id": "match-id",
    "sender_role": "A",
    "body": "Test message"
  }'
```

### Using Python

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Process message
response = requests.post(
    "http://localhost:8000/process-message",
    json={
        "id": "test-id",
        "match_id": "match-id",
        "sender_role": "A",
        "body": "Test message"
    }
)
print(response.json())
```

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

All configuration is managed through environment variables in `.env` file. See `.env.example` for required variables.

## Deployment

For production deployment:

1. Set `ENVIRONMENT=production` in `.env`
2. Configure proper CORS origins
3. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)
4. Set up proper logging and monitoring
5. Configure reverse proxy (nginx, etc.)

Example with Gunicorn:
```bash
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

