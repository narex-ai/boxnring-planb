"""
Dependencies for API endpoints.
"""
from fastapi import Request
from typing import Dict, Any


def get_app_state(request: Request) -> Dict[str, Any]:
    """Get application state from FastAPI app instance."""
    app = request.app
    return {
        "supabase_client": getattr(app.state, "supabase_client", None),
        "message_processor": getattr(app.state, "message_processor", None),
        "subscription": getattr(app.state, "subscription", None),
        "running": getattr(app.state, "running", False)
    }

