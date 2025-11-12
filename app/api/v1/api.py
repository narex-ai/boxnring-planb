"""
API v1 router aggregation.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, messages

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(messages.router, tags=["messages"])


