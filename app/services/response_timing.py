"""
Response timing logic to decide when Glovy should interject in conversations.
Handles phases: pre_match_intro, live, escalation, wrap_up

Note: This module is currently not used but kept for future reference.
The tone analyzer now returns trigger strings instead of ToneAnalysis objects.
"""
from typing import Dict, List, Any, Literal
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ResponseTiming:
    """Determines optimal timing for Glovy's responses based on phases and escalation."""
    
    def __init__(self):
        """Initialize response timing logic."""
        self.min_messages = settings.glovy_min_messages_before_response
        self.response_threshold = settings.glovy_response_threshold
    
    def get_match_phase(self, match: Dict[str, Any]) -> Literal["pre_match_intro", "live", "escalation", "wrap_up"]:
        """Determine the current phase of the match."""
        start_time = match.get("start_time")
        end_time = match.get("end_time")
        
        if not start_time:
            return "pre_match_intro"
        
        # Check if match has ended
        if end_time:
            return "wrap_up"
        
        # For now, assume "live" if match has started
        # In future, could check duration, message count, etc.
        return "live"
    
    def should_respond(
        self,
        trigger: str,
        conversation_history: List[Dict[str, Any]],
        match: Dict[str, Any]
    ) -> bool:
        """
        Determine if Glovy should respond based on trigger, context, timing, and phase.
        
        Args:
            trigger: Trigger string from tone analyzer (e.g., "silent", "contempt_or_insult", etc.)
            conversation_history: Recent messages in the conversation
            match: Match details
            
        Returns:
            True if Glovy should respond, False otherwise
        """
        phase = self.get_match_phase(match)
        
        # If trigger is "silent", don't respond
        if trigger == "silent":
            logger.debug("Trigger is 'silent' - no response needed")
            return False
        
        # High-priority triggers always require response
        high_priority_triggers = [
            "attack_human",
            "contempt_or_insult",
            "stonewalling_or_withdrawal",
            "defensiveness",
            "direct_request_for_help"
        ]
        if trigger in high_priority_triggers:
            logger.debug(f"High-priority trigger detected: {trigger}")
            return True
        
        # Phase-specific logic
        if phase == "pre_match_intro":
            # Can respond early in intro phase for most triggers
            return trigger != "silent"
        
        if phase == "wrap_up":
            # Minimal responses in wrap-up - only high priority
            return trigger in high_priority_triggers
        
        # Live phase - standard logic
        # Check minimum message count (skip for high urgency triggers)
        if trigger not in high_priority_triggers:
            if len(conversation_history) < self.min_messages:
                logger.debug(f"Not enough messages yet ({len(conversation_history)} < {self.min_messages})")
                return False
        
        # Check if Glovy has responded too recently (except for high priority triggers)
        if trigger not in high_priority_triggers:
            if self._glovy_responded_recently(conversation_history):
                logger.debug("Glovy responded recently, skipping")
                return False
        
        # Check for specific scenarios that require response
        if self._requires_intervention(trigger, conversation_history):
            logger.debug("Intervention required based on scenario")
            return True
        
        # Default: respond if trigger is not "silent"
        return True
    
    def _glovy_responded_recently(self, conversation_history: List[Dict[str, Any]], lookback: int = 3) -> bool:
        """Check if Glovy has responded in the last N messages."""
        recent_messages = conversation_history[-lookback:]
        for msg in recent_messages:
            if msg.get("sender_role") == "Glovy":
                return True
        return False
    
    def _requires_intervention(
        self,
        trigger: str,
        conversation_history: List[Dict[str, Any]]
    ) -> bool:
        """Check if the conversation requires Glovy's intervention."""
        # High-priority triggers always require response
        high_priority_triggers = [
            "attack_human",
            "contempt_or_insult",
            "stonewalling_or_withdrawal",
            "defensiveness",
            "direct_request_for_help"
        ]
        if trigger in high_priority_triggers:
            return True
        
        # Triggers that indicate conversation issues
        intervention_triggers = [
            "stuck_or_looping",
            "vague_or_abstract",
            "low_energy_engagement",
            "invitee_silence",
            "initiator_silence"
        ]
        if trigger in intervention_triggers:
            return True
        
        # Check for conversation stagnation
        if self._is_conversation_stuck(conversation_history):
            return True
        
        return False
    
    def _is_conversation_stuck(self, conversation_history: List[Dict[str, Any]], lookback: int = 5) -> bool:
        """Check if conversation seems stuck or repetitive."""
        if len(conversation_history) < lookback:
            return False
        
        recent = conversation_history[-lookback:]
        
        # Check for very short messages (might indicate confusion)
        short_messages = sum(1 for msg in recent if len(msg.get("body", "").split()) < 3)
        if short_messages >= 3:
            return True
        
        # Check for repeated similar messages
        bodies = [msg.get("body", "").lower() for msg in recent]
        unique_bodies = len(set(bodies))
        if unique_bodies < len(bodies) * 0.5:  # More than 50% repetition
            return True
        
        return False


