"""
Main message processing pipeline for handling incoming messages and generating Glovy responses.
"""
from typing import Dict, Any, Optional
from app.db.supabase import SupabaseClient
from app.services.tone_analyzer import ToneAnalyzer
from app.services.glovy_agent import GlovyAgent
from app.services.response_timing import ResponseTiming
from app.core.config import settings
from supabase import AsyncClient
import logging
import time
import asyncio

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes incoming messages and generates Glovy responses when appropriate."""
    
    def __init__(self, supabase_client: SupabaseClient, supabase_async: Optional[AsyncClient] = None):
        """Initialize message processor with dependencies."""
        self.supabase = supabase_client
        self.supabase_async = supabase_async
        self.tone_analyzer = ToneAnalyzer()
        self.glovy_agent = GlovyAgent(supabase_client)
        self.response_timing = ResponseTiming()
        # Cache channels per match_id to avoid re-subscribing
        self._channel_cache: Dict[str, Any] = {}
    
    async def _get_or_create_channel(self, match_id: str):
        """
        Get or create a channel for the match synchronously.
        Returns channel object (subscription happens in background).
        """
        if not self.supabase_async:
            return None
        
        try:
            # Check if we have a cached channel that's still subscribed
            if match_id in self._channel_cache:
                channel = self._channel_cache[match_id]
                # Check if channel is still in a valid state
                channel_state = None
                if hasattr(channel, 'state'):
                    channel_state = channel.state
                elif hasattr(channel, 'channel_state'):
                    channel_state = channel.channel_state
                
                # If channel is still subscribed/joined, reuse it
                if channel_state in ['joined', 'subscribed', 'attached']:
                    return channel
                else:
                    # Channel is no longer valid, remove from cache
                    del self._channel_cache[match_id]
            
            # Create new channel synchronously
            channel = self.supabase_async.realtime.channel(f"typing:{match_id}")
            
            # Start subscription in background (non-blocking)
            def on_subscribe(status, err=None):
                if status == "SUBSCRIBED":
                    logger.debug(f"Channel subscribed for match {match_id}")
                elif status in ["CHANNEL_ERROR", "TIMED_OUT", "CLOSED"]:
                    logger.debug(f"Channel subscription status for match {match_id}: {status}, err: {err}")
            
            # Start subscription asynchronously in background
            await channel.subscribe(on_subscribe)
            
            # Cache the channel immediately
            self._channel_cache[match_id] = channel
            
            return channel
            
        except Exception as e:
            logger.warning(f"Failed to get/create channel for match {match_id}: {e}")
            # Remove from cache if it exists
            self._channel_cache.pop(match_id, None)
            return None
    
    async def _send_typing_broadcast(self, channel, message_id: Optional[str], is_typing: bool, user_id: Optional[str]):
        """
        Send broadcast message to notify frontend about Glovy's typing status.
        Fire-and-forget: errors are logged but don't affect message processing.
        
        Args:
            channel: The Supabase realtime channel to send the broadcast on
            message_id: The message ID to include in the broadcast
            is_typing: Whether Glovy is currently typing
        """
        if not channel:
            return
        
        try:
            # Send broadcast using send_broadcast method (positional arguments)
            await channel.send_broadcast(
                "glovy-typing",
                {
                    "message_id": message_id or "",
                    "is_typing": is_typing,
                    "user_id": user_id or None
                }
            )
            
            logger.info(f"Sent glovy-typing broadcast, is_typing={is_typing}, message_id={message_id}")
            
        except Exception as e:
            # Log error but don't fail - broadcast is non-critical
            logger.warning(f"Failed to send typing broadcast: {e}")

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an incoming message and generate Glovy's response if needed.
        Optimized for 2-3 second response time.
        """
        start_time = time.time()
        match_id = None
        glovy_message = None
        incoming_message_id = None
        should_send_stop_broadcast = False
        
        try:
            
            match_id = message.get("match_id")
            if not match_id:
                logger.warning("Message missing match_id")
                return None
            
            incoming_message_id = message.get('id')
            
            # Get match details
            match = self.supabase.get_match(match_id)
            if not match:
                logger.warning(f"Match {match_id} not found")
                return None
            
            invitee = self.supabase.get_profile(match.get("invitee_id"))
            initiator = self.supabase.get_profile(match.get("initiator_id"))
            if not invitee or not initiator:
                logger.warning(f"Invitee or initiator not found for match {match_id}")
                return None

            # Get conversation history
            recent_messages = self.supabase.get_recent_messages(match_id, limit=20, exclude_sender_role="Glovy")

            # Analyze tone to detect intervention trigger
            logger.info(f"Analyzing tone for message in match {match_id}")
            trigger = self.tone_analyzer.analyze(
                match=match,
                initiator=initiator,
                invitee=invitee,
                recent_messages=recent_messages,
                new_message=message
            )
            logger.info(f"Detected trigger: {trigger}")
            
            # If trigger is "silent", Glovy should not respond
            if trigger == "silent":
                logger.info(f"Trigger is 'silent', Glovy will not respond: {message.get('body')}")
                return None
            
            # Get channel synchronously (fast, no waiting)
            channel = await self._get_or_create_channel(match_id)

            # Send "typing started" broadcast before generating message
            if channel and match_id:
                should_send_stop_broadcast = True
                await self._send_typing_broadcast(channel, incoming_message_id, user_id=None, is_typing=True)
            
            conversation_history = self.supabase.get_recent_messages(match_id, limit=20)

            # Generate Glovy's response
            logger.info(f"Generating Glovy response for match {match_id}")
            response_text = self.glovy_agent.generate_message(
                match=match,
                initiator=initiator,
                invitee=invitee,
                recent_messages=conversation_history,
                new_message=message,
                trigger=trigger
            )
            
            if should_send_stop_broadcast and match_id and channel:
                should_send_stop_broadcast = False
                await self._send_typing_broadcast(channel, incoming_message_id, user_id=None, is_typing=False)
            
            # Insert Glovy's response into Supabase
            glovy_message = self.supabase.insert_message(
                match_id=match_id,
                body=response_text,
                sender_role="Glovy",
                persona=settings.glovy_persona
            )
            
            if glovy_message:
                elapsed = time.time() - start_time
                logger.info(f"Glovy response inserted for match {match_id} in {elapsed:.2f}s")
                if elapsed > 3.0:
                    logger.warning(f"Total processing time exceeded 3s: {elapsed:.2f}s")
                return glovy_message
            else:
                logger.error(f"Failed to insert Glovy response for match {match_id}")
                # Send "typing stopped" broadcast even if insertion failed
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error processing message in {elapsed:.2f}s: {e}", exc_info=True)
            return None

        finally:    
            # Send "typing stopped" broadcast on error
            if should_send_stop_broadcast and match_id:
                # Get channel if we don't have it yet
                if 'channel' not in locals():
                    channel = await self._get_or_create_channel(match_id)
                if channel:
                    asyncio.create_task(self._send_typing_broadcast(channel, incoming_message_id, user_id=None, is_typing=False))


    async def process_whisper(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an incoming whisper and generate Glovy's response.
        Optimized for 2-3 second response time.
        """
        start_time = time.time()
        match_id = None
        glovy_message = None
        incoming_message_id = None
        should_send_stop_broadcast = False
        
        try:
            
            match_id = message.get("match_id")
            if not match_id:
                logger.warning("Message missing match_id")
                return None
            
            # Get channel synchronously (fast, no waiting)
            channel = await self._get_or_create_channel(match_id)
            
            incoming_message_id = message.get('id')
            
            # Send "typing started" broadcast before generating whisper
            if channel and match_id:
                should_send_stop_broadcast = True
                await self._send_typing_broadcast(channel, incoming_message_id, user_id=message.get("sender_id"), is_typing=True)

            
            # Get match details
            match = self.supabase.get_match(match_id)
            if not match:
                logger.warning(f"Match {match_id} not found")
                return None
            
            invitee = self.supabase.get_profile(match.get("invitee_id"))
            initiator = self.supabase.get_profile(match.get("initiator_id"))
            if not invitee or not initiator:
                logger.warning(f"Invitee or initiator not found for match {match_id}")
                return None

            conversation_history = self.supabase.get_recent_messages(match_id, limit=20)

            # Generate Glovy's response
            logger.info(f"Generating Glovy response for match {match_id}")
            response_text = self.glovy_agent.generate_whisper(
                match=match,
                initiator=initiator,
                invitee=invitee,
                recent_messages=conversation_history,
                new_message=message,
            )
            
            if should_send_stop_broadcast and match_id and channel:
                should_send_stop_broadcast = False
                await self._send_typing_broadcast(channel, incoming_message_id, user_id=message.get("sender_id"),is_typing=False)
            
            # Insert Glovy's response into Supabase
            glovy_message = self.supabase.insert_message(
                match_id=match_id,
                body=response_text,
                sender_role="Glovy",
                persona=settings.glovy_persona,
                recipient_id=message.get("sender_id"),
                is_whisper=True
            )
            
            if glovy_message:
                elapsed = time.time() - start_time
                logger.info(f"Glovy Whisper inserted for match {match_id} in {elapsed:.2f}s")
                if elapsed > 3.0:
                    logger.warning(f"Total processing time exceeded 3s: {elapsed:.2f}s")
                return glovy_message
            else:
                logger.error(f"Failed to insert Glovy Whisper for match {match_id}")
                # Send "typing stopped" broadcast even if insertion failed
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error processing whisper in {elapsed:.2f}s: {e}", exc_info=True)
            return None

        finally:    
            # Send "typing stopped" broadcast on error
            if should_send_stop_broadcast and match_id:
                # Get channel if we don't have it yet
                if 'channel' not in locals():
                    channel = await self._get_or_create_channel(match_id)
                if channel:
                    asyncio.create_task(self._send_typing_broadcast(channel, incoming_message_id, user_id=message.get("sender_id"), is_typing=False))
