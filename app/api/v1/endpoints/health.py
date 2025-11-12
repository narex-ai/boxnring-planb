"""
Health check and status endpoints.
"""
from fastapi import APIRouter, Depends
from app.core.config import settings
from app.api.v1.dependencies import get_app_state

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Glovy AI Agent API",
        "status": "running",
        "version": "1.0.0"
    }


@router.get("/health")
async def health_check(app_state: dict = Depends(get_app_state)):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "supabase_connected": app_state.get("supabase_client") is not None,
        "subscription_active": app_state.get("subscription") is not None,
        "environment": settings.environment
    }


@router.get("/status")
async def get_status(app_state: dict = Depends(get_app_state)):
    """Get current status of the Glovy service."""
    return {
        "running": app_state.get("running", False),
        "supabase_connected": app_state.get("supabase_client") is not None,
        "subscription_active": app_state.get("subscription") is not None,
        "environment": settings.environment,
        "glovy_persona": settings.glovy_persona
    }

