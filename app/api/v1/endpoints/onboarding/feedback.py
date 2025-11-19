"""
Feedback endpoint.
"""
from fastapi import APIRouter, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.api.v1.dependencies import get_feedback_onboarding, _format_respond
from app.prompts.onboarding_question import SYSTEM_PROMPT, build_human_message

import logging


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/feedback")
async def feedback():
    """
    GET endpoint for spar feedback that calls Gemini with a specific prompt
    and returns template data.
    """
    try:

        # Initialize Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=settings.google_api_key,
            temperature=0.9,
            top_p = 1.0,
            tpp_k=50,
            max_tokens=512
        )
        
        # Create the prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{message}")
        ])
    
        template = get_feedback_onboarding()
        human_message = build_human_message(template)
        prompt = prompt_template.format_messages(message = human_message)
        
        # Call Gemini (using async invoke)
        response = await llm.ainvoke(prompt)
        
        # Extract the response text
        response_text = response.content if hasattr(response, 'content') else str(response)
        respond_body = _format_respond(llm_output= response_text, template= template)

        logger.info("Spar Feedback Gemini call completed successfully")
        
        return {
            "status": "success",
            "message": "Spar Feedback completed successfully",
            "body": respond_body
        }
        
    except Exception as e:
        logger.error(f"Error in feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calling Gemini: {str(e)}")