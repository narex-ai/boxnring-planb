"""
FastAPI application for Glovy AI Agent backend.
"""
import warnings
# Suppress websockets deprecation warnings from Supabase realtime library
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from typing import Dict, Any
from app.db.supabase import SupabaseClient
from app.services.message_processor import MessageProcessor
from app.core.config import settings
from app.api.v1.api import api_router
from supabase import acreate_client, AsyncClient

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.environment == "development" else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state for reconnection
reconnect_task = None
reconnect_delay = 5  # Start with 5 seconds
max_reconnect_delay = 300  # Max 5 minutes
reconnect_lock = asyncio.Lock()  # Prevent concurrent reconnection attempts


async def reconnect_realtime(
    app: FastAPI,
    message_processor: MessageProcessor,
    reason: str = "connection lost"
):
    """Reconnect to Supabase realtime with proper error handling."""
    global reconnect_delay
    
    # Prevent concurrent reconnection attempts
    if reconnect_lock.locked():
        logger.debug("Reconnection already in progress, skipping...")
        return
    
    async with reconnect_lock:
        logger.warning(f"Realtime connection lost ({reason}), attempting to reconnect...")
        app.state.running = False
        
        try:
            # Unsubscribe from old channel if it exists
            if app.state.subscription:
                try:
                    await app.state.subscription.unsubscribe()
                    logger.debug("Unsubscribed from old channel")
                except Exception as unsub_error:
                    logger.debug(f"Error unsubscribing old channel: {unsub_error}")
            
            # Recreate async client
            supabase_async: AsyncClient = await acreate_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            # Reconnect
            channel = await setup_realtime_subscription(
                supabase_async,
                message_processor,
                app
            )
            
            if channel:
                app.state.supabase_async = supabase_async
                reconnect_delay = 5  # Reset delay on successful reconnect
                logger.info("Successfully reconnected to Supabase realtime")
            else:
                raise Exception("Failed to establish subscription")
                
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {e}")
            # Exponential backoff
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
            logger.info(f"Will retry reconnection in {reconnect_delay} seconds")
            app.state.running = False
            # Schedule retry
            asyncio.create_task(
                asyncio.sleep(reconnect_delay)
            ).add_done_callback(
                lambda _: asyncio.create_task(
                    reconnect_realtime(app, message_processor, "retry after backoff")
                )
            )


async def setup_realtime_subscription(
    supabase_async: AsyncClient,
    message_processor: MessageProcessor,
    app: FastAPI
):
    """Set up Supabase realtime subscription with error handling."""
    try:
        def on_message_insert(payload: Dict[str, Any]):
            """Callback for new message events (async)."""
            try:
                logger.info(f"on_message_insert called with payload keys: {list(payload.keys())}")
                
                data = payload.get("data", {})
                if not data:
                    logger.warning("Received payload without 'data' field")
                    return
                
                event_type = data.get("type")
                if event_type is None:
                    logger.warning("No event type found in payload data")
                    return
                
                event_type_value = None
                if hasattr(event_type, 'value'):
                    event_type_value = event_type.value
                else:
                    event_type_value = str(event_type)
                
                if event_type_value != "INSERT":
                    logger.info(f"Event type is not INSERT: {event_type_value}")
                    return
                
                new_record = data.get("record")
                if not new_record:
                    logger.warning("Received INSERT event without record in data")
                    return

                if new_record.get("sender_role") == "Glovy":
                    logger.debug("Skipping Glovy's own message")
                    return

                if new_record.get("sender_role") == "SYSTEM" and new_record.get("message_type") == "notification":
                    logger.debug("Skipping system notification message")
                    return
                
                logger.info(f"New message received: {new_record.get('id')}")
                if new_record.get("is_whisper") == True:
                    asyncio.create_task(message_processor.process_whisper(new_record))
                else:
                    asyncio.create_task(message_processor.process_message(new_record))
                
                
            except Exception as e:
                logger.error(f"Error in on_message_insert callback: {e}", exc_info=True)
        
        def on_error(payload: Dict[str, Any]):
            """Callback for channel errors."""
            logger.error(f"Realtime channel error: {payload}")
            # Trigger reconnection on error
            asyncio.create_task(
                reconnect_realtime(app, message_processor, f"channel error: {payload}")
            )
        
        def on_close(payload: Dict[str, Any]):
            """Callback for channel close events."""
            logger.warning(f"Realtime channel closed: {payload}")
            # Trigger reconnection on close
            asyncio.create_task(
                reconnect_realtime(app, message_processor, f"channel closed: {payload}")
            )
        
        # Set up channel and subscribe to postgres changes
        channel = supabase_async.realtime.channel("messages-realtime")
        
        # Add error and close handlers if available
        try:
            # Try to add error handler (method may vary by library version)
            if hasattr(channel, 'on'):
                channel.on("error", on_error)
                channel.on("close", on_close)
            elif hasattr(channel, 'on_error'):
                channel.on_error(on_error)
            elif hasattr(channel, 'on_close'):
                channel.on_close(on_close)
        except (AttributeError, TypeError) as e:
            logger.debug(f"Could not add error/close handlers (may not be supported): {e}")
        
        # Subscribe to postgres changes
        await (
            channel
            .on_postgres_changes(
                event="INSERT",
                schema="public",
                table="messages",
                callback=on_message_insert
            )
            .subscribe()
        )
        
        app.state.subscription = channel
        app.state.running = True
        logger.info("Glovy backend is running and listening for messages...")
        return channel
        
    except Exception as e:
        logger.error(f"Error setting up realtime subscription: {e}", exc_info=True)
        app.state.running = False
        # Don't raise - let the monitor handle reconnection
        return None


