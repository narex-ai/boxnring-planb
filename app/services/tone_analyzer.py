"""
Tone analysis module for detecting sentiment and emotional tone in messages.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal
from app.core.config import settings
from app.services.behavior_detector import BehaviorDetector
import logging
import time

logger = logging.getLogger(__name__)


class ToneAnalysis(BaseModel):
    """Structured output for tone analysis."""
    tone: Literal["positive", "negative", "neutral", "confused", "excited", "frustrated"] = Field(
        description="The emotional tone of the message"
    )
    intensity: float = Field(
        description="Intensity of the tone (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    requires_response: bool = Field(
        description="Whether this message requires or would benefit from Glovy's response"
    )
    response_urgency: Literal["low", "medium", "high"] = Field(
        description="How urgent it is for Glovy to respond"
    )
    context: str = Field(
        description="Brief context about why this tone was detected"
    )
    detected_behavior: Literal[
        "none", 
        "interruption", 
        "contempt_or_insult", 
        "stonewalling_or_withdrawal", 
        "positive_behavior",
        "escalation",
        "pattern_repetition"
    ] = Field(
        default="none",
        description="Specific behavior pattern detected"
    )
    escalation_tier: Literal["none", "low", "moderate", "severe"] = Field(
        default="none",
        description="Escalation level if applicable"
    )


class ToneAnalyzer:
    """Analyzes the tone and sentiment of messages."""
    
    def __init__(self):
        """Initialize the tone analyzer with LLM - using faster model for latency."""
        # Use faster model for tone analysis to reduce latency
        model = getattr(settings, "google_model", "gemini-1.5-flash")
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=0.2,  # Lower temperature for more consistent analysis
            google_api_key=settings.google_api_key,
            max_output_tokens=200  # Limit tokens for faster response
        )
        self.parser = PydanticOutputParser(pydantic_object=ToneAnalysis)
        self.behavior_detector = BehaviorDetector()  # Fast pattern-based detection
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing emotional tone and detecting relationship communication patterns.

Analyze the message and conversation context to detect:

BEHAVIORS TO DETECT:
1. interruption - One person cutting off the other mid-sentence
2. contempt_or_insult - Name-calling, insults, sarcasm, eye-rolls, dismissive language
3. stonewalling_or_withdrawal - Silent treatment, shutting down, refusing to engage
4. positive_behavior - Active listening, "I feel" statements, mirroring, validation
5. escalation - Conversation heating up, volume increasing, threats
6. pattern_repetition - Same argument repeating, going in circles

ESCALATION TIERS:
- low: Minor tension, slight defensiveness
- moderate: Raised voices, frustration building, some contempt
- severe: Threats, extreme contempt, complete withdrawal, "I'm done" language

Glovy is a relationship coach who intervenes when:
- Communication patterns break down (interruption, contempt, stonewalling)
- Positive behaviors need reinforcement
- Escalation needs de-escalation
- Patterns repeat and need breaking

{format_instructions}"""),
            ("human", "Analyze this message and context:\n\n{message}")
        ])
    
    def analyze(self, message_body: str, conversation_context: list = None) -> ToneAnalysis:
        """
        Analyze the tone of a message - optimized for low latency.
        Uses fast pattern detection first, then LLM if needed.
        
        Args:
            message_body: The text content of the message
            conversation_context: Optional list of recent messages for context
            
        Returns:
            ToneAnalysis object with tone details
        """
        start_time = time.time()
        
        try:
            # OPTIMIZATION: Fast pattern-based behavior detection first
            detected_behavior, escalation_tier = self.behavior_detector.detect_behavior(
                message_body, 
                conversation_context or []
            )
            
            # If we detected a clear behavior, use it and do minimal LLM analysis
            if detected_behavior and detected_behavior != "none":
                # Quick LLM call just for tone/intensity (smaller prompt)
                context_str = message_body
                if conversation_context:
                    context_str += f"\nContext: {conversation_context[-2:]}"  # Only last 2
                
                prompt = self.prompt_template.format_messages(
                    message=context_str,
                    format_instructions=self.parser.get_format_instructions()
                )
                
                response = self.llm.invoke(prompt)
                analysis = self.parser.parse(response.content)
                
                # Override with detected behavior
                analysis.detected_behavior = detected_behavior
                analysis.escalation_tier = escalation_tier
                
                # Determine if response needed based on behavior
                if detected_behavior in ["interruption", "contempt_or_insult", "stonewalling_or_withdrawal", "escalation"]:
                    analysis.requires_response = True
                    analysis.response_urgency = "high" if escalation_tier == "severe" else "medium"
                elif detected_behavior == "positive_behavior":
                    analysis.requires_response = True
                    analysis.response_urgency = "low"
                elif detected_behavior == "pattern_repetition":
                    analysis.requires_response = True
                    analysis.response_urgency = "medium"
                
                elapsed = time.time() - start_time
                logger.info(f"Tone analysis (fast path) in {elapsed:.2f}s: {detected_behavior}")
                return analysis
            
            # Fallback to full LLM analysis for ambiguous cases
            context_str = ""
            if conversation_context:
                context_str = "\n\nRecent conversation context:\n"
                for msg in conversation_context[-3:]:  # Reduced from 5 to 3
                    role = msg.get("sender_role", "Unknown")
                    body = msg.get("body", "")
                    context_str += f"{role}: {body}\n"
            
            prompt = self.prompt_template.format_messages(
                message=message_body + context_str,
                format_instructions=self.parser.get_format_instructions()
            )
            
            response = self.llm.invoke(prompt)
            analysis = self.parser.parse(response.content)
            
            # Set detected behavior from LLM if not set
            if not hasattr(analysis, 'detected_behavior') or analysis.detected_behavior == "none":
                analysis.detected_behavior = detected_behavior or "none"
                analysis.escalation_tier = escalation_tier or "none"
            
            elapsed = time.time() - start_time
            logger.info(f"Tone analysis (LLM) in {elapsed:.2f}s: {analysis.tone} (intensity: {analysis.intensity:.2f})")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing tone: {e}")
            # Return default neutral tone on error
            return ToneAnalysis(
                tone="neutral",
                intensity=0.5,
                requires_response=False,
                response_urgency="low",
                context="Error in tone analysis, defaulting to neutral",
                detected_behavior="none",
                escalation_tier="none"
            )


