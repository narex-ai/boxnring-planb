"""
Message processing endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from langchain_core.messages import human
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.prompts.quick_choices import SYSTEM_PROMPT, build_human_message
from app.api.v1.dependencies import get_app_state

import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook/message")
async def webhook_message(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    app_state: dict = Depends(get_app_state)
):
    """
    Webhook endpoint for receiving messages (alternative to real-time subscription).
    Can be used if Supabase webhooks are configured.
    """
    try:
        event_type = payload.get("type") or payload.get("eventType")
        
        if event_type != "INSERT":
            return {"status": "ignored", "reason": "not_insert_event"}
        
        new_record = payload.get("record") or payload.get("new")
        if not new_record:
            raise HTTPException(status_code=400, detail="No record in payload")
        
        # Process message in background
        message_processor = app_state.get("message_processor")
        if message_processor:
            background_tasks.add_task(
                message_processor.process_message,
                new_record
            )
        
        return {"status": "accepted", "message_id": new_record.get("id")}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class QuickChoicesRequest(BaseModel):
    """Request model for quick-choices endpoint."""
    match_id: str
    sender_id: str
    sender_role: str


@router.post("/quick-choices")
async def process_message_manual(
    request: QuickChoicesRequest,
    app_state: dict = Depends(get_app_state)
):
    """
    Generate quick reply message suggestions based on recent conversation.
    Returns a list of recommended reply messages that the sender can choose from.
    """

    try:
        supabase_client = app_state.get("supabase_client")
        if not supabase_client:
            raise HTTPException(status_code=503, detail="Supabase client not initialized")
        match = supabase_client.get_match(request.match_id)
        if not match:
            raise HTTPException(status_code=404, detail=f"Match {request.match_id} not found")
                # Get profiles
        initiator = supabase_client.get_profile(match.get("initiator_id"))
        invitee = supabase_client.get_profile(match.get("invitee_id"))
        if not initiator or not invitee:
            raise HTTPException(status_code=404, detail="Initiator or invitee not found")
        recent_messages = supabase_client.get_recent_messages(
            request.match_id, 
            limit=20
        )
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.7,
            google_api_key=settings.google_api_key,
            max_output_tokes=500
        )

        
        match_metadata = match.get("metadata", {})
        initiator_metadata = match_metadata.get("initiator", [])
        invitee_metadata = match_metadata.get("invitee", [])
            
        human_message = build_human_message(
            initiator_name=initiator.get("full_name", "Initiator"),
            invitee_name=invitee.get("full_name", "Invitee"),
            match_subject=match.get("subject", ""),
            initiator_metadata=initiator_metadata,
            invitee_metadata=invitee_metadata,
            conversation_history=recent_messages,
            sender_role=request.sender_role
        )    

        prompt = ChatPromptTemplate.from_messages([
            ("system",SYSTEM_PROMPT),
            ("human", "{message}")
        ])

        response = llm.invoke(prompt.format_messages(message=human_message))

        choices = json.loads(response.content)
        return {"status": "success","data":choices}
        
    except Exception as e:
        logger.error(f"Error generating quick choices: {e}", exc_info=True)
        # Return default suggestions on error
        return {"status": "warning",
        "data": [
            "I hear what you're saying and that makes sense.",
            "What part of that feels most important to you?",
            "I'm sorry if this is causing you some stress.",
            "That is fair, but I see things a little differently."
        ]}