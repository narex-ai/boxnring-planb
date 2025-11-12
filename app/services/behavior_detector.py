"""
Fast behavior detection using pattern matching for low latency.
Falls back to LLM only when patterns are ambiguous.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class BehaviorDetector:
    """Fast pattern-based behavior detection for low latency."""
    
    # Pattern definitions for common behaviors
    INTERRUPTION_PATTERNS = [
        r"wait\s+",
        r"hold\s+on",
        r"let\s+me\s+finish",
        r"you\s+always",
        r"you\s+never",
        r"stop\s+interrupting"
    ]
    
    CONTEMPT_PATTERNS = [
        r"\b(stupid|idiot|moron|dumb|ridiculous|pathetic)\b",
        r"eye\s*roll",
        r"whatever",
        r"i\s+don'?t\s+care",
        r"you'?re\s+impossible",
        r"sarcasm",
        r"obviously",
        r"of\s+course"
    ]
    
    STONEWALLING_PATTERNS = [
        r"^\.\.\.$",
        r"^\.$",
        r"fine",
        r"whatever\s+you\s+want",
        r"i'?m\s+done",
        r"i'?m\s+out",
        r"not\s+talking",
        r"silent\s+treatment"
    ]
    
    ESCALATION_PATTERNS = [
        r"divorce",
        r"break\s+up",
        r"i'?m\s+leaving",
        r"fuck\s+you",
        r"i\s+hate\s+you",
        r"you'?re\s+the\s+worst",
        r"i'?m\s+done\s+with\s+this"
    ]
    
    POSITIVE_PATTERNS = [
        r"i\s+feel\s+",
        r"i\s+understand",
        r"i\s+hear\s+you",
        r"that\s+makes\s+sense",
        r"thank\s+you\s+for",
        r"i\s+appreciate",
        r"you'?re\s+right",
        r"i\s+see\s+your\s+point"
    ]
    
    def __init__(self):
        """Initialize pattern matchers."""
        self.interruption_re = re.compile("|".join(self.INTERRUPTION_PATTERNS), re.IGNORECASE)
        self.contempt_re = re.compile("|".join(self.CONTEMPT_PATTERNS), re.IGNORECASE)
        self.stonewalling_re = re.compile("|".join(self.STONEWALLING_PATTERNS), re.IGNORECASE)
        self.escalation_re = re.compile("|".join(self.ESCALATION_PATTERNS), re.IGNORECASE)
        self.positive_re = re.compile("|".join(self.POSITIVE_PATTERNS), re.IGNORECASE)
    
    def detect_behavior(
        self, 
        message_body: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Fast pattern-based behavior detection.
        
        Returns:
            Tuple of (detected_behavior, escalation_tier)
        """
        message_lower = message_body.lower()
        
        # Check for severe escalation first (highest priority)
        if self.escalation_re.search(message_lower):
            return ("escalation", "severe")
        
        # Check for contempt/insult
        if self.contempt_re.search(message_lower):
            # Check if it's severe
            severe_indicators = ["hate", "worst", "impossible", "ridiculous"]
            if any(indicator in message_lower for indicator in severe_indicators):
                return ("contempt_or_insult", "severe")
            return ("contempt_or_insult", "moderate")
        
        # Check for stonewalling/withdrawal
        if self.stonewalling_re.search(message_lower):
            if any(phrase in message_lower for phrase in ["i'm done", "i'm out", "not talking"]):
                return ("stonewalling_or_withdrawal", "severe")
            return ("stonewalling_or_withdrawal", "moderate")
        
        # Check for interruption indicators
        if self.interruption_re.search(message_lower):
            return ("interruption", "low")
        
        # Check for positive behavior
        if self.positive_re.search(message_lower):
            return ("positive_behavior", "none")
        
        # Check for pattern repetition in conversation history
        if self._detect_repetition(conversation_history):
            return ("pattern_repetition", "moderate")
        
        return (None, None)
    
    def _detect_repetition(self, conversation_history: List[Dict[str, Any]], lookback: int = 5) -> bool:
        """Detect if conversation is repeating patterns."""
        if len(conversation_history) < lookback:
            return False
        
        recent = conversation_history[-lookback:]
        bodies = [msg.get("body", "").lower().strip() for msg in recent if msg.get("sender_role") != "Glovy"]
        
        # Check for very similar messages
        if len(bodies) >= 3:
            # Simple similarity check - same first few words
            first_words = [body.split()[:3] for body in bodies if len(body.split()) >= 3]
            if len(first_words) >= 3:
                unique_starts = len(set(tuple(words) for words in first_words))
                if unique_starts < len(first_words) * 0.5:
                    return True
        
        return False


