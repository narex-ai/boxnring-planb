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
import re

logger = logging.getLogger(__name__)

def extract_choices_from_response(content: str) -> List[str]:
    """
    Extract 4 choice messages from LLM response, handling various formats:
    - JSON array: ["msg1", "msg2", "msg3", "msg4"]
    - JSON with markdown code blocks
    - Plain text with 4 sentences (newlines, numbered lists, bullets, etc.)
    
    Args:
        content: Raw response content from LLM
        
    Returns:
        List of 4 choice strings
    """
    if not content:
        return []
    
    # Step 1: Try to extract and parse as JSON
    try:
        cleaned = content.strip()
        # Remove markdown code block markers if present
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()
        
        # Try to parse as JSON
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) > 0:
            # Ensure we have exactly 4 items, pad or truncate if needed
            choices = [str(item).strip() for item in parsed[:4]]
            while len(choices) < 4:
                choices.append("")
            return choices[:4]
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass
    
    # Step 2: Try to extract JSON array from text (might be embedded)
    try:
        # Look for JSON array pattern in the text
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list) and len(parsed) > 0:
                choices = [str(item).strip() for item in parsed[:4]]
                while len(choices) < 4:
                    choices.append("")
                return choices[:4]
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Step 3: Extract plain text sentences/messages
    # Remove markdown code blocks
    cleaned = content.strip()
    cleaned = re.sub(r'^```[a-z]*\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()
    
    # Split by various delimiters and extract sentences
    lines = []
    
    # Try splitting by newlines first
    for line in cleaned.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Remove common prefixes (numbers, bullets, dashes, etc.)
        line = re.sub(r'^[\d\.\)\-\*\•]\s*', '', line)
        # Remove quotes if present
        line = re.sub(r'^["\']|["\']$', '', line)
        line = line.strip()
        if line and len(line) > 3:  # Filter out very short lines
            lines.append(line)
    
    # If we got lines from newline splitting, use them
    if lines:
        choices = lines[:4]
        while len(choices) < 4:
            choices.append("")
        return choices[:4]
    
    # Try splitting by periods followed by space (sentence boundaries)
    sentences = re.split(r'\.\s+', cleaned)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
    
    if sentences:
        choices = sentences[:4]
        while len(choices) < 4:
            choices.append("")
        return choices[:4]
    
    # Fallback: return the whole content as a single choice (shouldn't happen)
    return [cleaned[:100]] + [""] * 3

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
            limit=20,
            is_whisper=False
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
        # Extract choices from response (handles JSON, markdown, and plain text formats)
        choices = extract_choices_from_response(response.content)
        
        # Ensure we always return exactly 4 choices
        if len(choices) < 4:
            choices.extend([""] * (4 - len(choices)))
        elif len(choices) > 4:
            choices = choices[:4]
        
        return {"status": "success", "data": choices}
        
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