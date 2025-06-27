"""
Main FastAPI application entry point for the multi-agent Slack system.
Handles incoming Slack webhooks and orchestrates agent responses.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
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
        # Debug logging for channel mentions
        event = event_data.event
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        logger.info(f"Processing message: '{text[:100]}...' from user {user_id} in channel {channel_id}")
        
        # Check if this contains a mention
        if f"<@{settings.SLACK_BOT_USER_ID}>" in text:
            logger.info(f"Bot mention detected in channel message: {text[:50]}...")
        else:
            logger.info(f"No bot mention detected. Bot user ID: {settings.SLACK_BOT_USER_ID}")
        
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
    """Admin endpoint to manually trigger data ingestion (bypasses Celery)"""
    try:
        # Direct ingestion without Celery dependency
        from services.slack_connector import SlackConnector
        from services.data_processor import DataProcessor
        from datetime import datetime, timedelta
        
        logger.info("Starting direct Slack data ingestion...")
        
        # Get monitored channels
        channels = settings.get_monitored_channels()
        if not channels:
            return {"status": "skipped", "reason": "no_channels_configured", "channels": []}
        
        logger.info(f"Found {len(channels)} channels to monitor: {channels}")
        
        # Initialize connector
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        
        # First, try to get list of accessible channels (if we have permissions)
        try:
            accessible_response = slack_connector.client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True
            )
            if accessible_response["ok"]:
                accessible_channels = [ch["id"] for ch in accessible_response["channels"] if ch.get("is_member", False)]
                logger.info(f"Found {len(accessible_channels)} accessible channels where bot is member")
                # Filter to only try accessible channels
                channels = [ch for ch in channels if ch in accessible_channels]
                if not channels:
                    return {
                        "status": "no_accessible_channels",
                        "message": "Bot is not a member of any configured channels. Add bot to channels first.",
                        "accessible_channels": accessible_channels
                    }
        except Exception as list_error:
            logger.warning(f"Could not list channels (missing permissions): {list_error}")
            # Continue with original channels list
        
        # Set time range for ingestion (last 7 days for initial population)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        results = {
            "status": "success",
            "channels_processed": [],
            "total_messages": 0,
            "errors": []
        }
        
        for channel in channels:
            try:
                logger.info(f"Processing channel: {channel}")
                
                # Extract messages from channel
                messages = await slack_connector.extract_channel_messages(
                    channel_id=channel,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if messages:
                    # Process and clean messages
                    processed_messages = await data_processor.process_messages(messages)
                    
                    channel_result = {
                        "channel": channel,
                        "raw_messages": len(messages),
                        "processed_messages": len(processed_messages),
                        "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}"
                    }
                    
                    results["channels_processed"].append(channel_result)
                    results["total_messages"] += len(processed_messages)
                    
                    logger.info(f"Channel {channel}: {len(messages)} raw messages, {len(processed_messages)} processed")
                else:
                    results["channels_processed"].append({
                        "channel": channel,
                        "raw_messages": 0,
                        "processed_messages": 0,
                        "note": "No messages found in time range"
                    })
                    
            except Exception as e:
                error_msg = f"Error processing channel {channel}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        logger.info(f"Ingestion completed: {results['total_messages']} total messages processed")
        return results
        
    except Exception as e:
        logger.error(f"Failed to trigger ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger ingestion: {str(e)}")

@app.get("/admin/bot-config")
async def bot_config():
    """Admin endpoint to check bot configuration"""
    return {
        "bot_token_configured": bool(settings.SLACK_BOT_TOKEN),
        "bot_token_length": len(settings.SLACK_BOT_TOKEN) if settings.SLACK_BOT_TOKEN else 0,
        "bot_user_id": settings.SLACK_BOT_USER_ID,
        "signing_secret_configured": bool(settings.SLACK_SIGNING_SECRET),
        "channels_to_monitor": settings.get_monitored_channels()
    }

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

@app.get("/admin/short-term-memory-test")
async def test_short_term_memory():
    """Admin endpoint to test 10-message short-term memory system"""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    test_results = {}
    
    try:
        # Test conversation key format
        channel_id = "C1234567890"
        thread_ts = "1640995200.001500"
        conversation_key = f"conv:{channel_id}:{thread_ts}"
        test_results["conversation_key"] = conversation_key
        
        # Test storing multiple raw messages (simulate conversation)
        messages = [
            {"text": "Hi, I need help with Autopilot", "user_name": "john", "message_ts": "1640995200.001500"},
            {"text": "What specific aspect of Autopilot are you working on?", "user_name": "bot", "message_ts": "1640995205.001501"},
            {"text": "I'm trying to set up triggers for our process", "user_name": "john", "message_ts": "1640995210.001502"},
            {"text": "Triggers are powerful! What kind of process are you automating?", "user_name": "bot", "message_ts": "1640995215.001503"},
            {"text": "We want to automate our approval workflow", "user_name": "john", "message_ts": "1640995220.001504"},
            {"text": "Great! Approval workflows are perfect for Autopilot. Do you have the process mapped out?", "user_name": "bot", "message_ts": "1640995225.001505"},
            {"text": "Yes, we have 3 approval steps", "user_name": "john", "message_ts": "1640995230.001506"},
            {"text": "Perfect! For 3-step approvals, you'll want to use conditional logic...", "user_name": "bot", "message_ts": "1640995235.001507"},
            {"text": "That sounds complex. Can you walk me through it?", "user_name": "john", "message_ts": "1640995240.001508"},
            {"text": "Of course! Let me break it down step by step...", "user_name": "bot", "message_ts": "1640995245.001509"},
            {"text": "Ok, tell me about the unified trigger in the web platform", "user_name": "john", "message_ts": "1640995250.001510"},
        ]
        
        # Store all messages
        for i, msg_data in enumerate(messages):
            success = await memory_service.store_raw_message(conversation_key, msg_data, max_messages=10)
            test_results[f"store_message_{i+1}"] = success
        
        # Retrieve recent messages
        recent_messages = await memory_service.get_recent_messages(conversation_key, limit=10)
        test_results["retrieved_message_count"] = len(recent_messages)
        test_results["messages_in_correct_order"] = recent_messages[0]["text"] == messages[-1]["text"] if recent_messages else False
        test_results["oldest_message_preserved"] = len(recent_messages) == 10 and recent_messages[-1]["text"] == messages[1]["text"]
        
        # Test that only 10 messages are kept (sliding window)
        test_results["sliding_window_working"] = len(recent_messages) <= 10
        
        # Test conversation context flow
        last_3_messages = recent_messages[:3] if len(recent_messages) >= 3 else recent_messages
        conversation_flow = " | ".join([msg["text"][:30] + "..." for msg in reversed(last_3_messages)])
        test_results["conversation_flow_sample"] = conversation_flow
        
        overall_success = all([
            test_results["retrieved_message_count"] > 0,
            test_results["messages_in_correct_order"],
            test_results["sliding_window_working"]
        ])
        
        return {
            "status": "success" if overall_success else "partial_failure",
            "short_term_memory_working": overall_success,
            "test_results": test_results,
            "summary": {
                "backend": "redis" if memory_service.redis_available else "in_memory",
                "messages_stored": test_results["retrieved_message_count"],
                "conversation_context_preserved": overall_success
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing short-term memory: {e}")
        return {
            "status": "error",
            "error": str(e),
            "test_results": test_results
        }

@app.get("/admin/conversation-memory-test")
async def test_conversation_memory():
    """Admin endpoint to test conversation memory similar to real Slack usage"""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    test_results = {}
    
    try:
        # Simulate a Slack conversation like the orchestrator does
        channel_id = "C1234567890"
        thread_ts = "1640995200.001500"
        message_ts = "1640995200.001500"
        
        # Test conversation key format (same as orchestrator uses)
        conversation_key = f"conv:{channel_id}:{thread_ts or message_ts}"
        test_results["conversation_key"] = conversation_key
        
        # Simulate message data structure
        message_data = {
            "channel_id": channel_id,
            "user_id": "U987654321",
            "text": "What's the latest update on Project Alpha?",
            "message_ts": message_ts,
            "thread_ts": thread_ts,
            "user_name": "john.doe",
            "channel_name": "general"
        }
        
        # Store conversation context (same way orchestrator does)
        store_success = await memory_service.store_conversation_context(
            conversation_key, 
            message_data, 
            ttl=86400  # 24 hours - same as orchestrator
        )
        test_results["store_conversation"] = store_success
        
        # Retrieve conversation context
        retrieved_context = await memory_service.get_conversation_context(conversation_key)
        test_results["retrieve_conversation"] = retrieved_context is not None
        test_results["data_matches"] = retrieved_context == message_data if retrieved_context else False
        
        # Test multiple conversations in same channel
        conversation_key_2 = f"conv:{channel_id}:{message_ts}_followup"
        followup_data = {
            "channel_id": channel_id,
            "user_id": "U555666777", 
            "text": "Thanks for the update! When is the next milestone?",
            "message_ts": "1640995260.001600",
            "thread_ts": thread_ts,
            "user_name": "jane.smith",
            "channel_name": "general"
        }
        
        await memory_service.store_conversation_context(conversation_key_2, followup_data, ttl=86400)
        retrieved_followup = await memory_service.get_conversation_context(conversation_key_2)
        test_results["multi_conversation_support"] = retrieved_followup is not None
        
        # Test memory backend info
        test_results["backend_type"] = "redis" if memory_service.redis_available else "in_memory"
        test_results["health_check"] = await memory_service.health_check()
        
        # Cache status (if in-memory)
        if not memory_service.redis_available:
            test_results["total_cached_conversations"] = len(memory_service._memory_cache)
            conversation_keys = [k for k in memory_service._memory_cache.keys() if k.startswith("conv:")]
            test_results["conversation_keys_count"] = len(conversation_keys)
        
        overall_success = all([
            test_results.get("store_conversation", False),
            test_results.get("retrieve_conversation", False),
            test_results.get("data_matches", False),
            test_results.get("multi_conversation_support", False)
        ])
        
        return {
            "status": "success" if overall_success else "partial_failure",
            "conversation_memory_working": overall_success,
            "test_results": test_results,
            "summary": {
                "backend": test_results.get("backend_type", "unknown"),
                "conversations_stored": test_results.get("conversation_keys_count", 0) if not memory_service.redis_available else "redis_backend",
                "all_tests_passed": overall_success
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing conversation memory: {e}")
        return {
            "status": "error",
            "error": str(e),
            "test_results": test_results
        }

@app.get("/admin/channel-diagnostic")
async def channel_diagnostic():
    """Admin endpoint to diagnose channel access and permissions"""
    try:
        from services.slack_connector import SlackConnector
        
        slack_connector = SlackConnector()
        channels = settings.get_monitored_channels()
        
        if not channels:
            return {"status": "no_channels_configured", "channels": []}
        
        results = {
            "configured_channels": channels,
            "channel_details": [],
            "bot_permissions": {},
            "recommendations": []
        }
        
        # Test each channel
        for channel in channels:
            channel_info = {
                "channel_id": channel,
                "accessible": False,
                "error": None,
                "member_count": None,
                "channel_name": None
            }
            
            try:
                # Try to get channel info
                response = slack_connector.client.conversations_info(channel=channel)
                if response["ok"]:
                    channel_data = response["channel"]
                    channel_info.update({
                        "accessible": True,
                        "channel_name": channel_data.get("name", "unknown"),
                        "is_private": channel_data.get("is_private", False),
                        "is_member": channel_data.get("is_member", False),
                        "member_count": channel_data.get("num_members", 0)
                    })
                else:
                    channel_info["error"] = response.get("error", "unknown_error")
                    
            except Exception as e:
                channel_info["error"] = str(e)
            
            results["channel_details"].append(channel_info)
        
        # Add recommendations
        for channel_detail in results["channel_details"]:
            if not channel_detail["accessible"]:
                if "not_in_channel" in str(channel_detail.get("error", "")):
                    results["recommendations"].append(f"Add bot to channel {channel_detail['channel_id']} (/invite @your-bot-name)")
                elif "channel_not_found" in str(channel_detail.get("error", "")):
                    results["recommendations"].append(f"Channel {channel_detail['channel_id']} may not exist or bot lacks permissions")
            elif not channel_detail.get("is_member", False):
                results["recommendations"].append(f"Bot needs to be added as member to {channel_detail.get('channel_name', channel_detail['channel_id'])}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in channel diagnostic: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/admin/workspace-channels")
async def list_workspace_channels():
    """Admin endpoint to list all accessible channels in the workspace"""
    try:
        from services.slack_connector import SlackConnector
        
        slack_connector = SlackConnector()
        
        # Get all conversations the bot can see
        all_channels = []
        cursor = None
        
        while True:
            try:
                response = slack_connector.client.conversations_list(
                    exclude_archived=True,
                    types="public_channel,private_channel",
                    limit=100,
                    cursor=cursor
                )
                
                if not response["ok"]:
                    return {"error": f"API error: {response.get('error')}", "channels": []}
                
                channels = response.get("channels", [])
                for channel in channels:
                    channel_info = {
                        "id": channel.get("id"),
                        "name": channel.get("name"),
                        "is_private": channel.get("is_private", False),
                        "is_member": channel.get("is_member", False),
                        "num_members": channel.get("num_members", 0),
                        "created": channel.get("created", 0),
                        "purpose": channel.get("purpose", {}).get("value", ""),
                        "topic": channel.get("topic", {}).get("value", "")
                    }
                    all_channels.append(channel_info)
                
                # Check for more channels
                if not response.get("response_metadata", {}).get("next_cursor"):
                    break
                cursor = response["response_metadata"]["next_cursor"]
                
            except Exception as e:
                return {"error": str(e), "channels": all_channels}
        
        # Separate channels by accessibility
        accessible_channels = [ch for ch in all_channels if ch["is_member"]]
        public_channels = [ch for ch in all_channels if not ch["is_private"] and not ch["is_member"]]
        private_channels = [ch for ch in all_channels if ch["is_private"]]
        
        # Check if our target channel is in the list
        target_channel = "C087QKECFKQ"
        target_found = None
        for ch in all_channels:
            if ch["id"] == target_channel:
                target_found = ch
                break
        
        return {
            "total_channels": len(all_channels),
            "accessible_channels": accessible_channels,
            "public_channels_not_member": public_channels,
            "private_channels": private_channels,
            "target_channel_info": target_found,
            "can_ingest_from": [ch["id"] for ch in accessible_channels]
        }
        
    except Exception as e:
        logger.error(f"Error listing workspace channels: {e}")
        return {"status": "error", "error": str(e)}

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
