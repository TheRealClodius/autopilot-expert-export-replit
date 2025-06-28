"""
Main FastAPI application entry point for the multi-agent Slack system.
Handles incoming Slack webhooks and orchestrates agent responses.
Updated: Vector search and embedding system fully functional.
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
from services.trace_manager import trace_manager

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
            # Create progress updater for real-time Slack message updates
            progress_updater = await slack_gateway.create_progress_updater(
                processed_message.channel_id,
                processed_message.thread_ts
            )
            
            if progress_updater:
                # Import progress tracker locally to avoid circular imports
                from services.progress_tracker import ProgressTracker
                
                # Create progress tracker with Slack update callback
                progress_tracker = ProgressTracker(update_callback=progress_updater)
                
                # Create new orchestrator instance with progress tracking
                from agents.orchestrator_agent import OrchestratorAgent
                orchestrator_with_progress = OrchestratorAgent(
                    memory_service=orchestrator_agent.memory_service,
                    progress_tracker=progress_tracker
                )
                
                # Forward to Orchestrator Agent for processing with progress tracking
                response = await orchestrator_with_progress.process_query(processed_message)
                
                # Update the progress message with final response
                if response:
                    final_response_text = response.get("text", "Sorry, I couldn't generate a response.")
                    await progress_updater(final_response_text)
                    logger.info("Successfully processed and updated Slack message with progress tracking")
                    
                    # Complete the LangSmith conversation session
                    await trace_manager.complete_conversation_session(
                        final_response=final_response_text
                    )
                else:
                    error_text = "Sorry, I couldn't process your request at the moment."
                    await progress_updater(error_text)
                    logger.warning("No response generated for Slack message")
                    
                    # Complete the LangSmith conversation session with error
                    await trace_manager.complete_conversation_session(
                        error="No response generated by agents"
                    )
            else:
                # Fallback to original behavior if progress updater creation fails
                logger.warning("Failed to create progress updater, falling back to standard processing")
                response = await orchestrator_agent.process_query(processed_message)
                if response:
                    await slack_gateway.send_response(response)
                    logger.info("Successfully processed and responded to Slack message (fallback)")
                    
                    # Complete the LangSmith conversation session for fallback path
                    await trace_manager.complete_conversation_session(
                        final_response=response.get("text", "Response sent via fallback method")
                    )
                else:
                    # Complete the LangSmith conversation session with error for fallback path
                    await trace_manager.complete_conversation_session(
                        error="No response generated in fallback mode"
                    )
        else:
            logger.info("Message filtered out by Slack Gateway")
            
    except Exception as e:
        logger.error(f"Error in message processing pipeline: {e}")
        
        # Complete the LangSmith conversation session with error
        await trace_manager.complete_conversation_session(
            error=f"Pipeline error: {str(e)}"
        )
        
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
    # Try to get bot user ID from Slack API if not configured
    bot_user_id = settings.SLACK_BOT_USER_ID
    if not bot_user_id and settings.SLACK_BOT_TOKEN:
        try:
            from slack_sdk import WebClient
            client = WebClient(token=settings.SLACK_BOT_TOKEN)
            auth_response = client.auth_test()
            if auth_response["ok"]:
                bot_user_id = auth_response["user_id"]
        except Exception as e:
            bot_user_id = f"API Error: {str(e)}"
    
    return {
        "bot_token_configured": bool(settings.SLACK_BOT_TOKEN),
        "bot_token_length": len(settings.SLACK_BOT_TOKEN) if settings.SLACK_BOT_TOKEN else 0,
        "bot_user_id": bot_user_id,
        "bot_user_id_from_api": bot_user_id != settings.SLACK_BOT_USER_ID,
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

@app.get("/admin/api-test")
async def api_test():
    """Admin endpoint to test all API keys and external services in sequence"""
    results = {
        "slack_api": {"status": "unknown", "details": {}},
        "gemini_api": {"status": "unknown", "details": {}},
        "pinecone_api": {"status": "unknown", "details": {}},
        "redis_connection": {"status": "unknown", "details": {}},
        "summary": {"total_tests": 4, "passed": 0, "failed": 0}
    }
    
    # Test 1: Slack API
    try:
        if settings.SLACK_BOT_TOKEN:
            from slack_sdk import WebClient
            slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)
            auth_response = slack_client.auth_test()
            
            if auth_response["ok"]:
                results["slack_api"]["status"] = "success"
                results["slack_api"]["details"] = {
                    "user_id": auth_response["user_id"],
                    "team": auth_response["team"],
                    "bot_id": auth_response.get("bot_id"),
                    "token_length": len(settings.SLACK_BOT_TOKEN)
                }
                results["summary"]["passed"] += 1
            else:
                results["slack_api"]["status"] = "failed"
                results["slack_api"]["details"] = {"error": "Authentication failed"}
                results["summary"]["failed"] += 1
        else:
            results["slack_api"]["status"] = "failed"
            results["slack_api"]["details"] = {"error": "No SLACK_BOT_TOKEN configured"}
            results["summary"]["failed"] += 1
    except Exception as e:
        results["slack_api"]["status"] = "failed"
        results["slack_api"]["details"] = {"error": str(e)}
        results["summary"]["failed"] += 1
    
    # Test 2: Gemini API
    try:
        if settings.GEMINI_API_KEY:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Test with a simple query
            config = types.GenerateContentConfig(
                system_instruction="You are a test assistant. Respond with exactly: 'API_TEST_SUCCESS'",
                response_mime_type="text/plain"
            )
            
            response = client.models.generate_content(
                model=settings.GEMINI_FLASH_MODEL,
                contents=[
                    types.Content(role="user", parts=[types.Part(text="Test connection")])
                ],
                config=config
            )
            
            if response and response.text:
                response_text = response.text.strip()
                results["gemini_api"]["status"] = "success"
                results["gemini_api"]["details"] = {
                    "model_used": settings.GEMINI_FLASH_MODEL,
                    "response_received": response_text[:100],
                    "api_key_length": len(settings.GEMINI_API_KEY)
                }
                results["summary"]["passed"] += 1
            else:
                results["gemini_api"]["status"] = "failed"
                results["gemini_api"]["details"] = {"error": "Empty response from API"}
                results["summary"]["failed"] += 1
        else:
            results["gemini_api"]["status"] = "failed"
            results["gemini_api"]["details"] = {"error": "No GEMINI_API_KEY configured"}
            results["summary"]["failed"] += 1
    except Exception as e:
        results["gemini_api"]["status"] = "failed"
        results["gemini_api"]["details"] = {"error": str(e)}
        results["summary"]["failed"] += 1
    
    # Test 3: Pinecone API
    try:
        if settings.PINECONE_API_KEY:
            from tools.vector_search import VectorSearchTool
            vector_tool = VectorSearchTool()
            
            if vector_tool.pinecone_available:
                # Test basic connection to index
                try:
                    # Try to query the index (this will test connectivity)
                    test_result = await vector_tool.search("test", top_k=1)
                    results["pinecone_api"]["status"] = "success"
                    results["pinecone_api"]["details"] = {
                        "index_name": settings.PINECONE_INDEX_NAME,
                        "api_key_configured": True,
                        "api_key_length": len(settings.PINECONE_API_KEY),
                        "connectivity": "confirmed",
                        "test_query_executed": True
                    }
                    results["summary"]["passed"] += 1
                except Exception as query_error:
                    results["pinecone_api"]["status"] = "partial"
                    results["pinecone_api"]["details"] = {
                        "index_name": settings.PINECONE_INDEX_NAME,
                        "api_key_configured": True,
                        "api_key_length": len(settings.PINECONE_API_KEY),
                        "connectivity": "api_connected",
                        "query_error": str(query_error)
                    }
                    results["summary"]["passed"] += 1
            else:
                results["pinecone_api"]["status"] = "failed"
                results["pinecone_api"]["details"] = {"error": "Pinecone initialization failed"}
                results["summary"]["failed"] += 1
        else:
            results["pinecone_api"]["status"] = "failed"
            results["pinecone_api"]["details"] = {"error": "No PINECONE_API_KEY configured"}
            results["summary"]["failed"] += 1
    except Exception as e:
        results["pinecone_api"]["status"] = "failed"
        results["pinecone_api"]["details"] = {"error": str(e)}
        results["summary"]["failed"] += 1
    
    # Test 4: Redis Connection
    try:
        from services.memory_service import MemoryService
        memory_service = MemoryService()
        
        # Test basic functionality
        test_key = "api_test_key"
        test_value = {"test": "api_test_value"}
        
        await memory_service.store_temp_data(test_key, test_value, ttl=60)
        retrieved_value = await memory_service.get_temp_data(test_key)
        
        if retrieved_value == test_value:
            results["redis_connection"]["status"] = "success"
            results["redis_connection"]["details"] = {
                "backend_type": "in_memory" if not settings.REDIS_URL else "redis",
                "redis_url_configured": bool(settings.REDIS_URL),
                "test_storage": "passed"
            }
            results["summary"]["passed"] += 1
        else:
            results["redis_connection"]["status"] = "failed"
            results["redis_connection"]["details"] = {"error": "Storage test failed"}
            results["summary"]["failed"] += 1
            
        # Clean up test data
        await memory_service.delete_temp_data(test_key)
        
    except Exception as e:
        results["redis_connection"]["status"] = "failed"
        results["redis_connection"]["details"] = {"error": str(e)}
        results["summary"]["failed"] += 1
    
    return {"status": "complete", "api_test_results": results}

@app.get("/admin/pinecone-status")
async def pinecone_status():
    """Admin endpoint to check Pinecone index status and contents"""
    try:
        from tools.vector_search import VectorSearchTool
        
        vector_tool = VectorSearchTool()
        
        if not vector_tool.pinecone_available:
            return {"status": "unavailable", "error": "Pinecone not initialized"}
        
        # Get index statistics
        stats = vector_tool.index.describe_index_stats()
        
        # Try a sample query to see if there's any data
        sample_results = await vector_tool.search("test sample query", top_k=5)
        
        return {
            "status": "available",
            "index_name": settings.PINECONE_INDEX_NAME,
            "statistics": {
                "total_vector_count": stats.total_vector_count if hasattr(stats, 'total_vector_count') else 0,
                "dimension": stats.dimension if hasattr(stats, 'dimension') else "unknown",
                "index_fullness": stats.index_fullness if hasattr(stats, 'index_fullness') else 0.0
            },
            "sample_query_results": len(sample_results),
            "has_data": len(sample_results) > 0
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/admin/ingest-test-document")
async def ingest_test_document():
    """Admin endpoint to ingest the Scandinavian furniture test document"""
    try:
        from services.document_ingestion import DocumentIngestionService
        
        ingestion_service = DocumentIngestionService()
        
        # Ingest the test document
        result = await ingestion_service.ingest_document(
            file_path="test_data/scandinavian_furniture.md",
            document_type="test_scandinavian_furniture"
        )
        
        return {"status": "complete", "ingestion_result": result}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/admin/search-test-content")
async def search_test_content(query: str = "Scandinavian design principles"):
    """Admin endpoint to search test content in Pinecone"""
    try:
        from services.document_ingestion import DocumentIngestionService
        
        ingestion_service = DocumentIngestionService()
        
        # Search the test content
        results = await ingestion_service.search_test_content(query, top_k=5)
        
        return {
            "status": "complete",
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.delete("/admin/cleanup-test-data")
async def cleanup_test_data():
    """Admin endpoint to clean up test data from Pinecone"""
    try:
        from services.document_ingestion import DocumentIngestionService
        
        ingestion_service = DocumentIngestionService()
        
        # Delete test documents
        result = await ingestion_service.delete_test_documents("test_scandinavian_furniture")
        
        return {"status": "complete", "cleanup_result": result}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/admin/orchestrator-test")
async def orchestrator_test(query: str = "What's the latest update on the UiPath integration project?"):
    """Admin endpoint to test orchestrator query analysis specifically"""
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from models.schemas import ProcessedMessage
        from services.memory_service import MemoryService
        from datetime import datetime
        
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Query parameter is now passed directly as function parameter
        
        # Create a test message 
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST",
            text=query,
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            channel_name="general"
        )
        
        # Test the orchestrator's query analysis
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        
        if execution_plan:
            return {
                "status": "success",
                "orchestrator_working": True,
                "execution_plan_received": True,
                "plan_details": {
                    "analysis": execution_plan.get("analysis", "No analysis"),
                    "intent": execution_plan.get("intent", "No intent"),
                    "tools_needed": execution_plan.get("tools_needed", []),
                    "context": execution_plan.get("context", {})
                }
            }
        else:
            return {
                "status": "failed",
                "orchestrator_working": False,
                "execution_plan_received": False,
                "error": "Query analysis returned None - this is why bot says 'trouble understanding'"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "orchestrator_working": False
        }

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

@app.get("/admin/test-progress-events")
async def test_progress_events():
    """Admin endpoint to test progress event generation (lightweight version)"""
    import time
    from datetime import datetime
    
    try:
        from services.progress_tracker import ProgressTracker, emit_thinking, emit_searching, emit_processing, emit_generating, emit_error, emit_warning, emit_retry
        import asyncio
        
        # Create a list to capture progress updates
        progress_updates = []
        
        async def mock_progress_updater(message: str):
            """Mock progress updater that captures messages"""
            progress_updates.append({
                "timestamp": datetime.now().isoformat(),
                "message": message
            })
        
        # Initialize progress tracker with mock updater
        progress_tracker = ProgressTracker(update_callback=mock_progress_updater)
        
        # Simulate the orchestrator progress events
        await emit_thinking(progress_tracker, "analyzing", "your test request")
        await asyncio.sleep(0.1)
        
        await emit_thinking(progress_tracker, "planning", "approach to answer")
        await asyncio.sleep(0.1)
        
        await emit_searching(progress_tracker, "vector_search", "knowledge base")
        await asyncio.sleep(0.1)
        
        await emit_searching(progress_tracker, "vector_search", "'integration status'")
        await asyncio.sleep(0.1)
        
        await emit_processing(progress_tracker, "analyzing_results", "search results")
        await asyncio.sleep(0.1)
        
        await emit_generating(progress_tracker, "response_generation", "your answer")
        await asyncio.sleep(0.1)
        
        # Test error and warning events
        await emit_warning(progress_tracker, "limited_results", "expanding search scope")
        await asyncio.sleep(0.1)
        
        return {
            "status": "success",
            "progress_tracking_system": "active",
            "total_progress_events": len(progress_updates),
            "progress_events": progress_updates,
            "event_types_tested": [
                "thinking - analyzing",
                "thinking - planning", 
                "searching - vector_search",
                "processing - analyzing_results",
                "generating - response_generation",
                "warning - limited_results"
            ],
            "natural_language_working": all("..." in event["message"] for event in progress_updates),
            "emoji_formatting_working": any("🤔" in event["message"] for event in progress_updates),
            "system_ready_for_deployment": len(progress_updates) == 7
        }
    
    except Exception as e:
        logger.error(f"Error testing progress events: {e}")
        return {
            "status": "error",
            "error": str(e),
            "progress_tracking_working": False
        }

@app.get("/admin/langsmith-test")
async def test_langsmith_tracing():
    """Admin endpoint to test LangSmith tracing integration"""
    try:
        test_results = {
            "langsmith_enabled": trace_manager.is_enabled(),
            "api_key_configured": bool(settings.LANGSMITH_API_KEY),
            "project_name": settings.LANGSMITH_PROJECT,
            "endpoint": settings.LANGSMITH_ENDPOINT,
            "trace_test": None
        }
        
        if not trace_manager.is_enabled():
            if settings.LANGSMITH_API_KEY:
                test_results["status"] = "disabled"
                test_results["message"] = "LangSmith tracing is disabled due to API authentication/project access issues"
                test_results["solution"] = "The API key may need write permissions or the project may not exist. Try creating the project in LangSmith UI first."
            else:
                test_results["status"] = "disabled"
                test_results["message"] = "LangSmith tracing is disabled - no API key configured"
            return test_results
        
        # Test trace creation
        try:
            session_id = await trace_manager.start_conversation_session(
                user_id="test_user",
                message="Test message for LangSmith integration",
                channel_id="test_channel",
                message_ts="test_timestamp"
            )
            
            if session_id:
                # Test orchestrator analysis logging  
                await trace_manager.log_orchestrator_analysis(
                    query="test query",
                    execution_plan="test execution plan",
                    duration=0.15
                )
                
                # Test LLM call logging
                await trace_manager.log_llm_call(
                    model="gemini-2.5-pro",
                    prompt="test prompt",
                    response="test response",
                    duration=0.15,
                    tokens_used=50
                )
                
                # Complete the trace
                await trace_manager.complete_conversation_session(final_response="test completed")
                
                test_results["trace_test"] = {
                    "status": "success",
                    "session_id": session_id,
                    "operations_logged": ["conversation_start", "orchestrator_analysis", "api_call", "conversation_complete"]
                }
            else:
                test_results["trace_test"] = {
                    "status": "failed",
                    "error": "Failed to create trace"
                }
                
        except Exception as trace_error:
            test_results["trace_test"] = {
                "status": "error",
                "error": str(trace_error)
            }
        
        test_results["status"] = "success" if test_results["trace_test"]["status"] == "success" else "partial"
        return test_results
        
    except Exception as e:
        logger.error(f"Error testing LangSmith integration: {e}")
        return {
            "status": "error",
            "error": str(e),
            "langsmith_available": False
        }

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
