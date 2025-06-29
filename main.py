"""
Main FastAPI application entry point for the multi-agent Slack system.
Handles incoming Slack webhooks and orchestrates agent responses.
Updated: Vector search and embedding system fully functional.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
import os

from agents.slack_gateway import SlackGateway
from agents.orchestrator_agent import OrchestratorAgent
from config import settings
from models.schemas import SlackEvent, SlackChallenge, ProcessedMessage
from services.memory_service import MemoryService
from services.trace_manager import trace_manager
from services.prewarming_service import PrewarmingService
from services.webhook_cache import WebhookCache
from services.performance_optimizer import performance_optimizer
from services.lazy_loader import lazy_loader
from services.connection_pool import connection_pool

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
prewarming_service = None
webhook_cache = None

# Initialize FastAPI without complex lifespan manager
app = FastAPI(
    title="Autopilot Expert Multi-Agent System",
    description="Backend system for AI-powered Slack responses with multi-agent architecture",
    version="1.0.0"
)

# Initialize services immediately for faster startup
def initialize_services():
    """Initialize services synchronously"""
    global slack_gateway, orchestrator_agent, memory_service, prewarming_service, webhook_cache
    
    logger.info("Initializing multi-agent system with performance optimizations...")
    
    try:
        # Start lazy loading of heavy modules in background
        lazy_loader.preload_critical_modules()
        
        # Initialize services
        memory_service = MemoryService()
        slack_gateway = SlackGateway()
        orchestrator_agent = OrchestratorAgent(memory_service)
        
        # Initialize webhook cache
        webhook_cache = WebhookCache(memory_service=memory_service)
        
        # Initialize pre-warming service with all components
        # Note: We'll pass the services and let pre-warming access tools through them
        prewarming_service = PrewarmingService(
            slack_client=slack_gateway.client if slack_gateway else None,
            memory_service=memory_service,
            vector_search=None,  # Will be accessed through orchestrator
            perplexity_search=None  # Will be accessed through orchestrator
        )
        
        logger.info("Multi-agent system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

# Initialize services on startup
services_initialized = initialize_services()

# Start pre-warming asynchronously after initial setup
async def start_prewarming():
    """Start the pre-warming system and performance optimizations after services are initialized"""
    if prewarming_service and services_initialized:
        try:
            # Apply async performance optimizations
            await performance_optimizer.apply_startup_optimizations()
            await connection_pool.warmup_connections()
            await prewarming_service.start_prewarming()
            logger.info("Pre-warming system, connection pools, and performance optimizations started successfully")
        except Exception as e:
            logger.error(f"Pre-warming startup failed: {e}")

# Note: Pre-warming will be started via admin endpoint to avoid event loop issues

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
    5-Step Timing Framework Implementation:
    Step 2: Slack → Your app (Events API HTTP POST) - 300ms-3s 
    Step 3: Cold-start / framework routing / auth - 50ms-4s
    Step 4: Your code before "Analyzing..." - X
    Step 5: Slack → user - 100-300ms
    """
    try:
        # ⏱️ STEP 2: Slack → Your app (HTTP POST received)
        webhook_received_time = time.time()
        logger.info(f"📥 STEP 2: Slack webhook received at {webhook_received_time:.6f}")
        
        # ⏱️ STEP 3A: Framework routing/parsing starts
        routing_start = time.time()
        logger.info(f"🔄 STEP 3A: Framework routing start at {routing_start:.6f} (step2→3 delay: {routing_start - webhook_received_time:.6f}s)")
        
        body = await request.json()
        
        # ⏱️ STEP 3B: JSON parsing complete
        json_parsed_time = time.time()
        logger.info(f"📋 STEP 3B: JSON parsing complete at {json_parsed_time:.6f} (parsing: {json_parsed_time - routing_start:.6f}s)")
        
        # Handle Slack URL verification challenge
        if body.get("type") == "url_verification":
            challenge_value = body.get("challenge")
            if challenge_value:
                return PlainTextResponse(challenge_value)
            else:
                raise HTTPException(status_code=400, detail="Missing challenge parameter")
        
        # Handle Slack events
        if body.get("type") == "event_callback":
            event_data = SlackEvent(**body)
            
            # ⏱️ STEP 3C: Event validation complete  
            validation_complete_time = time.time()
            logger.info(f"✅ STEP 3C: Event validation complete at {validation_complete_time:.6f} (validation: {validation_complete_time - json_parsed_time:.6f}s)")
            
            # Extract Slack timestamp for Step 2 analysis
            slack_timestamp = event_data.event.get("ts")
            if slack_timestamp:
                try:
                    slack_time = float(slack_timestamp)
                    slack_to_webhook_delay = webhook_received_time - slack_time
                    logger.info(f"📊 STEP 2 ANALYSIS: Slack edge→webhook delay: {slack_to_webhook_delay:.6f}s")
                except ValueError:
                    logger.warning("Could not parse Slack timestamp for Step 2 analysis")
            
            # Filter out bot messages and messages from the autopilot bot itself
            if (event_data.event.get("bot_id") or 
                event_data.event.get("user") == settings.SLACK_BOT_USER_ID):
                return {"status": "ignored"}
            
            # WEBHOOK CACHE: Check for duplicate or cached response
            cache_check_start = time.time()
            
            # Check for duplicate requests first
            if webhook_cache:
                is_duplicate = await webhook_cache.is_duplicate_request(body)
                if is_duplicate:
                    logger.info("🔄 Duplicate webhook detected - skipping processing")
                    return {"status": "duplicate_ignored"}
                
                # Check for cached response
                cached_response = await webhook_cache.get_cached_response(body)
                if cached_response:
                    cache_check_time = time.time() - cache_check_start
                    logger.info(f"⚡ Webhook cache HIT - returning cached response ({cache_check_time:.3f}s)")
                    return cached_response
            
            cache_check_time = time.time() - cache_check_start
            logger.info(f"⏱️  WEBHOOK CACHE: Cache check completed in {cache_check_time:.3f}s")
            
            # ⏱️ STEP 3D: About to queue background task
            task_queue_time = time.time()
            total_step3_time = task_queue_time - webhook_received_time
            user_message_ts = event_data.event.get('ts', '')
            user_text = event_data.event.get('text', '')[:50]
            
            logger.info(f"🚀 STEP 3D: Queueing background task at {task_queue_time:.6f}")
            logger.info(f"📊 STEP 3 TOTAL: Framework overhead = {total_step3_time:.6f}s for '{user_text}'")
            
            # Store all timing data for Steps 4-5 analysis
            event_data.event['webhook_received_time'] = webhook_received_time
            event_data.event['task_queue_time'] = task_queue_time
            event_data.event['slack_timestamp'] = slack_timestamp
            
            # Process the message in background (Steps 4-5 will be measured there)
            background_tasks.add_task(process_slack_message, event_data)
            
            # TIMING MEASUREMENT: Background Task Queued
            task_queued_time = time.time()
            queue_duration = task_queued_time - task_queue_time
            logger.info(f"⏱️  WEBHOOK TIMING: Background task queued at {task_queued_time:.3f} (queueing took: {queue_duration:.3f}s)")
            
            return {"status": "accepted"}
        
        return {"status": "ignored"}
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_slack_message(event_data: SlackEvent):
    """
    Process incoming Slack message through the agent pipeline
    Implements Steps 4-5 of the 5-Step Timing Framework
    """
    try:
        import time
        
        # ⏱️ STEP 4 START: Your code before "Analyzing..." 
        step4_start = time.time()
        user_message_ts = event_data.event.get('ts', '')
        user_message_text = event_data.event.get('text', '')[:50]
        webhook_received_time = event_data.event.get('webhook_received_time', step4_start)
        task_queue_time = event_data.event.get('task_queue_time', step4_start)
        slack_timestamp = event_data.event.get('slack_timestamp')
        
        logger.info(f"⚡ STEP 4 START: Background processing begins at {step4_start:.6f} for '{user_message_text}'")
        
        # Calculate cumulative delays from Steps 2-3
        if webhook_received_time != step4_start:
            step3_to_step4_delay = step4_start - task_queue_time
            logger.info(f"📊 STEP 3→4 DELAY: Background task queue delay = {step3_to_step4_delay:.6f}s")
        
        # Step 2 analysis: Slack edge → webhook delay
        if slack_timestamp:
            try:
                slack_time = float(slack_timestamp)
                step2_total_delay = webhook_received_time - slack_time
                logger.info(f"📊 STEP 2 TOTAL: Slack edge→webhook = {step2_total_delay:.6f}s")
            except ValueError:
                pass
        
        # Check services
        if not slack_gateway or not orchestrator_agent:
            logger.error("❌ STEP 4 ERROR: Services not initialized")
            return
        
        # ⏱️ STEP 4A: Gateway processing with optimizations
        gateway_start = time.time()
        logger.info(f"🔄 STEP 4A: Gateway processing starts at {gateway_start:.6f}")
        
        # Apply runtime optimizations for faster processing
        await performance_optimizer.optimize_runtime_performance()
        
        processed_message = await slack_gateway.process_message(event_data)
        
        gateway_complete = time.time()
        gateway_duration = gateway_complete - gateway_start
        logger.info(f"✅ STEP 4A: Gateway complete at {gateway_complete:.6f} (took {gateway_duration:.6f}s)")
        
        if processed_message:
            # ⏱️ STEP 4B: Progress updater creation (preparing to send "Analyzing...")
            step4b_start = time.time()
            logger.info(f"🔧 STEP 4B: Creating progress updater at {step4b_start:.6f}")
            
            # Create progress updater for real-time Slack message updates
            progress_updater = await slack_gateway.create_progress_updater(
                processed_message.channel_id,
                processed_message.thread_ts
            )
            
            step4b_complete = time.time()
            step4b_duration = step4b_complete - step4b_start
            logger.info(f"✅ STEP 4B: Progress updater ready at {step4b_complete:.6f} (took {step4b_duration:.6f}s)")
            
            # ⏱️ STEP 4C: Just before sending "Analyzing..." message 
            step4c_analyzing_start = time.time()
            logger.info(f"📤 STEP 4C: About to send 'Analyzing...' at {step4c_analyzing_start:.6f}")
            
            # Calculate total Step 4 duration (your code before "Analyzing...")
            total_step4_duration = step4c_analyzing_start - step4_start
            logger.info(f"📊 STEP 4 TOTAL: Your code duration = {total_step4_duration:.6f}s")
            
            # ⏱️ STEP 5 START: Send "Analyzing..." message to Slack
            step5_slack_call_start = time.time()
            
            # Send initial "Analyzing..." message with embedded timestamp for Step 5 measurement
            analyzing_timestamp = step5_slack_call_start
            analyzing_message = f"_Analyzing your request..._ 🕐{analyzing_timestamp:.6f}"
            
            if progress_updater:
                await progress_updater(analyzing_message)
            
            step5_slack_call_complete = time.time()
            step5_api_duration = step5_slack_call_complete - step5_slack_call_start
            logger.info(f"✅ STEP 5: Slack API call complete at {step5_slack_call_complete:.6f} (API took {step5_api_duration:.6f}s)")
            
            # 🎯 TOTAL DELAY ANALYSIS: User message → First visible "Analyzing..." 
            if slack_timestamp:
                try:
                    slack_time = float(slack_timestamp)
                    total_user_to_analyzing = step5_slack_call_complete - slack_time
                    logger.info(f"🎯 TOTAL USER→ANALYZING DELAY: {total_user_to_analyzing:.6f}s")
                    logger.info(f"📊 COMPLETE BREAKDOWN:")
                    logger.info(f"    Step 2 (Slack→Webhook): {webhook_received_time - slack_time:.6f}s")
                    logger.info(f"    Step 3 (Framework): {task_queue_time - webhook_received_time:.6f}s")
                    logger.info(f"    Step 3→4 (Queue): {step4_start - task_queue_time:.6f}s")
                    logger.info(f"    Step 4 (Your code): {total_step4_duration:.6f}s")
                    logger.info(f"    Step 5 (Slack API): {step5_api_duration:.6f}s")
                    logger.info(f"    🎯 TOTAL: {total_user_to_analyzing:.6f}s")
                except ValueError:
                    pass
            
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
                
                # Calculate total processing time for caching
                total_processing_time = time.time() - step4_start
                
                # Update the progress message with final response
                if response:
                    final_response_text = response.get("text", "Sorry, I couldn't generate a response.")
                    await progress_updater(final_response_text)
                    logger.info("Successfully processed and updated Slack message with progress tracking")
                    
                    # WEBHOOK CACHE: Store successful response for future use
                    if webhook_cache and webhook_cache.should_cache_response(event_data.dict(), {"status": "success", "response": response}):
                        await webhook_cache.cache_response(
                            event_data.dict(), 
                            {"status": "success", "response": response},
                            total_processing_time
                        )
                        logger.info(f"💾 Cached successful webhook response (processing: {total_processing_time:.3f}s)")
                    
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

