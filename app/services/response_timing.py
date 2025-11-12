"""
Response timing logic to decide when Glovy should interject in conversations.
Handles phases: pre_match_intro, live, escalation, wrap_up
"""
from typing import Dict, List, Any, Literal
from app.services.tone_analyzer import ToneAnalysis
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
        tone_analysis: ToneAnalysis,
        conversation_history: List[Dict[str, Any]],
        match: Dict[str, Any]
    ) -> bool:
        """
        Determine if Glovy should respond based on tone, context, timing, and phase.
        
        Args:
            tone_analysis: Analysis of the current message tone
            conversation_history: Recent messages in the conversation
            match: Match details
            
        Returns:
            True if Glovy should respond, False otherwise
        """
        phase = self.get_match_phase(match)
        
        # Always respond to severe escalation regardless of phase
        if hasattr(tone_analysis, 'escalation_tier') and tone_analysis.escalation_tier == "severe":
            logger.debug("Severe escalation detected - responding immediately")
            return True
        
        # Phase-specific logic
        if phase == "pre_match_intro":
            # Can respond early in intro phase
            return tone_analysis.requires_response
        
        if phase == "wrap_up":
            # Minimal responses in wrap-up
            return tone_analysis.response_urgency == "high"
        
        # Live phase - standard logic
        # Don't respond if tone analysis says not to
        if not tone_analysis.requires_response:
            logger.debug("Tone analysis indicates no response needed")
            return False
        
        # Check minimum message count (skip for high urgency behaviors)
        behavior = getattr(tone_analysis, 'detected_behavior', 'none')
        if behavior not in ["interruption", "contempt_or_insult", "stonewalling_or_withdrawal", "escalation"]:
            if len(conversation_history) < self.min_messages:
                logger.debug(f"Not enough messages yet ({len(conversation_history)} < {self.min_messages})")
                return False
        
        # Check if Glovy has responded too recently (except for severe escalation)
        if tone_analysis.response_urgency != "high":
            if self._glovy_responded_recently(conversation_history):
                logger.debug("Glovy responded recently, skipping")
                return False
        
        # Check tone intensity threshold
        if tone_analysis.intensity < self.response_threshold:
            # Still respond if urgency is high or specific behaviors detected
            if tone_analysis.response_urgency == "high" or behavior in ["interruption", "contempt_or_insult", "stonewalling_or_withdrawal"]:
                logger.debug("High urgency or critical behavior detected, responding")
                return True
            logger.debug(f"Tone intensity too low ({tone_analysis.intensity:.2f} < {self.response_threshold})")
            return False
        
        # Check for specific scenarios that require response
        if self._requires_intervention(tone_analysis, conversation_history):
            logger.debug("Intervention required based on scenario")
            return True
        
        # Default: respond if tone analysis says so and intensity is sufficient
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
        tone_analysis: ToneAnalysis,
        conversation_history: List[Dict[str, Any]]
    ) -> bool:
        """Check if the conversation requires Glovy's intervention."""
        # High urgency always requires response
        if tone_analysis.response_urgency == "high":
            return True
        
        # Negative tones often need support
        if tone_analysis.tone in ["negative", "frustrated"] and tone_analysis.intensity > 0.6:
            return True
        
        # Confusion needs clarification
        if tone_analysis.tone == "confused":
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


