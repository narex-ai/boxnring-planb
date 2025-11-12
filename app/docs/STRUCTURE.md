# Project Structure

## Folder Organization

```
PlanA-Backend/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   │
│   ├── api/                      # API routes
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── api.py            # Router aggregation
│   │       └── endpoints/        # Endpoint handlers
│   │           ├── __init__.py
│   │           ├── health.py     # Health check endpoints
│   │           └── messages.py  # Message processing endpoints
│   │
│   ├── core/                     # Core configuration
│   │   ├── __init__.py
│   │   └── config.py            # Settings and configuration
│   │
│   ├── db/                       # Database clients
│   │   ├── __init__.py
│   │   └── supabase.py          # Supabase client wrapper
│   │
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── behavior_detector.py # Fast pattern-based behavior detection
│   │   ├── tone_analyzer.py     # Tone and sentiment analysis
│   │   ├── response_templates.py # Pre-defined response templates
│   │   ├── response_timing.py   # Response timing logic
│   │   ├── glovy_agent.py       # Glovy AI agent (LLM integration)
│   │   └── message_processor.py # Main message processing pipeline
│   │
│   ├── models/                   # Database models (future use)
│   └── schemas/                  # Pydantic schemas (future use)
│
├── .env                          # Environment variables (not in git)
├── env.template                  # Environment template
├── requirements.txt              # Python dependencies
├── run.py                        # Application entry point
├── setup_env.py                  # Interactive .env setup
├── main.py                       # Legacy entry point (deprecated)
├── app.py                        # Legacy FastAPI app (deprecated)
│
└── Documentation/
    ├── README.md                 # Main documentation
    ├── QUICKSTART.md            # Quick start guide
    ├── INTEGRATION.md            # Frontend integration guide
    ├── API_DOCUMENTATION.md     # API documentation
    ├── GLOVY_IMPLEMENTATION.md  # Glovy implementation details
    ├── LATENCY_OPTIMIZATION.md  # Performance optimization guide
    └── STRUCTURE.md              # This file
```

## Import Patterns

### Configuration
```python
from app.core.config import settings
```

### Database
```python
from app.db.supabase import SupabaseClient
```

### Services
```python
from app.services.tone_analyzer import ToneAnalyzer
from app.services.glovy_agent import GlovyAgent
from app.services.message_processor import MessageProcessor
```

### API Endpoints
```python
from app.api.v1.endpoints import health, messages
```

## Module Responsibilities

### `app/core/`
- **config.py**: Application settings, environment variables, configuration management

### `app/db/`
- **supabase.py**: Supabase client initialization, database operations, query helpers

### `app/services/`
- **behavior_detector.py**: Fast regex-based behavior pattern detection
- **tone_analyzer.py**: LLM-based tone and sentiment analysis
- **response_templates.py**: Pre-defined intervention responses for low latency
- **response_timing.py**: Logic for determining when Glovy should respond
- **glovy_agent.py**: Core AI agent with LangChain, Mem0, and response generation
- **message_processor.py**: Main orchestration pipeline for message processing

### `app/api/v1/endpoints/`
- **health.py**: Health check and status endpoints
- **messages.py**: Message processing webhooks and manual triggers

### `app/main.py`
- FastAPI application setup
- Lifespan management (startup/shutdown)
- Real-time subscription setup
- CORS configuration
- Router registration

## Adding New Features

### Adding a New Service
1. Create file in `app/services/`
2. Import in `app/services/__init__.py` if needed
3. Use in `message_processor.py` or other services

### Adding a New API Endpoint
1. Create endpoint function in `app/api/v1/endpoints/`
2. Add router in `app/api/v1/api.py`
3. Endpoint will be available at `/api/v1/your-endpoint`

### Adding Configuration
1. Add to `app/core/config.py` Settings class
2. Add to `env.template`
3. Update `setup_env.py` if needed

## Migration from Old Structure

Old imports → New imports:
- `from config import settings` → `from app.core.config import settings`
- `from supabase_client import SupabaseClient` → `from app.db.supabase import SupabaseClient`
- `from tone_analyzer import ToneAnalyzer` → `from app.services.tone_analyzer import ToneAnalyzer`
- `from glovy_agent import GlovyAgent` → `from app.services.glovy_agent import GlovyAgent`
- `from message_processor import MessageProcessor` → `from app.services.message_processor import MessageProcessor`

## Running the Application

```bash
# Development
python run.py

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test status endpoint
curl http://localhost:8000/api/v1/status
```