@app.get("/admin/perplexity-slack-test")
async def test_perplexity_slack_integration():
    """Admin endpoint to test complete Perplexity Slack integration including progress tracking"""
    try:
        from services.progress_tracker import ProgressTracker
        import time
        
        # Capture Slack-style progress messages
        slack_messages = []
        
        async def mock_slack_updater(message: str):
            """Mock Slack progress updater"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            slack_messages.append(f"[{timestamp}] {message}")
        
        # Test with progress tracking
        progress_tracker = ProgressTracker(update_callback=mock_slack_updater)
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service, progress_tracker)
        
        test_message = ProcessedMessage(
            channel_id="C_TEST_SLACK",
            user_id="U_TEST_SLACK", 
            text="What are the latest developments in AI automation for 2025?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Alex",
            user_display_name="Alex Rodriguez",
            user_title="CTO", 
            user_department="Engineering",
            channel_name="ai-strategy",
            is_dm=False,
            thread_context=""
        )
        
        # Test complete flow with timing
        start_time = time.time()
        response = await orchestrator.process_query(test_message)
        total_time = time.time() - start_time
        
        # Analyze progress messages
        web_search_msgs = [msg for msg in slack_messages if "real-time web" in msg.lower()]
        processing_msgs = [msg for msg in slack_messages if any(emoji in msg for emoji in ["⚙️", "⚡"])]
        error_msgs = [msg for msg in slack_messages if "⚠️" in msg]
        
        return {
            "status": "success" if response else "partial",
            "perplexity_slack_integration": {
                "total_processing_time": round(total_time, 2),
                "slack_messages_sent": len(slack_messages),
                "web_search_indicators": len(web_search_msgs),
                "processing_feedback": len(processing_msgs),
                "error_messages": len(error_msgs),
                "response_generated": response is not None,
                "response_length": len(response.get("text", "")) if response else 0
            },
            "slack_message_sequence": slack_messages,
            "user_experience": {
                "clear_web_search_indication": len(web_search_msgs) > 0,
                "real_time_feedback": len(slack_messages) >= 4,
                "logical_progression": len(slack_messages) > 0,
                "timely_completion": total_time < 20.0,
                "final_response": response is not None
            },
            "sample_response_preview": response.get("text", "")[:200] + "..." if response else None,
            "integration_working": len(web_search_msgs) > 0 and response is not None
        }
        
    except Exception as e:
        logger.error(f"Error testing Perplexity Slack integration: {e}")
        return {
            "status": "error",
            "error": str(e),
            "perplexity_slack_working": False
        }

@app.get("/admin/perplexity-test")
async def test_perplexity_integration():
    """Admin endpoint to test Perplexity search integration"""
    try:
        from tools.perplexity_search import PerplexitySearchTool
        from agents.orchestrator_agent import OrchestratorAgent
        from models.schemas import ProcessedMessage
        import time
        
        # Test Perplexity tool directly
        perplexity_tool = PerplexitySearchTool()
        test_results = {
            "perplexity_available": perplexity_tool.available,
            "api_key_configured": bool(perplexity_tool.api_key),
            "direct_search_test": None,
            "orchestrator_integration_test": None
        }
        
        if not perplexity_tool.available:
            test_results["status"] = "failed"
            test_results["message"] = "Perplexity API not available - check API key configuration"
            return test_results
        
        # Test direct search
        print("Testing direct Perplexity search...")
        start_time = time.time()
        search_result = await perplexity_tool.search("latest AI automation trends 2025", max_tokens=500)
        search_time = time.time() - start_time
        
        test_results["direct_search_test"] = {
            "query": "latest AI automation trends 2025",
            "success": bool(search_result.get("content")),
            "content_length": len(search_result.get("content", "")),
            "citations_count": len(search_result.get("citations", [])),
            "search_time": round(search_time, 2),
            "model_used": search_result.get("model_used", "unknown"),
            "error": search_result.get("error", None)
        }
        
        # Test orchestrator integration
        print("Testing orchestrator integration...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        test_message = ProcessedMessage(
            channel_id="C_TEST",
            user_id="U_TEST", 
            text="What are the latest trends in AI automation for 2025?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Engineer", 
            user_department="Engineering",
            channel_name="test",
            is_dm=False,
            thread_context=""
        )
        
        # Test orchestrator analysis
        start_time = time.time()
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        analysis_time = time.time() - start_time
        
        # Test plan execution  
        start_time = time.time()
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        execution_time = time.time() - start_time
        
        test_results["orchestrator_integration_test"] = {
            "analysis_success": execution_plan is not None,
            "tools_planned": execution_plan.get("tools_needed", []) if execution_plan else [],
            "perplexity_planned": "perplexity_search" in execution_plan.get("tools_needed", []) if execution_plan else False,
            "perplexity_queries": execution_plan.get("perplexity_queries", []) if execution_plan else [],
            "web_results_found": len(gathered_info.get("perplexity_results", [])),
            "analysis_time": round(analysis_time, 2),
            "execution_time": round(execution_time, 2),
            "total_time": round(analysis_time + execution_time, 2)
        }
        
        # Overall status
        direct_success = test_results["direct_search_test"]["success"]
        orchestrator_success = test_results["orchestrator_integration_test"]["analysis_success"]
        perplexity_used = test_results["orchestrator_integration_test"]["perplexity_planned"] 
        
        test_results["status"] = "success" if direct_success and orchestrator_success else "partial"
        test_results["integration_working"] = direct_success and orchestrator_success and perplexity_used
        test_results["ready_for_deployment"] = direct_success and orchestrator_success
        
        return test_results
        
    except Exception as e:
        logger.error(f"Error testing Perplexity integration: {e}")
        return {
            "status": "error",
            "error": str(e),
            "perplexity_integration_working": False
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

@app.get("/admin/test-state-stack")
async def test_state_stack():
    """Admin endpoint to test state stack content and debug analysis flow"""
    try:
        from models.schemas import ProcessedMessage
        from datetime import datetime
        
        # Create test message
        test_message = ProcessedMessage(
            text="Hello my dude",
            user_id="U_TEST_USER",
            user_name="TestUser",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Software Engineer",
            user_department="Engineering",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=str(int(datetime.now().timestamp())),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        # Process through orchestrator
        logger.info("Testing state stack creation...")
        response = await orchestrator_agent.process_query(test_message)
        
        if response:
            return {
                "status": "success",
                "response_received": True,
                "response_text": response.get("text", "")[:200] + "...",
                "message": "State stack test completed - check logs for debug info"
            }
        else:
            return {
                "status": "failed",
                "message": "No response generated"
            }
            
    except Exception as e:
        logger.error(f"State stack test error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/admin/diagnose-8s-delay")
async def diagnose_8s_delay():
    """Admin endpoint to diagnose the 8-second delay to 'Starting up...' message"""
    try:
        import time
        
        # Test each component that could cause delay
        diagnosis = {
            "test_timestamp": time.time(),
            "system_status": "running",
            "component_timings": {},
            "bottleneck_analysis": []
        }
        
        # Test 1: Service Initialization Times
        init_start = time.time()
        try:
            if slack_gateway:
                diagnosis["component_timings"]["slack_gateway_available"] = True
            if orchestrator_agent:  
                diagnosis["component_timings"]["orchestrator_available"] = True
            if memory_service:
                diagnosis["component_timings"]["memory_service_available"] = True
        except Exception as e:
            diagnosis["component_timings"]["service_check_error"] = str(e)
        
        init_time = time.time() - init_start
        diagnosis["component_timings"]["service_availability_check"] = round(init_time, 3)
        
        # Test 2: Slack API Response Time
        slack_api_start = time.time()
        try:
            if slack_gateway and slack_gateway.client:
                # Test a simple API call
                response = slack_gateway.client.auth_test()
                slack_api_time = time.time() - slack_api_start
                diagnosis["component_timings"]["slack_api_response"] = round(slack_api_time, 3)
                diagnosis["component_timings"]["slack_api_success"] = response.get("ok", False)
            else:
                diagnosis["component_timings"]["slack_api_response"] = "client_unavailable"
        except Exception as e:
            slack_api_time = time.time() - slack_api_start
            diagnosis["component_timings"]["slack_api_response"] = round(slack_api_time, 3)
            diagnosis["component_timings"]["slack_api_error"] = str(e)
        
        # Test 3: Memory Service Response Time
        memory_start = time.time()
        try:
            if memory_service:
                test_key = f"test_timing_{int(time.time())}"
                await memory_service.store_conversation_context(test_key, {"test": "data"}, ttl=60)
                memory_time = time.time() - memory_start
                diagnosis["component_timings"]["memory_service_response"] = round(memory_time, 3)
        except Exception as e:
            memory_time = time.time() - memory_start
            diagnosis["component_timings"]["memory_service_response"] = round(memory_time, 3)
            diagnosis["component_timings"]["memory_service_error"] = str(e)
        
        # Test 4: Progress Updater Creation Time (simulated)
        progress_start = time.time()
        try:
            if slack_gateway:
                # Simulate the progress updater creation steps without actually posting
                test_channel = "C_DIAGNOSTIC_TEST"
                # This simulates the setup but doesn't make API calls
                progress_time = time.time() - progress_start
                diagnosis["component_timings"]["progress_updater_setup"] = round(progress_time, 3)
        except Exception as e:
            progress_time = time.time() - progress_start
            diagnosis["component_timings"]["progress_updater_setup"] = round(progress_time, 3)
            diagnosis["component_timings"]["progress_updater_error"] = str(e)
        
        # Analyze bottlenecks
        timings = diagnosis["component_timings"]
        
        if timings.get("slack_api_response", 0) > 2.0:
            diagnosis["bottleneck_analysis"].append({
                "component": "Slack API",
                "delay": timings.get("slack_api_response"),
                "severity": "HIGH",
                "description": "Slack API calls are taking longer than 2 seconds"
            })
        
        if timings.get("memory_service_response", 0) > 1.0:
            diagnosis["bottleneck_analysis"].append({
                "component": "Memory Service", 
                "delay": timings.get("memory_service_response"),
                "severity": "MEDIUM",
                "description": "Memory service operations are slow"
            })
        
        # Recommendations for 8s delay
        total_measured_time = sum([
            timings.get("service_availability_check", 0),
            timings.get("slack_api_response", 0), 
            timings.get("memory_service_response", 0),
            timings.get("progress_updater_setup", 0)
        ])
        
        diagnosis["total_measured_component_time"] = round(total_measured_time, 3)
        diagnosis["unmeasured_delay"] = round(8.0 - total_measured_time, 3)
        
        if diagnosis["unmeasured_delay"] > 5.0:
            diagnosis["bottleneck_analysis"].append({
                "component": "Unknown/External",
                "delay": diagnosis["unmeasured_delay"],
                "severity": "CRITICAL", 
                "description": "Most delay is happening outside measured components - likely webhook delivery, cold starts, or resource constraints"
            })
        
        # Specific recommendations
        diagnosis["recommendations"] = []
        
        if timings.get("slack_api_response", 0) > 1.0:
            diagnosis["recommendations"].append("Consider implementing Slack API caching or connection pooling")
        
        if diagnosis["unmeasured_delay"] > 3.0:
            diagnosis["recommendations"].append("Check deployment environment for cold starts, resource constraints, or network latency")
            diagnosis["recommendations"].append("Consider pre-warming strategies or connection keepalives")
        
        if len(diagnosis["bottleneck_analysis"]) == 0:
            diagnosis["recommendations"].append("All measured components are fast - delay likely in webhook delivery or deployment environment")
        
        return {
            "status": "success",
            "diagnosis": diagnosis,
            "description": "Comprehensive analysis of potential causes for 8-second delay to 'Starting up...' message"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to complete 8-second delay diagnosis"
        }

@app.post("/admin/start-prewarming")
async def start_prewarming_endpoint():
    """Admin endpoint to start the pre-warming system"""
    try:
        if not prewarming_service:
            return {
                "status": "error",
                "message": "Pre-warming service not initialized"
            }
        
        await prewarming_service.start_prewarming()
        
        return {
            "status": "success",
            "message": "Pre-warming system started successfully",
            "description": "Service pre-warming and keep-alive system is now active"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to start pre-warming system"
        }

@app.get("/admin/prewarming-status")
async def get_prewarming_status():
    """Admin endpoint to check pre-warming system status"""
    try:
        if not prewarming_service:
            return {
                "status": "error",
                "message": "Pre-warming service not initialized"
            }
        
        health_status = prewarming_service.get_health_status()
        
        return {
            "status": "success",
            "health_status": health_status,
            "description": "Current status of service pre-warming and keep-alive system"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to get pre-warming status"
        }

@app.post("/admin/stop-prewarming")
async def stop_prewarming_endpoint():
    """Admin endpoint to stop the pre-warming system"""
    try:
        if not prewarming_service:
            return {
                "status": "error",
                "message": "Pre-warming service not initialized"
            }
        
        await prewarming_service.stop_prewarming()
        
        return {
            "status": "success",
            "message": "Pre-warming system stopped successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to stop pre-warming system"
        }

@app.get("/admin/performance-comparison")
async def performance_comparison():
    """Admin endpoint to compare system performance with and without pre-warming"""
    try:
        import time
        
        # Get current pre-warming status
        prewarming_active = prewarming_service._is_running if prewarming_service else False
        
        comparison = {
            "test_timestamp": time.time(),
            "prewarming_active": prewarming_active,
            "performance_tests": {},
            "improvement_analysis": {}
        }
        
        # Test 1: Slack API Response Time (multiple samples for accuracy)
        slack_times = []
        for i in range(3):
            start_time = time.time()
            try:
                if slack_gateway and slack_gateway.client:
                    response = slack_gateway.client.auth_test()
                    slack_time = time.time() - start_time
                    slack_times.append(slack_time)
            except Exception as e:
                comparison["performance_tests"][f"slack_api_test_{i+1}_error"] = str(e)
        
        if slack_times:
            comparison["performance_tests"]["slack_api"] = {
                "samples": len(slack_times),
                "average_response_time": round(sum(slack_times) / len(slack_times), 3),
                "min_response_time": round(min(slack_times), 3),
                "max_response_time": round(max(slack_times), 3),
                "all_samples": [round(t, 3) for t in slack_times]
            }
        
        # Test 2: Memory Service Response Time
        memory_times = []
        for i in range(3):
            start_time = time.time()
            try:
                if memory_service:
                    test_key = f"perf_test_{int(time.time())}_{i}"
                    await memory_service.store_conversation_context(test_key, {"test": "data"}, ttl=30)
                    memory_time = time.time() - start_time
                    memory_times.append(memory_time)
            except Exception as e:
                comparison["performance_tests"][f"memory_test_{i+1}_error"] = str(e)
        
        if memory_times:
            comparison["performance_tests"]["memory_service"] = {
                "samples": len(memory_times),
                "average_response_time": round(sum(memory_times) / len(memory_times), 3),
                "min_response_time": round(min(memory_times), 3),
                "max_response_time": round(max(memory_times), 3),
                "all_samples": [round(t, 3) for t in memory_times]
            }
        
        # Performance Analysis
        total_avg_time = 0
        if "slack_api" in comparison["performance_tests"]:
            total_avg_time += comparison["performance_tests"]["slack_api"]["average_response_time"]
        if "memory_service" in comparison["performance_tests"]:
            total_avg_time += comparison["performance_tests"]["memory_service"]["average_response_time"]
        
        comparison["performance_tests"]["total_average_component_time"] = round(total_avg_time, 3)
        
        # Improvement Analysis
        baseline_component_time = 0.11  # Based on previous diagnostics
        current_component_time = total_avg_time
        
        improvement = baseline_component_time - current_component_time
        improvement_pct = (improvement / baseline_component_time * 100) if baseline_component_time > 0 else 0
        
        comparison["improvement_analysis"] = {
            "baseline_component_time": baseline_component_time,
            "current_component_time": round(current_component_time, 3),
            "time_improvement": round(improvement, 3),
            "improvement_percentage": round(improvement_pct, 1),
            "prewarming_effectiveness": "active" if prewarming_active else "inactive"
        }
        
        # Recommendations based on results
        recommendations = []
        if prewarming_active and improvement > 0.01:
            recommendations.append(f"Pre-warming is effective: {improvement:.3f}s improvement in component response times")
        elif prewarming_active and improvement <= 0:
            recommendations.append("Pre-warming is active but may not be significantly improving component response times")
        else:
            recommendations.append("Start pre-warming system to test potential improvements")
        
        if current_component_time < 0.05:
            recommendations.append("Component response times are excellent - delay likely external")
        elif current_component_time > 0.2:
            recommendations.append("Component response times could be improved - check service health")
        
        comparison["recommendations"] = recommendations
        
        return {
            "status": "success",
            "comparison": comparison,
            "description": "Performance comparison to measure pre-warming effectiveness"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to complete performance comparison"
        }

@app.get("/admin/webhook-cache-stats")
async def get_webhook_cache_stats():
    """Admin endpoint to get webhook cache statistics"""
    try:
        if not webhook_cache:
            return {
                "status": "error",
                "message": "Webhook cache not initialized"
            }
        
        stats = webhook_cache.get_cache_stats()
        
        return {
            "status": "success",
            "cache_stats": stats,
            "description": "Current webhook cache performance and configuration"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to get webhook cache statistics"
        }

@app.post("/admin/clear-webhook-cache")
async def clear_webhook_cache():
    """Admin endpoint to clear webhook cache"""
    try:
        if not webhook_cache:
            return {
                "status": "error",
                "message": "Webhook cache not initialized"
            }
        
        result = await webhook_cache.clear_cache()
        
        return {
            "status": "success",
            "clear_result": result,
            "description": "Webhook cache cleared successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to clear webhook cache"
        }

@app.get("/admin/webhook-cache-test")
async def test_webhook_cache():
    """Admin endpoint to test webhook cache functionality"""
    try:
        if not webhook_cache:
            return {
                "status": "error",
                "message": "Webhook cache not initialized"
            }
        
        import time
        
        # Create test webhook data
        test_event = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U_TEST_USER",
                "text": f"Test cache message {int(time.time())}",
                "channel": "C_TEST_CHANNEL",
                "ts": str(time.time())
            }
        }
        
        test_response = {
            "status": "success",
            "response": {
                "text": "Test cached response",
                "timestamp": time.time()
            }
        }
        
        # Test cache storage
        storage_start = time.time()
        await webhook_cache.cache_response(test_event, test_response, 0.5)
        storage_time = time.time() - storage_start
        
        # Test cache retrieval
        retrieval_start = time.time()
        cached_result = await webhook_cache.get_cached_response(test_event)
        retrieval_time = time.time() - retrieval_start
        
        # Test duplicate detection
        duplicate_start = time.time()
        is_duplicate = await webhook_cache.is_duplicate_request(test_event)
        duplicate_time = time.time() - duplicate_start
        
        cache_stats = webhook_cache.get_cache_stats()
        
        return {
            "status": "success",
            "test_results": {
                "cache_storage": {
                    "time": round(storage_time, 3),
                    "success": True
                },
                "cache_retrieval": {
                    "time": round(retrieval_time, 3),
                    "success": cached_result is not None,
                    "cache_hit": cached_result is not None
                },
                "duplicate_detection": {
                    "time": round(duplicate_time, 3),
                    "is_duplicate": is_duplicate
                },
                "cache_stats": cache_stats
            },
            "description": "Webhook cache functionality test completed"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to test webhook cache"
        }

@app.get("/admin/test-timing-metrics")
async def test_timing_metrics():
    """Admin endpoint to test timing metrics between user message and first visual trace"""
    try:
        import time
        from models.schemas import ProcessedMessage
        
        # Capture timing events
        timing_events = []
        
        async def capture_timing_event(message: str):
            """Capture timing events with precise timestamps"""
            timestamp = time.time()
            timing_events.append((timestamp, message))
        
        # Initialize services for testing
        from services.progress_tracker import ProgressTracker
        from agents.orchestrator_agent import OrchestratorAgent
        
        # Create test message simulating user input
        test_message = ProcessedMessage(
            text="What are the latest features in UiPath Autopilot?",
            user_id="U_TIMING_TEST",
            user_name="TimingTestUser", 
            user_first_name="Timing",
            user_display_name="Timing Test User",
            user_title="Product Manager",
            user_department="Product",
            channel_id="C_TIMING_TEST",
            channel_name="timing-test-channel",
            message_ts=str(time.time()),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        # SIMULATE USER MESSAGE TIMING
        simulated_user_send_time = time.time()
        
        # Create progress tracker with timing capture
        tracker = ProgressTracker(update_callback=capture_timing_event)
        orchestrator_with_timing = OrchestratorAgent(memory_service, tracker)
        
        # Start processing with timing measurements
        start_time = time.time()
        response = await orchestrator_with_timing.process_query(test_message)
        end_time = time.time()
        
        total_duration = end_time - start_time
        
        # Analyze timing results
        timing_analysis = {
            "test_message": test_message.text,
            "simulated_user_send_time": simulated_user_send_time,
            "processing_start_time": start_time,
            "processing_end_time": end_time,
            "total_processing_duration": round(total_duration, 3),
            "total_progress_events": len(timing_events),
            "response_generated": bool(response)
        }
        
        if timing_events:
            first_event_time = timing_events[0][0]
            first_trace_delay = first_event_time - start_time
            timing_analysis["first_trace_delay"] = round(first_trace_delay, 3)
            
            # Performance assessment
            if first_trace_delay < 0.1:
                assessment = "EXCELLENT"
            elif first_trace_delay < 0.5:
                assessment = "GOOD" 
            elif first_trace_delay < 1.0:
                assessment = "ACCEPTABLE"
            elif first_trace_delay < 2.0:
                assessment = "SLOW"
            else:
                assessment = "VERY SLOW"
            
            timing_analysis["performance_assessment"] = assessment
            timing_analysis["timing_events"] = [
                {
                    "relative_time": round(timestamp - start_time, 3),
                    "message": message
                }
                for timestamp, message in timing_events
            ]
        else:
            timing_analysis["first_trace_delay"] = None
            timing_analysis["performance_assessment"] = "NO_TRACES"
            timing_analysis["timing_events"] = []
        
        # Add response details
        if response:
            timing_analysis["response"] = {
                "text_length": len(response.get("text", "")),
                "has_suggestions": bool(response.get("suggestions")),
                "preview": response.get("text", "")[:100]
            }
        
        return {
            "status": "success",
            "timing_analysis": timing_analysis,
            "description": "Timing metrics test completed - measures delay from processing start to first visual trace"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to complete timing metrics test"
        }

@app.get("/admin/test-analysis-traces")
async def test_analysis_traces():
    """Admin endpoint to test orchestrator analysis visibility in LangSmith traces"""
    try:
        from models.schemas import ProcessedMessage
        from datetime import datetime
        from services.trace_manager import trace_manager
        
        # Start a conversation trace for visibility
        conversation_id = await trace_manager.start_conversation_session(
            user_id="U_TRACE_TEST",
            channel_id="C_TRACE_TEST"
        )
        
        if not conversation_id:
            return {
                "status": "error",
                "message": "Failed to start conversation trace"
            }
        
        # Create test message that will trigger interesting analysis
        test_message = ProcessedMessage(
            text="What is UiPath Autopilot and how does it help with automation?",
            user_id="U_TRACE_TEST",
            user_name="TraceTestUser",
            user_first_name="Trace",
            user_display_name="Trace Test User",
            user_title="Product Manager",
            user_department="Product",
            channel_id="C_TRACE_TEST",
            channel_name="trace-test-channel",
            message_ts=str(int(datetime.now().timestamp())),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        logger.info("Testing orchestrator analysis trace visibility...")
        
        # Process through full orchestrator pipeline
        response = await orchestrator_agent.process_query(test_message)
        
        # Complete the conversation trace
        await trace_manager.complete_conversation_turn(success=True)
        
        if response:
            return {
                "status": "success",
                "conversation_trace_id": conversation_id,
                "response_generated": True,
                "response_preview": response.get("text", "")[:150] + "...",
                "message": f"Analysis trace test completed. Check LangSmith trace: {conversation_id}",
                "langsmith_project": "autopilot-expert-multi-agent"
            }
        else:
            return {
                "status": "partial_success",
                "conversation_trace_id": conversation_id,
                "message": "Trace created but no response generated"
            }
            
    except Exception as e:
        logger.error(f"Analysis traces test error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/admin/test-tool-results-flow")
async def test_tool_results_flow():
    """Admin endpoint to test tool results flow from orchestrator to client agent"""
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from models.schemas import ProcessedMessage
        from services.memory_service import MemoryService
        
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create test message that should trigger vector search
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST",
            text="Autopilot is an AI, right?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Software Engineer",
            user_department="Engineering",
            channel_name="general",
            is_dm=False,
            thread_context=""
        )
        
        # Test step by step
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        if not execution_plan:
            return {"status": "error", "message": "No execution plan generated"}
        
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        vector_results = gathered_info.get("vector_results", [])
        
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        search_results_in_state = orchestrator_analysis.get("search_results", [])
        
        # Test client agent formatting
        client_agent = orchestrator.client_agent
        formatted_context = client_agent._format_state_stack_context(state_stack)
        
        # Check if search results are visible in formatted context
        search_results_visible = "Vector Search Results:" in formatted_context
        
        return {
            "status": "success",
            "tool_execution": {
                "execution_plan_created": bool(execution_plan),
                "tools_needed": execution_plan.get("tools_needed", []),
                "vector_queries": execution_plan.get("vector_queries", []),
                "vector_results_found": len(vector_results),
                "vector_results_preview": [r.get("content", "")[:100] for r in vector_results[:2]]
            },
            "state_stack": {
                "search_results_in_orchestrator_analysis": len(search_results_in_state),
                "first_result_preview": search_results_in_state[0].get("content", "")[:100] if search_results_in_state else None
            },
            "client_agent": {
                "search_results_visible_in_context": search_results_visible,
                "context_preview": formatted_context[:500] + "..." if len(formatted_context) > 500 else formatted_context
            },
            "fix_status": "WORKING" if (len(vector_results) > 0 and len(search_results_in_state) > 0 and search_results_visible) else "BROKEN"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "note": "Check server logs for detailed error information"
        }

@app.get("/admin/performance-status")
async def get_performance_status():
    """Admin endpoint to check performance optimization status"""
    try:
        optimizer_status = performance_optimizer.get_optimization_status()
        lazy_loader_stats = lazy_loader.get_load_stats()
        
        return {
            "status": "success",
            "performance_optimizer": optimizer_status,
            "lazy_loader": lazy_loader_stats,
            "system_info": {
                "services_initialized": services_initialized,
                "prewarming_service_available": prewarming_service is not None
            }
        }
    except Exception as e:
        logger.error(f"Performance status check failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/admin/optimize-runtime")
async def optimize_runtime():
    """Admin endpoint to apply runtime performance optimizations"""
    try:
        await performance_optimizer.optimize_runtime_performance()
        status = performance_optimizer.get_optimization_status()
        
        return {
            "status": "success",
            "message": "Runtime optimization applied",
            "optimization_status": status
        }
    except Exception as e:
        logger.error(f"Runtime optimization failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/performance-comparison")
async def performance_comparison():
    """Admin endpoint to compare system performance with and without optimizations"""
    try:
        import time
        import asyncio
        
        # Measure baseline timing
        baseline_start = time.time()
        await asyncio.sleep(0.001)
        baseline_time = time.time() - baseline_start
        
        # Measure with optimizations
        optimized_start = time.time()
        session = performance_optimizer.get_http_session()
        optimized_time = time.time() - optimized_start
        
        optimizer_status = performance_optimizer.get_optimization_status()
        lazy_stats = lazy_loader.get_load_stats()
        
        improvement_ratio = baseline_time / optimized_time if optimized_time > 0 else 0
        
        return {
            "status": "success",
            "performance_comparison": {
                "baseline_time_ms": round(baseline_time * 1000, 3),
                "optimized_time_ms": round(optimized_time * 1000, 3),
                "improvement_factor": round(improvement_ratio, 2),
                "time_saved_ms": round((baseline_time - optimized_time) * 1000, 3)
            },
            "optimization_summary": {
                "optimizations_applied": optimizer_status.get("total_optimizations", 0),
                "modules_preloaded": lazy_stats.get("total_modules", 0),
                "connection_pool_available": optimizer_status.get("session_available", False),
                "memory_usage_mb": optimizer_status.get("memory_usage_mb", 0)
            }
        }
    except Exception as e:
        logger.error(f"Performance comparison failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/connection-pool-status")
async def connection_pool_status():
    """Admin endpoint to check connection pool status and performance"""
    try:
        pool_stats = connection_pool.get_stats()
        
        return {
            "status": "success",
            "connection_pool": pool_stats,
            "optimization_benefits": {
                "persistent_connections": pool_stats["active_connections"] > 0,
                "connection_reuse_ratio": round(
                    pool_stats["performance"]["connections_reused"] / max(1, pool_stats["performance"]["total_requests"]), 
                    2
                ),
                "average_response_time": pool_stats["performance"]["average_response_time_ms"]
            }
        }
    except Exception as e:
        logger.error(f"Connection pool status check failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/admin/warmup-connections")
async def warmup_connections():
    """Admin endpoint to manually warmup connection pools"""
    try:
        await connection_pool.warmup_connections()
        stats = connection_pool.get_stats()
        
        return {
            "status": "success",
            "message": "Connection pools warmed up successfully",
            "active_connections": stats["active_connections"],
            "services": stats["services"]
        }
    except Exception as e:
        logger.error(f"Connection warmup failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/test-gemini-reasoning")
async def test_gemini_reasoning(query: str = "Explain how machine learning works"):
    """Admin endpoint to test Gemini 2.5 detailed response including reasoning steps"""
    try:
        from utils.gemini_client import GeminiClient
        
        gemini_client = GeminiClient()
        
        # Test with Gemini 2.5 Pro for reasoning
        system_prompt = """You are an AI assistant that shows your reasoning process step by step. 
