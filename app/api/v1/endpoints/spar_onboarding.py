"""
Spar onboarding endpoint.
"""
from ast import List
from fastapi import APIRouter, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.api.v1.dependencies import get_spar_onboarding
from app.prompts.onboarding_question import SYSTEM_PROMPT, build_human_message

import logging
import random
from typing import List


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/spar-onboarding")
async def spar_onboarding():
    """
    GET endpoint for spar onboarding that calls Gemini with a specific prompt
    and returns template data.
    """
    try:

        # Initialize Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=settings.google_api_key,
            temperature=0.7,
            max_tokens=512
        )
        
        # Create the prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{message}")
        ])
    
        template = get_spar_onboarding()
        human_message = build_human_message(template)
        prompt = prompt_template.format_messages(message = human_message)
        
        # Call Gemini (using async invoke)
        response = await llm.ainvoke(prompt)
        
        # Extract the response text
        response_text = response.content if hasattr(response, 'content') else str(response)
        respond_body = _format_respond(llm_output= response_text, template= template)

        logger.info("Spar onboarding Gemini call completed successfully")
        
        return {
            "status": "success",
            "message": "Spar onboarding completed successfully",
            "body": respond_body
        }
        
    except Exception as e:
        logger.error(f"Error in spar onboarding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calling Gemini: {str(e)}")

def _format_respond(llm_output: str, template: List) -> str:
    output = []
    arr = llm_output.split("\n")
    
    if len(arr) == len(template) * 2:
        dynamic = [
            {
                "question": arr[i],
                "whisper": arr[i + 1]
            }
            for i in range(0, len(arr), 2)
        ]
    elif len(arr) == len(template):
        dynamic = [
            {
                "question": arr[i],
                "whisper": template[i]['whisper']
            }
            for i in range(0, len(arr))
        ]

    animations = ["thinking", "nod", "celebration", "sad", "idle"]

    for index, item in enumerate(template):

        # Same logic as JS
        if item.get("interaction_pattern") == "complex":
            item["custom_input"] = True

        item["question_number"] = index + 1
        item["glovy_animation"] = animations[random.randint(0, 4)]

        item["question"] = dynamic[index]["question"]
        item["whisper"] = dynamic[index]["whisper"]

        output.append(item)

    # Final output
    return output