async def monitor_and_reconnect(app: FastAPI, message_processor: MessageProcessor):
    """Background task to monitor connection and reconnect if needed."""
    global reconnect_delay
    
    while True:
        try:
            await asyncio.sleep(30)  # Check every 10 seconds (more frequent)
            
            # Check if connection is still alive
            if not app.state.running or not app.state.subscription:
                # Trigger reconnection
                await reconnect_realtime(app, message_processor, "monitor detected disconnect")
                continue
            
            # Check connection state - try to verify channel is still active
            if app.state.subscription:
                try:
                    # Check channel state
                    channel_state = None
                    if hasattr(app.state.subscription, 'state'):
                        channel_state = app.state.subscription.state
                    elif hasattr(app.state.subscription, 'channel_state'):
                        channel_state = app.state.subscription.channel_state
                    
                    # If channel is not joined/subscribed, mark for reconnection
                    if channel_state and channel_state not in ['joined', 'subscribed', 'attached']:
                        logger.warning(f"Channel state is {channel_state}, marking for reconnection")
                        await reconnect_realtime(app, message_processor, f"channel state: {channel_state}")
                        continue
                    
                    # Check if we can access the socket state
                    if hasattr(app.state.subscription, 'socket'):
                        socket = app.state.subscription.socket
                        if socket:
                            # Check if socket is closed
                            if hasattr(socket, 'closed') and socket.closed:
                                logger.warning("WebSocket socket is closed, reconnecting...")
                                await reconnect_realtime(app, message_processor, "socket closed")
                                continue
                            
                            # Check if socket has a connection state
                            if hasattr(socket, 'state'):
                                socket_state = socket.state
                                if socket_state not in ['open', 'OPEN']:
                                    logger.warning(f"WebSocket state is {socket_state}, reconnecting...")
                                    await reconnect_realtime(app, message_processor, f"socket state: {socket_state}")
                                    continue
                    
                    # Try to verify connection by checking if realtime client is connected
                    if hasattr(app.state, 'supabase_async') and app.state.supabase_async:
                        if hasattr(app.state.supabase_async, 'realtime'):
                            realtime = app.state.supabase_async.realtime
                            if hasattr(realtime, 'is_connected'):
                                if not realtime.is_connected:
                                    logger.warning("Realtime client reports disconnected, reconnecting...")
                                    await reconnect_realtime(app, message_processor, "realtime client disconnected")
                                    continue
                
                except AttributeError:
                    # Channel might not have expected attributes, that's okay
                    pass
                except Exception as e:
                    logger.warning(f"Error checking connection state: {e}")
                    # Mark for reconnection on any error checking state
                    await reconnect_realtime(app, message_processor, f"state check error: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Reconnection monitor task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in reconnection monitor: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait longer on unexpected errors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global reconnect_task
    
    # Startup
    logger.info("Starting Glovy AI Agent backend...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    
    try:
        # Initialize clients
        supabase_client = SupabaseClient()
        
        # Create async Supabase client for realtime operations
        supabase_async: AsyncClient = await acreate_client(
            settings.supabase_url,
            settings.supabase_key
        )
        
        # Initialize message processor with both clients
        message_processor = MessageProcessor(supabase_client, supabase_async)
        
        # Store in app.state for dependency injection
        app.state.supabase_client = supabase_client
        app.state.message_processor = message_processor
        app.state.subscription = None
        app.state.running = False
        
        # Set up Supabase real-time subscription using async client
        logger.info("Subscribing to Supabase real-time messages...")
        
        # Set up initial subscription
        await setup_realtime_subscription(
            supabase_async,
            message_processor,
            app
        )
        
        app.state.supabase_async = supabase_async
        
        # Start reconnection monitor task
        reconnect_task = asyncio.create_task(
            monitor_and_reconnect(app, message_processor)
        )
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Glovy backend...")
        app.state.running = False
        
        # Cancel reconnection task
        if reconnect_task:
            reconnect_task.cancel()
            try:
                await reconnect_task
            except asyncio.CancelledError:
                pass
        
        if app.state.subscription:
            try:
                await app.state.subscription.unsubscribe()
                logger.info("Unsubscribed from Supabase real-time")
            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")
        
        # Note: Supabase AsyncClient doesn't require explicit closing
        # The client will be cleaned up automatically when the app shuts down


# Create FastAPI app
app = FastAPI(
    title="Glovy AI Agent API",
    description="Witty and smart AI relationship coach for facilitating conversations",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info" if settings.environment == "development" else "warning"
    )

