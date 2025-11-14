"""
Main message processing pipeline for handling incoming messages and generating Glovy responses.
"""
from typing import Dict, Any, Optional
from app.db.supabase import SupabaseClient
from app.services.tone_analyzer import ToneAnalyzer
from app.services.glovy_agent import GlovyAgent
from app.services.response_timing import ResponseTiming
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes incoming messages and generates Glovy responses when appropriate."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """Initialize message processor with dependencies."""
        self.supabase = supabase_client
        self.tone_analyzer = ToneAnalyzer()
        self.glovy_agent = GlovyAgent(supabase_client)
        self.response_timing = ResponseTiming()
    
    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an incoming message and generate Glovy's response if needed.
        Optimized for 2-3 second response time.
        """
        start_time = time.time()
        
        try:
            # Skip if message is from Glovy itself
            if message.get("sender_role") == "Glovy":
                logger.debug("Skipping Glovy's own message")
                return None
            
            match_id = message.get("match_id")
            if not match_id:
                logger.warning("Message missing match_id")
                return None
            
            # Get match details
            match = self.supabase.get_match(match_id)
            if not match:
                logger.warning(f"Match {match_id} not found")
                return None
            
            invitee = self.supabase.get_profile(match.get("invitee_id"))
            initiator = self.supabase.get_profile(match.get("initiator_id"))
            if not invitee or not initiator:
                logger.warning(f"Invitee or initiator not found for match {match_id}")
                return None

            # Get conversation history
            conversation_history = self.supabase.get_recent_messages(match_id, limit=20, exclude_sender_role="Glovy")
            
            # Analyze tone to detect intervention trigger
            logger.info(f"Analyzing tone for message in match {match_id}")
            trigger = self.tone_analyzer.analyze(
                match=match,
                initiator=initiator,
                invitee=invitee,
                recent_messages=conversation_history,
                new_message=message
            )
            logger.info(f"Detected trigger: {trigger}")
            
            # If trigger is "silent", Glovy should not respond
            if trigger == "silent":
                logger.info(f"Trigger is 'silent', Glovy will not respond: {message.get('body')}")
                return None
            
            # # Get profile information
            # initiator_id = match.get("initiator_id")
            # invitee_id = match.get("invitee_id")
            # profiles = self.supabase.get_profiles([initiator_id, invitee_id])
            
            # # Generate Glovy's response
            # logger.info(f"Generating Glovy response for match {match_id}")
            # response_text = self.glovy_agent.generate_response(
            #     match_id=match_id,
            #     current_message=message,
            #     conversation_history=conversation_history,
            #     match=match,
            #     profiles=profiles,
            #     tone_analysis=tone_analysis
            # )
            
            # if not response_text:
            #     logger.warning("Glovy failed to generate response")
            #     return None
            
            # # Insert Glovy's response into Supabase
            # glovy_message = self.supabase.insert_message(
            #     match_id=match_id,
            #     body=response_text,
            #     sender_role="Glovy",
            #     persona=settings.glovy_persona
            # )
            
            # if glovy_message:
            #     elapsed = time.time() - start_time
            #     logger.info(f"Glovy response inserted for match {match_id} in {elapsed:.2f}s")
            #     if elapsed > 3.0:
            #         logger.warning(f"Total processing time exceeded 3s: {elapsed:.2f}s")
            #     return glovy_message
            # else:
            #     logger.error(f"Failed to insert Glovy response for match {match_id}")
            #     return None
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error processing message in {elapsed:.2f}s: {e}", exc_info=True)
            return None


