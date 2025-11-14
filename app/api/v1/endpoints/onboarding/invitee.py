"""
Invitee Onboarding endpoint.
"""
from ast import List
from fastapi import APIRouter, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.api.v1.dependencies import get_invitee_onboarding, _format_respond
from app.prompts.onboarding_question import SYSTEM_PROMPT, build_human_message

import logging
import random
from typing import List


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/invitee")
async def invitee():
    """
    GET endpoint for spar invitee onboarding that calls Gemini with a specific prompt
    and returns template data.
    """
    try:

        # Initialize Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=settings.google_api_key,
            temperature=0.8,
            top_p = 1.0,
            tpp_k=50,
            max_tokens=512
        )
        
        # Create the prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{message}")
        ])
    
        template = get_invitee_onboarding()
        human_message = build_human_message(template)
        prompt = prompt_template.format_messages(message = human_message)
        
        # Call Gemini (using async invoke)
        response = await llm.ainvoke(prompt)
        
        # Extract the response text
        response_text = response.content if hasattr(response, 'content') else str(response)
        respond_body = _format_respond(llm_output= response_text, template= template)

        logger.info("Spar Invitee onboarding Gemini call completed successfully")
        
        return {
            "status": "success",
            "message": "Spar Invitee onboarding completed successfully",
            "body": respond_body
        }
        
    except Exception as e:
        logger.error(f"Error in invitee onboarding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calling Gemini: {str(e)}")
    output = []
    arr = llm_output.split("\n")
    # Filter out empty strings from splitting
    arr = [line.strip() for line in arr if line.strip()]
    
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
    else:
        # Handle unexpected output format
        logger.warning(
            f"Unexpected LLM output format. Expected {len(template)} or {len(template) * 2} lines, "
            f"got {len(arr)}. Using first {min(len(arr), len(template))} items as questions."
        )
        # Use available items, pad with template values if needed
        dynamic = []
        for i in range(len(template)):
            dynamic.append({
                "question": template[i].get('question', ''),
                "whisper": template[i].get('whisper', '')
            })

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