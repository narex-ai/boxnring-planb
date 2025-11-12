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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
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
        
        async def on_message_insert(payload: Dict[str, Any]):
            """Callback for new message events."""
            try:
                # Payload structure from Supabase realtime
                event_type = payload.get("eventType") or payload.get("event_type")
                if event_type != "INSERT":
                    return
                
                new_record = payload.get("new") or payload.get("record")
                if not new_record:
                    logger.warning("Received INSERT event without new record")
                    return
                
                logger.info(f"New message received: {new_record.get('id')}")
                
                # Process message asynchronously
                asyncio.create_task(message_processor.process_message(new_record))
                
            except Exception as e:
                logger.error(f"Error in on_message_insert callback: {e}", exc_info=True)
        
        # Set up channel and subscribe to postgres changes
        channel = supabase_async.realtime.channel("glovy-messages")
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
        app.state.supabase_async = supabase_async
        app.state.running = True
        
        logger.info("Glovy backend is running and listening for messages...")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Glovy backend...")
        app.state.running = False
        
        if app.state.subscription:
            try:
                await app.state.subscription.unsubscribe()
                logger.info("Unsubscribed from Supabase real-time")
            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")
        
        # Close async client if it exists
        if hasattr(app.state, 'supabase_async') and app.state.supabase_async:
            try:
                await app.state.supabase_async.close()
                logger.info("Closed async Supabase client")
            except Exception as e:
                logger.error(f"Error closing async client: {e}")


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

