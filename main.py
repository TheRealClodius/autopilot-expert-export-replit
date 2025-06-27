"""
Main FastAPI application entry point for the multi-agent Slack system.
Handles incoming Slack webhooks and orchestrates agent responses.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
import os

from agents.slack_gateway import SlackGateway
from agents.orchestrator_agent import OrchestratorAgent
from config import settings
from models.schemas import SlackEvent, SlackChallenge
from services.memory_service import MemoryService

# Import Celery only if configured
try:
    from celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
slack_gateway = None
orchestrator_agent = None
memory_service = None

# Initialize FastAPI without complex lifespan manager
app = FastAPI(
    title="Autopilot Expert Multi-Agent System",
    description="Backend system for AI-powered Slack responses with multi-agent architecture",
    version="1.0.0"
)

# Initialize services immediately for faster startup
def initialize_services():
    """Initialize services synchronously"""
    global slack_gateway, orchestrator_agent, memory_service
    
    logger.info("Initializing multi-agent system...")
    
    try:
        # Initialize services
        memory_service = MemoryService()
        slack_gateway = SlackGateway()
        orchestrator_agent = OrchestratorAgent(memory_service)
        
        logger.info("Multi-agent system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

# Initialize on startup
services_initialized = initialize_services()

@app.get("/")
def root():
    """Root endpoint - responds immediately for health checks"""
    return {"service": "autopilot-expert", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "autopilot-expert"}

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming Slack events including messages from channels, threads, and DMs.
    This is the main entry point for Slack interactions.
    """
    try:
        body = await request.json()
        
        # Handle Slack URL verification challenge
        if body.get("type") == "url_verification":
            # Return challenge as plain text according to Slack documentation
            challenge_value = body.get("challenge")
            if challenge_value:
                return PlainTextResponse(challenge_value)
            else:
                raise HTTPException(status_code=400, detail="Missing challenge parameter")
        
        # Handle Slack events
        if body.get("type") == "event_callback":
            event_data = SlackEvent(**body)
            
            # Filter out bot messages and messages from the autopilot bot itself
            if (event_data.event.get("bot_id") or 
                event_data.event.get("user") == settings.SLACK_BOT_USER_ID):
                return {"status": "ignored"}
            
            # Process the message in background
            background_tasks.add_task(process_slack_message, event_data)
            
            return {"status": "accepted"}
        
        return {"status": "ignored"}
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_slack_message(event_data: SlackEvent):
    """Process incoming Slack message through the agent pipeline"""
    try:
        logger.info(f"Processing message from user {event_data.event.get('user')} in channel {event_data.event.get('channel')}")
        
        # Check if services are initialized
        if not slack_gateway or not orchestrator_agent:
            logger.error("Services not properly initialized")
            return
        
        # Pass to Slack Gateway for initial processing
        processed_message = await slack_gateway.process_message(event_data)
        
        if processed_message:
            # Send immediate thinking indicator
            thinking_message_ts = await slack_gateway.send_thinking_indicator(
                processed_message.channel_id,
                processed_message.thread_ts
            )
            
            # Forward to Orchestrator Agent for processing
            response = await orchestrator_agent.process_query(processed_message)
            
            # Update the thinking message with final response
            if response and thinking_message_ts:
                await slack_gateway.update_message(
                    processed_message.channel_id,
                    thinking_message_ts,
                    response.get("text", "Sorry, I couldn't generate a response.")
                )
                logger.info("Successfully processed and updated Slack message")
            elif response:
                # Fallback: send new message if update failed
                await slack_gateway.send_response(response)
                logger.info("Successfully processed and responded to Slack message")
            else:
                # Update thinking indicator with error message
                if thinking_message_ts:
                    await slack_gateway.update_message(
                        processed_message.channel_id,
                        thinking_message_ts,
                        "Sorry, I couldn't process your request at the moment."
                    )
                logger.warning("No response generated for Slack message")
        else:
            logger.info("Message filtered out by Slack Gateway")
            
    except Exception as e:
        logger.error(f"Error in message processing pipeline: {e}")
        # Send error message to Slack
        try:
            channel_id = event_data.event.get('channel')
            thread_ts = event_data.event.get('thread_ts')
            
            if slack_gateway and channel_id:
                # Try to update thinking message if it exists, otherwise send new error
                await slack_gateway.send_error_response(
                    channel_id,
                    "I'm experiencing technical difficulties. Please try again later.",
                    thread_ts
                )
        except Exception as send_err:
            logger.error(f"Failed to send error response: {send_err}")

@app.post("/admin/trigger-ingestion")
async def trigger_manual_ingestion():
    """Admin endpoint to manually trigger data ingestion"""
    if not CELERY_AVAILABLE or not celery_app:
        raise HTTPException(status_code=503, detail="Background task processing is not available in this deployment")
    
    try:
        task = celery_app.send_task('workers.knowledge_update_worker.manual_ingestion')
        return {"status": "triggered", "task_id": task.id}
    except Exception as e:
        logger.error(f"Failed to trigger ingestion: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger ingestion")

@app.get("/admin/system-status")
async def system_status():
    """Admin endpoint to check system status"""
    try:
        # Check Redis connection
        redis_status = False
        if memory_service:
            redis_status = await memory_service.health_check()
        
        # Check Celery workers (disabled for Cloud Run deployment)
        if CELERY_AVAILABLE and celery_app and settings.CELERY_BROKER_URL and settings.CELERY_BROKER_URL.strip():
            try:
                celery_status = celery_app.control.inspect().active() is not None
            except Exception:
                celery_status = False
        else:
            # Celery not configured or not available
            celery_status = "disabled"
        
        return {
            "redis": "healthy" if redis_status else "unhealthy",
            "celery": "healthy" if celery_status else "unhealthy",
            "agents": "healthy" if slack_gateway and orchestrator_agent else "unhealthy",
            "services_initialized": services_initialized
        }
    except Exception as e:
        logger.error(f"Error checking system status: {e}")
        return {"error": str(e)}

@app.get("/admin/prompts")
async def get_prompt_info():
    """Admin endpoint to get prompt information"""
    from utils.prompt_loader import prompt_loader
    return {
        "prompt_info": prompt_loader.get_prompt_info(),
        "prompts_loaded": len(prompt_loader.get_all_prompts()),
        "yaml_available": hasattr(prompt_loader, '_prompts') and 'version' in prompt_loader._prompts
    }

@app.post("/admin/prompts/reload")
async def reload_prompts():
    """Admin endpoint to reload prompts from file"""
    from utils.prompt_loader import reload_all_prompts
    try:
        reload_all_prompts()
        return {"status": "success", "message": "Prompts reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload prompts: {e}")

if __name__ == "__main__":
    # Get port from environment for Cloud Run deployment
    port = int(os.environ.get("PORT", 5000))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )
