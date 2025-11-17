"""
Spar Initiator Onboarding endpoint.
"""
from fastapi import APIRouter, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.api.v1.dependencies import get_initiator_onboarding, _format_respond
from app.prompts.onboarding_question import SYSTEM_PROMPT, build_human_message

import logging


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/initiator")
async def initiator():
    """
    GET endpoint for spar initiator onboarding that calls Gemini with a specific prompt
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
    
        template = get_initiator_onboarding()
        human_message = build_human_message(template)
        prompt = prompt_template.format_messages(message = human_message)
        
        # Call Gemini (using async invoke)
        response = await llm.ainvoke(prompt)
        
        # Extract the response text
        response_text = response.content if hasattr(response, 'content') else str(response)
        respond_body = _format_respond(llm_output= response_text, template= template)

        logger.info("Spar Initiator Onboarding Gemini call completed successfully")
        
        return {
            "status": "success",
            "message": "Spar Initiator Onboarding Questions loaded successfully",
            "body": respond_body
        }
        
    except Exception as e:
        logger.error(f"Error in initiator onboarding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calling Gemini: {str(e)}")
