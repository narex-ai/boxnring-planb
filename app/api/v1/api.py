"""
API v1 router aggregation.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, messages, onboarding

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(messages.router, tags=["messages"])

# Create onboarding subrouter
onboarding_router = APIRouter(prefix="/onboarding", tags=["onboarding"])
onboarding_router.include_router(onboarding.initiator.router)
onboarding_router.include_router(onboarding.invitee.router)
onboarding_router.include_router(onboarding.visitor.router)
onboarding_router.include_router(onboarding.partner.router)

api_router.include_router(onboarding_router)


