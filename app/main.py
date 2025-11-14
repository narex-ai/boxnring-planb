"""
FastAPI application for Glovy AI Agent backend.
"""
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
                
                logger.info(f"New message received: {new_record.get('id')}")
                asyncio.create_task(message_processor.process_message(new_record))
                
            except Exception as e:
                logger.error(f"Error in on_message_insert callback: {e}", exc_info=True)
        
        # Set up channel and subscribe to postgres changes
        channel = supabase_async.realtime.channel("messages-realtime")
        
        # Add error handler for connection issues
        def on_error(payload: Dict[str, Any]):
            logger.error(f"Realtime error: {payload}")
            app.state.running = False
        
        def on_close(payload: Dict[str, Any]):
            logger.warning(f"Realtime connection closed: {payload}")
            app.state.running = False
        
        channel.on_error(on_error)
        channel.on_close(on_close)
        
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
        raise


async def monitor_and_reconnect(app: FastAPI, message_processor: MessageProcessor):
    """Background task to monitor connection and reconnect if needed."""
    global reconnect_delay
    
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            # Check if connection is still alive
            if not app.state.running or not app.state.subscription:
                logger.warning("Realtime connection lost, attempting to reconnect...")
                
                try:
                    # Unsubscribe from old channel if it exists
                    if app.state.subscription:
                        try:
                            await app.state.subscription.unsubscribe()
                        except:
                            pass
                    
                    # Recreate async client
                    supabase_async: AsyncClient = await acreate_client(
                        settings.supabase_url,
                        settings.supabase_key
                    )
                    
                    # Reconnect
                    await setup_realtime_subscription(
                        supabase_async,
                        message_processor,
                        app
                    )
                    
                    app.state.supabase_async = supabase_async
                    reconnect_delay = 5  # Reset delay on successful reconnect
                    logger.info("Successfully reconnected to Supabase realtime")
                    
                except Exception as e:
                    logger.error(f"Reconnection attempt failed: {e}")
                    # Exponential backoff
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    logger.info(f"Will retry reconnection in {reconnect_delay} seconds")
                    await asyncio.sleep(reconnect_delay)
            
            # Check connection state
            elif hasattr(app.state.subscription, 'socket') and app.state.subscription.socket:
                # Check if socket is closed
                if app.state.subscription.socket.closed:
                    logger.warning("WebSocket socket is closed, marking for reconnection")
                    app.state.running = False
                    
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
        message_processor = MessageProcessor(supabase_client)
        
        # Store in app.state for dependency injection
        app.state.supabase_client = supabase_client
        app.state.message_processor = message_processor
        app.state.subscription = None
        app.state.running = False
        
        # Set up Supabase real-time subscription using async client
        logger.info("Subscribing to Supabase real-time messages...")
        
        # Create async Supabase client for realtime operations
        supabase_async: AsyncClient = await acreate_client(
            settings.supabase_url,
            settings.supabase_key
        )
        
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