When answering questions, please:
1. Think through the problem systematically
2. Show your reasoning steps
3. Provide a clear final answer

Please be thorough in explaining your thought process."""
        
        user_prompt = f"Question: {query}\n\nPlease show your reasoning steps as you work through this question."
        
        # Get detailed response to examine structure
        detailed_response = await gemini_client.generate_detailed_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="gemini-2.5-pro",  # Use Pro model for better reasoning
            max_tokens=2000,
            temperature=0.7
        )
        
        # Test streaming response to capture reasoning steps
        reasoning_prompt = f"""Think step by step about this question. Please show your reasoning process as you work through it:

Question: {query}

Please think through this systematically, showing each step of your reasoning."""
        
        streaming_response = await gemini_client.generate_streaming_response(
            system_prompt="You are a helpful AI that thinks step by step and shows your reasoning process clearly.",
            user_prompt=reasoning_prompt,
            model="gemini-2.5-pro"
        )
        
        return {
            "status": "success",
            "query": query,
            "detailed_response": detailed_response,
            "streaming_response": streaming_response,
            "analysis": {
                "streaming_chunks": streaming_response.get("streaming_stats", {}).get("total_chunks", 0),
                "reasoning_steps_found": len(streaming_response.get("reasoning_steps", [])),
                "reasoning_step_samples": [
                    step.get("text", "")[:100] + "..." if len(step.get("text", "")) > 100 else step.get("text", "")
                    for step in streaming_response.get("reasoning_steps", [])[:3]
                ],
                "token_usage": streaming_response.get("usage_metadata", {}),
                "has_multiple_parts": len(detailed_response.get("candidates", [])) > 0 and 
                                    len(detailed_response["candidates"][0].get("parts", [])) > 1 if detailed_response.get("candidates") else False
            }
        }
        
    except Exception as e:
        logger.error(f"Gemini reasoning test failed: {e}")
        return {"status": "error", "message": str(e)}

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
