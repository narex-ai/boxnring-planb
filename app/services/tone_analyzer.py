"""
Tone analysis module for detecting intervention triggers in messages.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field
from app.core.config import settings
from app.prompts.tone_analyzer import SYSTEM_PROMPT, build_human_message
import logging
import time
import re

logger = logging.getLogger(__name__)

# Define all possible valid outputs.
# This FORCES the model to choose one of these and nothing else.
TriggerOptions = Literal[
    "silent",
    "attack_human",
    "contempt_or_insult",
    "stonewalling_or_withdrawal",
    "defensiveness",
    "over_generalization",
    "interruption",
    "vague_or_abstract",
    "low_energy_engagement",
    "stuck_or_looping",
    "direct_request_for_help",
    "invitee_silence",
    "initiator_silence",
    "positive_behavior"
]

# Create a Pydantic model that has only one field, 
# which must be one of the options above.
class TriggerClassification(BaseModel):
    """A classification of the conversation trigger."""
    trigger: TriggerOptions = Field(description="The single trigger word or phrase classification.")

class ToneAnalyzer:
    """Analyzes messages to detect intervention triggers for Glovy."""
    
    def __init__(self):
        """Initialize the tone analyzer with LLM - using faster model for latency."""
        # Use faster model for tone analysis to reduce latency
        model = getattr(settings, "google_model", "gemini-2.5-flash")
        # Define settings to be less restrictive
        # This tells the API "Do not block content for these reasons"
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.1,  # Lower temperature for more consistent classification     
            google_api_key=settings.google_api_key,
            max_tokens=6400
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{message}")
        ])
    
    def analyze(
        self,
        match: Dict[str, Any],
        initiator: Dict[str, Any],
        invitee: Dict[str, Any],
        recent_messages: List[Dict[str, Any]],
        new_message: Dict[str, Any]
    ) -> str:
        """
        Analyze the message to detect intervention triggers.
        
        Args:
            match: Match dictionary with subject, metadata, etc.
            initiator: Initiator profile dictionary
            invitee: Invitee profile dictionary
            recent_messages: List of recent conversation messages
            new_message: The new message to analyze
            
        Returns:
            Trigger name as string (e.g., "silent", "contempt_or_insult", etc.)
        """
        start_time = time.time()
        
        try:
            # Extract metadata
            match_metadata = match.get("metadata", {})
            initiator_metadata = match_metadata.get("initiator", [])
            invitee_metadata = match_metadata.get("invitee", [])
            
            # Build human message
            human_message = build_human_message(
                initiator_name=initiator.get("full_name", "Initiator"),
                invitee_name=invitee.get("full_name", "Invitee"),
                match_subject=match.get("subject", ""),
                initiator_metadata=initiator_metadata,
                invitee_metadata=invitee_metadata,
                recent_messages=recent_messages,
                new_message=new_message,
                initiator_id=match.get("initiator_id"),
                invitee_id=match.get("invitee_id")
            )
            # Create prompt
            prompt = self.prompt_template.format_messages(message=human_message)
            
            # Invoke LLM 
            response = self.llm.invoke(prompt)

            trigger = self._extract_trigger(response.content)

            elapsed = time.time() - start_time
            logger.info(f"Tone analysis completed in {elapsed:.2f}s: trigger={trigger}")
            
            # return trigger
            return trigger
            
        except Exception as e:
            logger.error(f"Error analyzing tone: {e}", exc_info=True)
            # Return default silent on error
            return "silent"
    
    def _extract_trigger(self, llm_output: str) -> str:
        """
        Extract the trigger name from LLM output.
        The output should be a single word/phrase, but we clean it up just in case.
        
        Args:
            llm_output: Raw output from LLM
            
        Returns:
            Cleaned trigger name
        """
        # Remove any markdown formatting, quotes, or extra whitespace
        trigger = llm_output.strip()
        # Remove markdown code blocks if present
        trigger = re.sub(r'```[a-z]*\n?', '', trigger)
        trigger = re.sub(r'```', '', trigger)
        
        # Remove quotes if present
        trigger = trigger.strip('"\'')
        
        # Remove any trailing punctuation or explanation
        # Split by common separators and take first part
        trigger = trigger.split('\n')[0].split('.')[0].split(',')[0].strip()
        
        # Validate trigger is one of the expected values
        valid_triggers = [
            "silent",
            "attack_human",
            "contempt_or_insult",
            "stonewalling_or_withdrawal",
            "defensiveness",
            "over_generalization",
            "interruption",
            "vague_or_abstract",
            "low_energy_engagement",
            "stuck_or_looping",
            "direct_request_for_help",
            "invitee_silence",
            "initiator_silence",
            "positive_behavior"
        ]
        
        # If trigger matches a valid one, return it; otherwise default to silent
        if trigger.lower() in valid_triggers:
            return trigger.lower()
        
        # If it's close to a valid trigger, try to match
        trigger_lower = trigger.lower()
        for valid in valid_triggers:
            if valid in trigger_lower or trigger_lower in valid:
                return valid
        
        logger.info(f"Unexpected trigger output: '{trigger}', defaulting to 'silent'")
        return "silent"


