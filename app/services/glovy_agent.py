"""
Glovy AI Agent - The witty and smart AI coach for facilitating conversations.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.db.supabase import SupabaseClient
from app.services.response_templates import ResponseTemplates
from app.prompts import glovy_whisper, glovy_message
import logging
import time

try:
    import mem0
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    mem0 = None

logger = logging.getLogger(__name__)


class GlovyAgent:
    """Glovy AI Agent that participates in real-time chat sessions."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """Initialize Glovy agent with LLM and memory."""
        self.supabase = supabase_client
        # Use faster model for response generation to meet latency requirements
        model = getattr(settings, 'glovy_response_model', getattr(settings, 'google_model', 'gemini-2.5-flash'))
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.8,  # Higher temperature for more creative/witty responses
            google_api_key=settings.google_api_key,
            max_tokens=5120
        )
        
        # Initialize Mem0 for long-term memory
        self.memory = None
        if MEM0_AVAILABLE and settings.mem0_api_key:
            try:
                self.memory = mem0.Mem0(api_key=settings.mem0_api_key)
                logger.info("Mem0 memory initialized")
            except Exception as e:
                logger.warning(f"Mem0 initialization failed: {e}")
        elif not MEM0_AVAILABLE:
            logger.info("Mem0 not available (package not installed)")
        
        # Conversation memory per match
        self.match_memories: Dict[str, ConversationBufferMemory] = {}
        
        # Build Glovy's persona prompt
        self._build_persona_prompt()
    
    def _build_persona_prompt(self):
        """Build Glovy's persona and system prompt based on design specifications."""
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", glovy_message.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
    
    def _get_or_create_memory(self, match_id: str) -> ConversationBufferMemory:
        """Get or create conversation memory for a match."""
        if match_id not in self.match_memories:
            self.match_memories[match_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        return self.match_memories[match_id]
    
    def _get_match_context(self, match: Dict[str, Any], profiles: Dict[str, Dict[str, Any]]) -> str:
        """Build context string about the match and participants."""
        initiator_id = match.get("initiator_id")
        invitee_id = match.get("invitee_id")
        
        initiator = profiles.get(initiator_id, {})
        invitee = profiles.get(invitee_id, {})
        
        context = f"Conversation Context:\n"
        context += f"Subject: {match.get('subject', 'General conversation')}\n"
        context += f"Participant A (Initiator): {initiator.get('full_name', 'Unknown')}\n"
        context += f"Participant B (Invitee): {invitee.get('full_name', 'Unknown')}\n"
        
        metadata = match.get("metadata", {})
        if metadata:
            context += f"Match metadata: {metadata}\n"
        
        return context
    
    def _retrieve_memories(self, match_id: str, query: str) -> List[str]:
        """Retrieve relevant memories from Mem0."""
        if not self.memory:
            return []
        
        try:
            memories = self.memory.search(query=query, user_id=match_id, limit=3)
            return [mem.get("memory", "") for mem in memories if mem.get("memory")]
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []
    
    def _store_memory(self, match_id: str, memory_text: str):
        """Store a memory in Mem0."""
        if not self.memory:
            return
        
        try:
            self.memory.add(
                memory=memory_text,
                user_id=match_id
            )
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
    
    def generate_response(
        self,
        match_id: str,
        current_message: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        match: Dict[str, Any],
        profiles: Dict[str, Dict[str, Any]],
        tone_analysis: Any
    ) -> Optional[str]:
        """
        Generate Glovy's response to the current message.
        Optimized for low latency: uses templates when possible, LLM when needed.
        """
        start_time = time.time()
        
        try:
            behavior = getattr(tone_analysis, 'detected_behavior', 'none')
            escalation_tier = getattr(tone_analysis, 'escalation_tier', 'none')
            
            # OPTIMIZATION: Use templates for common interventions (instant response)
            if ResponseTemplates.should_use_template(behavior, escalation_tier):
                template_response = ResponseTemplates.get_intervention_response(
                    behavior, 
                    escalation_tier,
                    is_whisper=False
                )
                if template_response:
                    elapsed = time.time() - start_time
                    logger.info(f"Glovy template response in {elapsed:.2f}s for match {match_id}")
                    return template_response
            
            # For complex situations, use LLM (but still optimized)
            return self._generate_llm_response(
                match_id, current_message, conversation_history, 
                match, profiles, tone_analysis, start_time
            )
            
        except Exception as e:
            logger.error(f"Error generating Glovy response: {e}")
            return None
    
    def _generate_llm_response(
        self,
        match_id: str,
        current_message: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        match: Dict[str, Any],
        profiles: Dict[str, Dict[str, Any]],
        tone_analysis: Any,
        start_time: float
    ) -> Optional[str]:
        """Generate response using LLM for complex situations."""
        try:
            # Get conversation memory
            memory = self._get_or_create_memory(match_id)
            
            # Build minimal context (optimize for speed)
            match_context = self._get_match_context(match, profiles)
            
            # Only retrieve memories if needed
            behavior = getattr(tone_analysis, 'detected_behavior', 'none')
            if behavior not in ['positive_behavior', 'none']:
                query = f"{current_message.get('body', '')} {tone_analysis.context}"
                relevant_memories = self._retrieve_memories(match_id, query)
                memory_context = "\n".join(relevant_memories[:2]) if relevant_memories else ""
            else:
                memory_context = ""
            
            # Build minimal conversation history (last 5 messages for speed)
            chat_history = []
            for msg in conversation_history[-5:]:
                role = msg.get("sender_role", "Unknown")
                body = msg.get("body", "")
                if role == "Glovy":
                    chat_history.append(("assistant", body))
                else:
                    chat_history.append(("human", f"{role}: {body}"))
            
            # Build concise input prompt
            current_role = current_message.get("sender_role", "Unknown")
            current_body = current_message.get("body", "")
            
            input_text = f"Behavior: {behavior}, Escalation: {tone_analysis.escalation_tier}\n"
            if memory_context:
                input_text += f"Context: {memory_context}\n"
            input_text += f"{current_role}: {current_body}\n\n"
            input_text += "Generate Glovy's response (≤2 sentences, witty, constructive)."
            
            # Create chain
            chain = LLMChain(
                llm=self.llm,
                prompt=self.prompt_template,
                memory=memory,
                verbose=False
            )
            
            # Generate response
            response = chain.run(input=input_text)
            
            elapsed = time.time() - start_time
            logger.info(f"Glovy LLM response in {elapsed:.2f}s for match {match_id}")
            
            if elapsed > 3.0:
                logger.warning(f"Response time exceeded 3s: {elapsed:.2f}s")
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return None


    def generate_message(
        self,
        match: Dict[str, Any],
        initiator: Dict[str, Any],
        invitee: Dict[str, Any],
        recent_messages: List[Dict[str, Any]],
        new_message: Dict[str, Any],
        trigger: str
    ) -> str:
        """
        Generate Glovy's response to the current message.
        Optimized for low latency: uses templates when possible, LLM when needed.
        
        Args:
            match: Match dictionary with subject, metadata, etc.
            initiator: Initiator profile dictionary
            invitee: Invitee profile dictionary
            recent_messages: List of recent conversation messages
            new_message: The new message to analyze
            trigger: The Glovy Trigger
        Returns:
            Glovy Broadcast Message as string
        """
        start_time = time.time()
        
        try:
            # Extract metadata
            match_metadata = match.get("metadata", {})
            initiator_metadata = match_metadata.get("initiator", [])
            invitee_metadata = match_metadata.get("invitee", [])
            
            # Build human message
            human_message = glovy_message.build_human_message(
                initiator_name=initiator.get("full_name", "Initiator"),
                invitee_name=invitee.get("full_name", "Invitee"),
                match_subject=match.get("subject", ""),
                initiator_metadata=initiator_metadata,
                invitee_metadata=invitee_metadata,
                recent_messages=recent_messages,
                new_message=new_message,
                initiator_id=match.get("initiator_id"),
                invitee_id=match.get("invitee_id"),
                trigger=trigger
            )
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", glovy_message.SYSTEM_PROMPT),
                ("human", "{message}")
            ]).format_messages(message=human_message)
            # Invoke LLM 
            response = self.llm.invoke(prompt)

            print("______________________________________")
            print(response)
            print("______________________________________")

            elapsed = time.time() - start_time
            logger.info(f"Glovy Message generated in {elapsed:.2f}s: message={response.content}")
            
            # return glovy message
            return response.content
            
        except Exception as e:
            logger.error(f"Error glovy message: {e}", exc_info=True)
            # Return None on error
            return None

    def generate_whisper(
        self,
        match: Dict[str, Any],
        initiator: Dict[str, Any],
        invitee: Dict[str, Any],
        recent_messages: List[Dict[str, Any]],
        new_message: Dict[str, Any]
    ) -> str:
        """
        Generate Glovy's whisper to the current message.
        Optimized for low latency: uses templates when possible, LLM when needed.
        
        Args:
            match: Match dictionary with subject, metadata, etc.
            initiator: Initiator profile dictionary
            invitee: Invitee profile dictionary
            recent_messages: List of recent conversation messages
            new_message: The new message to analyze
        Returns:
            Glovy Whisper Message as string
        """
        start_time = time.time()
        
        try:
            # Extract metadata
            match_metadata = match.get("metadata", {})
            initiator_metadata = match_metadata.get("initiator", [])
            invitee_metadata = match_metadata.get("invitee", [])
            
            # Build human message
            human_message = glovy_whisper.build_human_message(
                initiator_name=initiator.get("full_name", "Initiator"),
                invitee_name=invitee.get("full_name", "Invitee"),
                match_subject=match.get("subject", ""),
                initiator_metadata=initiator_metadata,
                invitee_metadata=invitee_metadata,
                recent_messages=recent_messages,
                new_message=new_message,
                initiator_id=match.get("initiator_id"),
                invitee_id=match.get("invitee_id"),
            )
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", glovy_whisper.SYSTEM_PROMPT),
                ("human", "{message}")
            ]).format_messages(message=human_message)
            # Invoke LLM 
            response = self.llm.invoke(prompt)

            print("______________________________________")
            print(response)
            print("______________________________________")

            elapsed = time.time() - start_time
            logger.info(f"Glovy Whisper generated in {elapsed:.2f}s: message={response.content}")
            
            # return glovy message
            return response.content
            
        except Exception as e:
            logger.error(f"Error glovy message: {e}", exc_info=True)
            # Return None on error
            return None