"""
Supabase client initialization and utilities.
"""
from supabase import create_client, Client
from app.core.config import settings
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper for Supabase client operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        logger.info("Supabase client initialized")
    
    def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get match details by ID."""
        try:
            response = self.client.table("matches").select("*").eq("id", match_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching match {match_id}: {e}")
            return None
    
    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get profile details by ID."""
        try:
            response = self.client.table("profiles").select("*").eq("id", profile_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching profile {profile_id}: {e}")
            return None

    def get_profiles(self, profile_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get multiple profiles by IDs."""
        try:
            response = self.client.table("profiles").select("*").in_("id", profile_ids).execute()
            profiles = {profile["id"]: profile for profile in response.data}
            return profiles
        except Exception as e:
            logger.error(f"Error fetching profiles: {e}")
            return {}
    
    def get_recent_messages(
        self,
        match_id: str,
        limit: int = 20,
        exclude_sender_role: Optional[str] = None,
        message_types: Optional[List[str]] = None,
        is_whisper: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages for a match.
        If limit=0, return all messages for the match.
        Optionally exclude messages from a sender_role (e.g., exclude_sender_role='Glovy').
        Optionally filter by message_types (e.g., ['intro', 'feedback']).
        Optionally filter by is_whisper (if None, don't filter; if True/False, filter by that value).
        """
        try:
            query = self.client.table("messages").select("*").eq("match_id", match_id)
            
            if exclude_sender_role:
                query = query.neq("sender_role", exclude_sender_role)
            if message_types is not None and len(message_types) > 0:
                query = query.in_("message_type", message_types)
            if is_whisper is not None:
                query = query.eq("is_whisper", is_whisper)
            
            query = query.order("created_at", desc=True)
            if limit and limit > 0:
                query = query.limit(limit)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching messages for match {match_id}: {e}")
            return []
    def insert_message(
        self,
        match_id: str,
        body: str,
        sender_role: str = "Glovy",
        persona: Optional[str] = None,
        recipient_id: Optional[str] = None,
        is_whisper: bool = False,
        message_type: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """Insert a new message from Glovy."""
        try:
            message_data = {
                "match_id": match_id,
                "sender_id": None,  # Glovy has no sender_id
                "sender_role": sender_role,
                "persona": persona or settings.glovy_persona,
                "body": body,
                "message_type": message_type,
                "is_whisper": is_whisper,
            }
            
            if recipient_id:
                message_data["recipient_id"] = recipient_id
            
            response = self.client.table("messages").insert(message_data).execute()
            if response.data:
                logger.info(f"Glovy message inserted for match {match_id}")
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error inserting Glovy message: {e}")
            return None
    
    def get_client(self) -> Client:
        """Get the underlying Supabase client."""
        return self.client


