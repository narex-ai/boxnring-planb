"""
Prompts for onboarding questions
"""

from typing import List


SYSTEM_PROMPT = """
Generate Similar Meaning Sentences for each sentences.
no reasoning, no notes, no prefixes.
"""

def build_human_message(
    template: List
) -> str:
     """
    Build the human message template for tone analysis.
    
    Args:
        template: List of Questions
    Returns:
        Formatted human message string
    """
     return "\n".join(
            f"{option['question']}\n{option['whisper']}"
            for option in template
        )