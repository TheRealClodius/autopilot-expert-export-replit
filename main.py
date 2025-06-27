"""
Main FastAPI application entry point for the multi-agent Slack system.
Handles incoming Slack webhooks and orchestrates agent responses.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import os

from agents.slack_gateway import SlackGateway
from agents.orchestrator_agent import OrchestratorAgent
from config import settings
from models.schemas import SlackEvent, SlackChallenge
from services.memory_service import MemoryService
from celery_app import celery_app

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global slack_gateway, orchestrator_agent, memory_service
    
    logger.info("Initializing multi-agent system...")
    
    # Initialize services
    memory_service = MemoryService()
    slack_gateway = SlackGateway()
    orchestrator_agent = OrchestratorAgent(memory_service)
    
    # Start background tasks
    logger.info("Starting daily knowledge update task...")
    celery_app.send_task('workers.knowledge_update_worker.daily_ingestion')
    
    logger.info("Multi-agent system initialized successfully")
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down multi-agent system...")
    if memory_service:
        await memory_service.close()

app = FastAPI(
    title="Autopilot Expert Multi-Agent System",
    description="Backend system for AI-powered Slack responses with multi-agent architecture",
    version="1.0.0",
    lifespan=lifespan
)

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
            challenge = SlackChallenge(**body)
            return {"challenge": challenge.challenge}
        
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
        
        # Pass to Slack Gateway for initial processing
        processed_message = await slack_gateway.process_message(event_data)
        
        if processed_message:
            # Forward to Orchestrator Agent
            response = await orchestrator_agent.process_query(processed_message)
            
            # Send response back to Slack
            if response:
                await slack_gateway.send_response(response)
                logger.info("Successfully processed and responded to Slack message")
            else:
                logger.warning("No response generated for Slack message")
        else:
            logger.info("Message filtered out by Slack Gateway")
            
    except Exception as e:
        logger.error(f"Error in message processing pipeline: {e}")
        # Send error message to Slack
        try:
            await slack_gateway.send_error_response(
                event_data.event.get('channel'),
                "I'm experiencing technical difficulties. Please try again later."
            )
        except Exception as send_err:
            logger.error(f"Failed to send error response: {send_err}")

@app.post("/admin/trigger-ingestion")
async def trigger_manual_ingestion():
    """Admin endpoint to manually trigger data ingestion"""
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
        redis_status = await memory_service.health_check() if memory_service else False
        
        # Check Celery workers
        celery_status = celery_app.control.inspect().active() is not None
        
        return {
            "redis": "healthy" if redis_status else "unhealthy",
            "celery": "healthy" if celery_status else "unhealthy",
            "agents": "healthy" if slack_gateway and orchestrator_agent else "unhealthy"
        }
    except Exception as e:
        logger.error(f"Error checking system status: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info"
    )
