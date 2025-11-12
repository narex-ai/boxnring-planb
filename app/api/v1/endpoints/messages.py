"""
Message processing endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any
import logging
from app.api.v1.dependencies import get_app_state

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


@router.post("/process-message")
async def process_message_manual(
    message: Dict[str, Any],
    background_tasks: BackgroundTasks,
    app_state: dict = Depends(get_app_state)
):
    """
    Manually trigger message processing (for testing).
    """
    try:
        message_processor = app_state.get("message_processor")
        if not message_processor:
            raise HTTPException(status_code=503, detail="Message processor not initialized")
        
        background_tasks.add_task(
            message_processor.process_message,
            message
        )
        
        return {"status": "processing", "message_id": message.get("id")}
        
    except Exception as e:
        logger.error(f"Error processing message manually: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

