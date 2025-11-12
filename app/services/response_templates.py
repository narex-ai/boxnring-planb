"""
Response templates for common interventions to reduce LLM latency.
These provide instant responses for detected behaviors.
"""
from typing import Optional
import random

class ResponseTemplates:
    """Pre-defined response templates for fast interventions."""
    
    INTERRUPTION_RESPONSES = [
        "Let's pause so they can finish—your turn is next.",
        "Hold up! Let them finish their thought first.",
        "Whoa there! One at a time—let's hear them out.",
        "Time out! Finish your point, then it's their turn."
    ]
    
    INTERRUPTION_WHISPERS = [
        "Jot your point; mirror first, then add it.",
        "Take a breath. Listen, then respond.",
        "Write it down if you need to—we'll get to it."
    ]
    
    CONTEMPT_RESPONSES = [
        "Flag on tone—try a respectful rephrase.",
        "Whoa, that tone won't help. Let's reset with respect.",
        "Time out! That language isn't constructive. Try 'I feel...' instead.",
        "Penalty on the play! Name the impact, not the insult."
    ]
    
    CONTEMPT_WHISPERS = [
        "Name impact, not insult. e.g., 'I felt anxious about the purchase.'",
        "Try: 'When X happens, I feel Y' instead of name-calling.",
        "Focus on your feeling, not their character."
    ]
    
    STONEWALLING_RESPONSES = [
        "I'm sensing withdrawal. Want a brief breather, or restate the last point?",
        "Check-in: Still with us? Want to pause or continue?",
        "I see you pulling back. Take a moment if needed, or let's try one more exchange.",
        "On a scale of 1 to 'throwing in the towel,' where are we? Let's reset."
    ]
    
    POSITIVE_REINFORCEMENT = [
        "BEAUTIFUL! Did you see that? An actual 'I feel' statement!",
        "Hold up, hold up! That was some solid active listening right there!",
        "That's what I'm talking about! You just turned a complaint into a request.",
        "Clear mirroring—nice. Keep that up!",
        "That's like turning water into wine, but for relationships!"
    ]
    
    ESCALATION_LOW = [
        "Slow down—one at a time.",
        "Let's take a breath. We're getting heated.",
        "Pump the brakes—let's reset the tone."
    ]
    
    ESCALATION_MODERATE = [
        "Let's try a 10-second reset breath together.",
        "Okay, emotional temperature check—we're approaching 'hangry' levels here.",
        "I'm sensing we've entered the 'loud equals right' zone. Volume doesn't win arguments."
    ]
    
    ESCALATION_SEVERE = [
        "Time-out recommended. Pause and return when ready.",
        "RED FLAG! We've entered dangerous territory. Let's step back.",
        "STOP! That language is relationship nuclear codes. Let's reset with respect.",
        "This is a private space. Take the time you need."
    ]
    
    PATTERN_REPETITION = [
        "Interesting! This is your third lap around the same argument. It's like watching NASCAR but with feelings.",
        "I'm getting déjà vu here—didn't we do this dance before? Let's try a new tune.",
        "Classic pattern alert! Same song, different verse. Time for a new approach.",
        "Okay, that round was like watching two people try to fold a fitted sheet—lots of effort, minimal progress."
    ]
    
    @staticmethod
    def get_intervention_response(
        behavior: str, 
        escalation_tier: str = "none",
        is_whisper: bool = False
    ) -> Optional[str]:
        """Get a template response for detected behavior."""
        if behavior == "interruption":
            templates = ResponseTemplates.INTERRUPTION_WHISPERS if is_whisper else ResponseTemplates.INTERRUPTION_RESPONSES
        elif behavior == "contempt_or_insult":
            templates = ResponseTemplates.CONTEMPT_WHISPERS if is_whisper else ResponseTemplates.CONTEMPT_RESPONSES
        elif behavior == "stonewalling_or_withdrawal":
            templates = ResponseTemplates.STONEWALLING_RESPONSES
        elif behavior == "positive_behavior":
            templates = ResponseTemplates.POSITIVE_REINFORCEMENT
        elif behavior == "escalation":
            if escalation_tier == "severe":
                templates = ResponseTemplates.ESCALATION_SEVERE
            elif escalation_tier == "moderate":
                templates = ResponseTemplates.ESCALATION_MODERATE
            else:
                templates = ResponseTemplates.ESCALATION_LOW
        elif behavior == "pattern_repetition":
            templates = ResponseTemplates.PATTERN_REPETITION
        else:
            return None
        
        return random.choice(templates) if templates else None
    
    @staticmethod
    def should_use_template(behavior: str, escalation_tier: str) -> bool:
        """Determine if we should use a template (fast) vs LLM (slower but more contextual)."""
        # Use templates for clear, common interventions
        # Use LLM for complex, contextual situations
        if behavior in ["interruption", "contempt_or_insult", "stonewalling_or_withdrawal"]:
            return True
        if behavior == "escalation" and escalation_tier in ["low", "moderate", "severe"]:
            return True
        if behavior == "positive_behavior":
            return True
        return False


