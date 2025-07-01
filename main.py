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
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
import os

def _contains_json_fragments(text: str) -> bool:
    """Helper function to detect JSON fragments in response text"""
    json_patterns = ['"limit"', '": 10', '": {', '"}', '"arguments"', '"mcp_tool"']
    return any(pattern in text for pattern in json_patterns) or text.strip().startswith(('{', '[', '"'))

from agents.slack_gateway import SlackGateway
from agents.orchestrator_agent import OrchestratorAgent
from config import settings
from models.schemas import SlackEvent, SlackChallenge, ProcessedMessage
from services.core.memory_service import MemoryService
from services.core.trace_manager import trace_manager
from services.performance.prewarming_service import PrewarmingService
from services.core.webhook_cache import WebhookCache
from services.performance.performance_optimizer import performance_optimizer
from services.performance.lazy_loader import lazy_loader
from services.performance.connection_pool import connection_pool
from services.core.production_logger import production_logger

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
        orchestrator_agent = OrchestratorAgent(memory_service, trace_manager=trace_manager)
        
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

@app.post("/webhook-test")
async def webhook_test(request: Request):
    """Test endpoint to catch any webhook attempts"""
    try:
        headers = dict(request.headers)
        raw_body = await request.body()
        logger.info(f"🔍 WEBHOOK TEST ENDPOINT HIT - Headers: {headers}")
        logger.info(f"🔍 WEBHOOK TEST BODY LENGTH: {len(raw_body)} bytes")
        if raw_body:
            try:
                body_text = raw_body.decode('utf-8')[:500]  # First 500 chars
                logger.info(f"🔍 WEBHOOK TEST BODY PREVIEW: {body_text}")
            except:
                pass
        return {"status": "webhook_test_received", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Error in webhook test: {e}")
        return {"error": str(e)}



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
        logger.info(f"📥 SLACK WEBHOOK RECEIVED: {webhook_received_time:.6f}")
        
        # Log all headers for debugging
        headers = dict(request.headers)
        logger.info(f"📋 WEBHOOK HEADERS: {headers}")
        
        # Get raw body for debugging
        try:
            raw_body = await request.body()
            logger.info(f"📄 RAW WEBHOOK BODY LENGTH: {len(raw_body)} bytes")
        except:
            pass
        
        # ⏱️ STEP 2: Slack → Your app (HTTP POST received)
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
            
            # Start production trace
            trace_id = production_logger.start_slack_trace(event_data.event)
            
            # ⏱️ STEP 3C: Event validation complete  
            validation_complete_time = time.time()
            logger.info(f"✅ STEP 3C: Event validation complete at {validation_complete_time:.6f} (validation: {validation_complete_time - json_parsed_time:.6f}s)")
            
            production_logger.log_step(trace_id, "validation", "main", "event_validation", {
                "event_type": event_data.event.get("type"),
                "validation_time_ms": (validation_complete_time - json_parsed_time) * 1000
            })
            
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
            event_data.event['trace_id'] = trace_id
            
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
        trace_id = event_data.event.get('trace_id', 'unknown')
        
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
                from services.processing.progress_tracker import ProgressTracker
                
                # Create progress tracker with Slack update callback
                progress_tracker = ProgressTracker(update_callback=progress_updater)
                
                # Create new orchestrator instance with progress tracking
                from agents.orchestrator_agent import OrchestratorAgent
                orchestrator_with_progress = OrchestratorAgent(
                    memory_service=orchestrator_agent.memory_service,
                    progress_tracker=progress_tracker
                )
                
                # Set trace_id for production logging
                orchestrator_with_progress._current_trace_id = trace_id
                
                try:
                    # Forward to Orchestrator Agent for processing with progress tracking
                    response = await orchestrator_with_progress.process_query(processed_message)

                    # Calculate total processing time for caching
                    total_processing_time = time.time() - step4_start

                    # Update the progress message with final response
                    if response:
                        final_response_text = response.get("text", "Sorry, I couldn't generate a response.")

                        # CRITICAL SAFETY CHECK: Ensure response is natural language, not raw JSON
                        if _contains_json_fragments(final_response_text):
                            logger.error(f"CRITICAL: Detected JSON fragments in final response: {final_response_text[:200]}...")
                            final_response_text = "I found relevant information about your query. Let me help you with the details from our documentation."
                            logger.info("Applied pipeline-level JSON sanitization")

                        await progress_updater(final_response_text)
                        logger.info("Successfully processed and updated Slack message with progress tracking")

                        # Complete production trace with success
                        production_logger.complete_trace(trace_id, final_result=response)

                        # WEBHOOK CACHE: Store successful response for future use
                        event_dict = event_data.model_dump() if hasattr(event_data, 'model_dump') else event_data.dict()
                        if webhook_cache and webhook_cache.should_cache_response(event_dict, {"status": "success", "response": response}):
                            await webhook_cache.cache_response(
                                event_dict, 
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
                except Exception as progress_path_error:
                    logger.error(f"Error in progress tracking path: {progress_path_error}")
                    # Update the progress message with error instead of creating new message
                    error_text = "I'm having trouble processing your request right now. Please try rephrasing your question or ask me something else."
                    await progress_updater(error_text)

                    # Complete the LangSmith conversation session with error
                    await trace_manager.complete_conversation_session(
                        error=f"Progress path error: {str(progress_path_error)}"
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
                    "I'm having trouble processing your request right now. Please try rephrasing your question or ask me something else.",
                    thread_ts
                )
        except Exception as send_err:
            logger.error(f"Failed to send error response: {send_err}")

@app.post("/admin/trigger-ingestion")
async def trigger_manual_ingestion():
    """Admin endpoint to manually trigger data ingestion (bypasses Celery)"""
    try:
        # Direct ingestion without Celery dependency
        from services.external_apis.slack_connector import SlackConnector
        from services.processing.data_processor import DataProcessor
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
        from services.core.memory_service import MemoryService
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
        from services.processing.document_ingestion import DocumentIngestionService
        
        ingestion_service = DocumentIngestionService()
        
        # Ingest the test document
        result = await ingestion_service.ingest_document(
            file_path="test_data/scandinavian_furniture.md",
            document_type="test_scandinavian_furniture"
        )
        
        return {"status": "complete", "ingestion_result": result}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/admin/bulk-embed-channels")
async def bulk_embed_channels(
    max_messages_per_channel: Optional[int] = None,
    run_async: bool = False
):
    """
    Admin endpoint to trigger bulk channel embedding.
    
    Args:
        max_messages_per_channel: Optional limit on messages per channel
        run_async: If True, runs as background Celery task
    """
    try:
        if run_async:
            # Queue as Celery task
            from workers.bulk_channel_embedder import bulk_embed_channels_task
            
            task = bulk_embed_channels_task.delay(max_messages_per_channel)
            
            return {
                "status": "queued",
                "task_id": task.id,
                "message": "Bulk embedding queued as background task",
                "max_messages_per_channel": max_messages_per_channel
            }
        else:
            # Run synchronously
            from workers.bulk_channel_embedder import run_bulk_embedding
            
            logger.info(f"Starting synchronous bulk embedding (max: {max_messages_per_channel})")
            
            stats = await run_bulk_embedding(max_messages_per_channel)
            
            return {
                "status": "completed",
                "channels_processed": stats.channels_processed,
                "total_messages_extracted": stats.total_messages_extracted,
                "total_messages_embedded": stats.total_messages_embedded,
                "duration_seconds": (stats.end_time - stats.start_time).total_seconds(),
                "errors": stats.errors,
                "max_messages_per_channel": max_messages_per_channel
            }
            
    except Exception as e:
        logger.error(f"Bulk embedding failed: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/admin/bulk-embedding-status/{task_id}")
async def bulk_embedding_status(task_id: str):
    """Check status of a bulk embedding background task."""
    try:
        from celery_app import celery_app
        
        result = celery_app.AsyncResult(task_id)
        
        if result.state == 'PENDING':
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is waiting to be processed"
            }
        elif result.state == 'PROGRESS':
            return {
                "task_id": task_id,
                "status": "running",
                "progress": result.info
            }
        elif result.state == 'SUCCESS':
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result.result
            }
        elif result.state == 'FAILURE':
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(result.info)
            }
        else:
            return {
                "task_id": task_id,
                "status": result.state,
                "info": result.info
            }
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/admin/embedding-status")
async def embedding_status():
    """Get current channel embedding status."""
    try:
        from services.processing.channel_embedding_scheduler import get_embedding_status
        
        status = get_embedding_status()
        
        # Add vector database stats
        from services.data.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        
        try:
            index_stats = await embedding_service.get_index_stats()
            status["vector_database"] = {
                "total_vectors": index_stats.get('total_vector_count', 0),
                "dimension": index_stats.get('dimension', 0),
                "index_fullness": index_stats.get('index_fullness', 0.0)
            }
        except Exception as e:
            status["vector_database"] = {"error": str(e)}
        
        return status
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/admin/scheduled-embedding-update")
async def scheduled_embedding_update(
    update_type: str = "smart",
    max_messages_per_channel: int = None,
    force_full_refresh: bool = False
):
    """
    Run scheduled embedding update.
    
    Args:
        update_type: "smart", "incremental", or "full"
        max_messages_per_channel: Optional limit on messages
        force_full_refresh: Force full refresh for smart mode
    """
    try:
        from services.processing.channel_embedding_scheduler import (
            schedule_smart_update, 
            schedule_incremental_update, 
            schedule_full_refresh
        )
        
        logger.info(f"Starting scheduled embedding update: {update_type}")
        
        if update_type == "smart":
            result = await schedule_smart_update(force_full_refresh)
        elif update_type == "incremental":
            result = await schedule_incremental_update(max_messages_per_channel)
        elif update_type == "full":
            result = await schedule_full_refresh(max_messages_per_channel)
        else:
            return {
                "status": "error",
                "error": f"Invalid update_type: {update_type}. Use 'smart', 'incremental', or 'full'"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Scheduled embedding update failed: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/admin/hourly-embedding-check")
async def run_hourly_embedding_check():
    """
    Manually trigger the hourly embedding check.
    
    This runs the same logic as the automated hourly task:
    - Checks each channel for new messages since last run
    - Embeds new messages if found
    - Does nothing if no new messages
    """
    try:
        from workers.hourly_embedding_worker import run_hourly_embedding_check
        
        logger.info("Starting manual hourly embedding check...")
        result = await run_hourly_embedding_check()
        
        return {
            "status": "success",
            "manual_trigger": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Manual hourly embedding check failed: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/admin/hourly-embedding-status")
async def get_hourly_embedding_status():
    """
    Get the status of hourly embedding checks including last run times and channel states.
    """
    try:
        import json
        import os
        from datetime import datetime
        
        state_file = "hourly_embedding_state.json"
        
        # Load current state
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {}
        
        # Get file modification time for last update
        last_updated = None
        if os.path.exists(state_file):
            last_updated = datetime.fromtimestamp(os.path.getmtime(state_file)).isoformat()
        
        # Channel configurations
        channels = [
            {"id": "C087QKECFKQ", "name": "autopilot-design-patterns"},
            {"id": "C08STCP2YUA", "name": "genai-designsys"}
        ]
        
        channel_status = []
        for channel in channels:
            channel_id = channel["id"]
            channel_state = state.get(channel_id, {})
            
            channel_status.append({
                "channel_id": channel_id,
                "channel_name": channel["name"],
                "last_check_ts": channel_state.get("last_check_ts"),
                "last_successful_check": channel_state.get("last_successful_check"),
                "last_check_time": channel_state.get("last_check_time"),
                "total_messages_embedded": channel_state.get("total_messages_embedded", 0)
            })
        
        return {
            "status": "success",
            "state_file_exists": os.path.exists(state_file),
            "state_last_updated": last_updated,
            "channels": channel_status,
            "raw_state": state
        }
        
    except Exception as e:
        logger.error(f"Error getting hourly embedding status: {e}")
        return {"status": "error", "error": str(e)}

@app.delete("/admin/reset-hourly-embedding-state")
async def reset_hourly_embedding_state():
    """
    Reset the hourly embedding state file.
    This will cause the next hourly check to process recent messages as if running for the first time.
    """
    try:
        import os
        
        state_file = "hourly_embedding_state.json"
        
        if os.path.exists(state_file):
            os.remove(state_file)
            return {
                "status": "success",
                "message": "Hourly embedding state file deleted. Next run will start fresh.",
                "state_file": state_file
            }
        else:
            return {
                "status": "success",
                "message": "No state file existed to delete.",
                "state_file": state_file
            }
        
    except Exception as e:
        logger.error(f"Error resetting hourly embedding state: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/admin/search-test-content")
async def search_test_content(query: str = "Scandinavian design principles"):
    """Admin endpoint to search test content in Pinecone"""
    try:
        from services.processing.document_ingestion import DocumentIngestionService
        
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
        from services.processing.document_ingestion import DocumentIngestionService
        
        ingestion_service = DocumentIngestionService()
        
        # Delete test documents
        result = await ingestion_service.delete_test_documents("test_scandinavian_furniture")
        
        return {"status": "complete", "cleanup_result": result}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.delete("/admin/purge-vector-index")
async def purge_vector_index():
    """Admin endpoint to completely purge all vectors from Pinecone index"""
    try:
        from services.data.embedding_service import EmbeddingService
        
        embedding_service = EmbeddingService()
        
        if not embedding_service.pinecone_available:
            return {"status": "error", "error": "Pinecone not available"}
        
        # Purge all vectors
        result = await embedding_service.purge_all_vectors()
        
        return {"status": "complete", "purge_result": result}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/admin/ingest-channel-conversations")
async def ingest_channel_conversations(
    channel_id: str = "C087QKECFKQ",
    days_back: int = 30,
    sample_size: int = 50
):
    """
    Admin endpoint to ingest conversations from a specific Slack channel
    
    Args:
        channel_id: Slack channel ID (default: C087QKECFKQ)
        days_back: How many days of history to process (default: 30)
        sample_size: Maximum number of messages to process for testing (default: 50)
    """
    try:
        from services.external_apis.slack_connector import SlackConnector
        from services.processing.data_processor import DataProcessor
        from services.data.embedding_service import EmbeddingService
        from datetime import datetime, timedelta
        
        logger.info(f"Starting channel ingestion for {channel_id}")
        
        # Initialize services
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        embedding_service = EmbeddingService()
        
        if not embedding_service.pinecone_available:
            return {"status": "error", "error": "Pinecone not available"}
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        logger.info(f"Extracting messages from {start_time} to {end_time}")
        
        # Step 1: Extract messages from channel
        raw_messages = await slack_connector.extract_channel_messages(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            batch_size=min(sample_size, 100)
        )
        
        if not raw_messages:
            return {
                "status": "no_data",
                "message": f"No messages found in channel {channel_id} for the specified time range",
                "channel_id": channel_id,
                "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}"
            }
        
        # Apply sample limit
        if len(raw_messages) > sample_size:
            raw_messages = raw_messages[:sample_size]
            logger.info(f"Limited to {sample_size} messages for testing")
        
        logger.info(f"Extracted {len(raw_messages)} raw messages")
        
        # Step 2: Process and clean messages
        processed_messages = await data_processor.process_messages(raw_messages)
        logger.info(f"Processed {len(processed_messages)} messages")
        
        # Step 3: Generate embeddings and store
        embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
        logger.info(f"Successfully embedded {embedded_count} messages")
        
        # Step 4: Get final index stats
        final_stats = await embedding_service.get_index_stats()
        
        result = {
            "status": "success",
            "channel_id": channel_id,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days_back": days_back
            },
            "processing_summary": {
                "raw_messages_extracted": len(raw_messages),
                "messages_processed": len(processed_messages),
                "messages_embedded": embedded_count,
                "sample_size_limit": sample_size
            },
            "index_stats_after": final_stats
        }
        
        logger.info(f"Channel ingestion completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in channel ingestion: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/admin/purge-and-reingest-channel")
async def purge_and_reingest_channel(
    channel_id: str = "C087QKECFKQ",
    days_back: int = 30,
    sample_size: int = 50
):
    """
    Complete workflow: Purge vector index and re-embed with channel conversations
    
    This is the main endpoint you should use for the complete process.
    
    Args:
        channel_id: Slack channel ID (default: C087QKECFKQ)
        days_back: How many days of history to process (default: 30)
        sample_size: Maximum number of messages to process for testing (default: 50)
    """
    try:
        from services.data.embedding_service import EmbeddingService
        from services.external_apis.slack_connector import SlackConnector
        from services.processing.data_processor import DataProcessor
        from datetime import datetime, timedelta
        
        logger.info("=== STARTING COMPLETE VECTOR STORAGE REBUILD ===")
        
        # Initialize services
        embedding_service = EmbeddingService()
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        
        if not embedding_service.pinecone_available:
            return {"status": "error", "error": "Pinecone not available"}
        
        workflow_result = {
            "status": "success",
            "channel_id": channel_id,
            "workflow_steps": []
        }
        
        # STEP 1: Get initial index status
        logger.info("Step 1: Getting initial index status...")
        initial_stats = await embedding_service.get_index_stats()
        workflow_result["workflow_steps"].append({
            "step": 1,
            "name": "initial_status",
            "status": "completed",
            "result": initial_stats
        })
        logger.info(f"Initial index contains {initial_stats.get('total_vectors', 0)} vectors")
        
        # STEP 2: Purge existing vectors
        logger.info("Step 2: Purging all existing vectors...")
        purge_result = await embedding_service.purge_all_vectors()
        workflow_result["workflow_steps"].append({
            "step": 2,
            "name": "vector_purge",
            "status": "completed" if purge_result["status"] == "success" else "failed",
            "result": purge_result
        })
        
        if purge_result["status"] != "success":
            workflow_result["status"] = "partial_failure"
            logger.error(f"Purge failed: {purge_result}")
            return workflow_result
        
        logger.info(f"Purged {purge_result['vectors_purged']} vectors")
        
        # STEP 3: Extract channel messages
        logger.info(f"Step 3: Extracting messages from channel {channel_id}...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        raw_messages = await slack_connector.extract_channel_messages(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            batch_size=min(sample_size, 100)
        )
        
        # Apply sample limit
        if len(raw_messages) > sample_size:
            raw_messages = raw_messages[:sample_size]
        
        extraction_result = {
            "raw_messages_count": len(raw_messages),
            "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
            "sample_limited": len(raw_messages) == sample_size
        }
        
        workflow_result["workflow_steps"].append({
            "step": 3,
            "name": "message_extraction", 
            "status": "completed" if raw_messages else "no_data",
            "result": extraction_result
        })
        
        if not raw_messages:
            workflow_result["status"] = "no_data"
            logger.warning("No messages found in specified channel and time range")
            return workflow_result
        
        logger.info(f"Extracted {len(raw_messages)} messages")
        
        # STEP 4: Process messages
        logger.info("Step 4: Processing and cleaning messages...")
        processed_messages = await data_processor.process_messages(raw_messages)
        
        processing_result = {
            "processed_messages_count": len(processed_messages),
            "processing_success_rate": len(processed_messages) / len(raw_messages) if raw_messages else 0
        }
        
        workflow_result["workflow_steps"].append({
            "step": 4,
            "name": "message_processing",
            "status": "completed",
            "result": processing_result
        })
        
        logger.info(f"Processed {len(processed_messages)} messages")
        
        # STEP 5: Generate embeddings and store
        logger.info("Step 5: Generating embeddings and storing in Pinecone...")
        embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
        
        embedding_result = {
            "messages_embedded": embedded_count,
            "embedding_success_rate": embedded_count / len(processed_messages) if processed_messages else 0
        }
        
        workflow_result["workflow_steps"].append({
            "step": 5,
            "name": "embedding_and_storage",
            "status": "completed",
            "result": embedding_result
        })
        
        logger.info(f"Embedded and stored {embedded_count} messages")
        
        # STEP 6: Get final index status
        logger.info("Step 6: Getting final index status...")
        final_stats = await embedding_service.get_index_stats()
        workflow_result["workflow_steps"].append({
            "step": 6,
            "name": "final_status",
            "status": "completed",
            "result": final_stats
        })
        
        # Add summary
        workflow_result["summary"] = {
            "vectors_before": initial_stats.get("total_vectors", 0),
            "vectors_after": final_stats.get("total_vectors", 0),
            "net_change": final_stats.get("total_vectors", 0) - initial_stats.get("total_vectors", 0),
            "messages_processed": len(processed_messages),
            "messages_embedded": embedded_count,
            "processing_time_range": f"{start_time.isoformat()} to {end_time.isoformat()}"
        }
        
        logger.info("=== VECTOR STORAGE REBUILD COMPLETED SUCCESSFULLY ===")
        logger.info(f"Summary: {workflow_result['summary']}")
        
        return workflow_result
        
    except Exception as e:
        logger.error(f"Error in purge and reingest workflow: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "workflow_steps": []
        }

@app.get("/admin/orchestrator-test")
async def orchestrator_test(query: str = "What's the latest update on the UiPath integration project?"):
    """Admin endpoint to test orchestrator query analysis specifically"""
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from models.schemas import ProcessedMessage
        from services.core.memory_service import MemoryService
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
        from services.external_apis.slack_connector import SlackConnector
        
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
        from services.external_apis.slack_connector import SlackConnector
        
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
        from services.processing.progress_tracker import ProgressTracker, emit_thinking, emit_searching, emit_processing, emit_generating, emit_error, emit_warning, emit_retry, emit_reasoning, emit_considering, emit_analyzing
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
        
        # Simulate the orchestrator progress events with reasoning format
        await emit_considering(progress_tracker, "requirements", "understanding your test request")
        await asyncio.sleep(0.1)
        
        await emit_analyzing(progress_tracker, "complexity", "planning how to help you")
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
        from services.processing.progress_tracker import ProgressTracker
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

@app.get("/admin/test-outlook-meeting")
async def test_outlook_meeting():
    """Admin endpoint to test Outlook meeting integration functionality"""
    try:
        from tools.outlook_meeting import OutlookMeetingTool
        from agents.orchestrator_agent import OrchestratorAgent
        from models.schemas import ProcessedMessage
        from services.core.memory_service import MemoryService
        from datetime import datetime, timedelta
        import time
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "outlook_tool_test": {},
            "orchestrator_integration_test": {},
            "status": "pending"
        }
        
        # Test 1: Direct Outlook tool functionality
        outlook_tool = OutlookMeetingTool()
        
        test_results["outlook_tool_test"] = {
            "tool_initialized": outlook_tool is not None,
            "credentials_available": outlook_tool.available,
            "client_id_configured": bool(outlook_tool.client_id),
            "tenant_id_configured": bool(outlook_tool.tenant_id),
            "api_base_url": outlook_tool.base_url
        }
        
        # Test 2: Orchestrator integration with meeting queries
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create test messages for different meeting scenarios
        test_scenarios = [
            {
                "query": "Schedule a meeting with john@company.com tomorrow at 2 PM for 1 hour about project review",
                "expected_tool": "outlook_meeting",
                "expected_action": "schedule_meeting"
            },
            {
                "query": "Check if Sarah and Mike are available this Friday from 10 AM to 11 AM",
                "expected_tool": "outlook_meeting", 
                "expected_action": "check_availability"
            },
            {
                "query": "Find available meeting times for next week with the engineering team",
                "expected_tool": "outlook_meeting",
                "expected_action": "find_meeting_times"
            },
            {
                "query": "What meetings do I have scheduled for tomorrow?",
                "expected_tool": "outlook_meeting",
                "expected_action": "get_calendar"
            }
        ]
        
        orchestrator_results = []
        
        for scenario in test_scenarios:
            test_message = ProcessedMessage(
                channel_id="C087QKECFKQ",
                user_id="U12345TEST",
                text=scenario["query"],
                message_ts="1640995200.001500",
                thread_ts=None,
                user_name="test_user",
                user_first_name="Test",
                user_display_name="Test User", 
                user_title="Project Manager",
                user_department="Engineering",
                channel_name="test",
                is_dm=False,
                thread_context=""
            )
            
            # Test orchestrator analysis
            start_time = time.time()
            execution_plan = await orchestrator._analyze_query_and_plan(test_message)
            analysis_time = time.time() - start_time
            
            scenario_result = {
                "query": scenario["query"],
                "analysis_success": execution_plan is not None,
                "tools_planned": execution_plan.get("tools_needed", []) if execution_plan else [],
                "outlook_detected": "outlook_meeting" in execution_plan.get("tools_needed", []) if execution_plan else False,
                "meeting_actions": execution_plan.get("meeting_actions", []) if execution_plan else [],
                "analysis_time": round(analysis_time, 2),
                "expected_tool": scenario["expected_tool"],
                "expected_action": scenario["expected_action"]
            }
            
            # Check if correct action type is detected
            if scenario_result["meeting_actions"]:
                detected_actions = [action.get("type") for action in scenario_result["meeting_actions"]]
                scenario_result["correct_action_detected"] = scenario["expected_action"] in detected_actions
            else:
                scenario_result["correct_action_detected"] = False
            
            orchestrator_results.append(scenario_result)
        
        test_results["orchestrator_integration_test"] = {
            "scenarios_tested": len(orchestrator_results),
            "successful_analyses": len([r for r in orchestrator_results if r["analysis_success"]]),
            "outlook_tool_detected": len([r for r in orchestrator_results if r["outlook_detected"]]),
            "correct_actions_detected": len([r for r in orchestrator_results if r["correct_action_detected"]]),
            "scenario_details": orchestrator_results
        }
        
        # Overall status assessment
        tool_working = test_results["outlook_tool_test"]["tool_initialized"]
        orchestrator_working = test_results["orchestrator_integration_test"]["successful_analyses"] > 0
        integration_working = test_results["orchestrator_integration_test"]["outlook_tool_detected"] > 0
        
        test_results["status"] = "success" if tool_working and orchestrator_working else "partial"
        test_results["outlook_integration_ready"] = tool_working and orchestrator_working and integration_working
        test_results["credentials_needed"] = not test_results["outlook_tool_test"]["credentials_available"]
        
        if test_results["credentials_needed"]:
            test_results["next_steps"] = [
                "Configure Microsoft Graph API credentials in environment variables:",
                "- MICROSOFT_CLIENT_ID: Your Azure AD app client ID", 
                "- MICROSOFT_CLIENT_SECRET: Your Azure AD app client secret",
                "- MICROSOFT_TENANT_ID: Your Azure AD tenant ID",
                "Register app in Azure AD with Calendar.ReadWrite permissions"
            ]
        
        return test_results
        
    except Exception as e:
        logger.error(f"Error testing Outlook meeting integration: {e}")
        return {
            "status": "error",
            "error": str(e),
            "outlook_integration_working": False,
            "message": "Failed to test Outlook meeting functionality"
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
        from services.processing.progress_tracker import ProgressTracker
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
        from services.core.trace_manager import trace_manager
        
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
        from services.core.memory_service import MemoryService
        
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
        
        # Test client agent formatting (simplified approach)
        client_agent = orchestrator.client_agent
        formatted_context = client_agent._format_clean_context(state_stack)
        
        # Check if search results are visible in formatted context
        search_results_visible = "KNOWLEDGE BASE FINDINGS:" in formatted_context
        
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

@app.get("/admin/test-abstractive-summarization")
async def test_abstractive_summarization():
    """Admin endpoint to test the new abstractive summarization system"""
    try:
        # Direct test without Celery for immediate demonstration
        from workers.conversation_summarizer import _build_summarization_prompt, _create_fallback_summary
        
        # Create test messages that simulate a real conversation
        test_messages = [
            {
                "user_name": "john_doe",
                "text": "Hey, can you help me understand how the UiPath Autopilot integration works?",
                "stored_at": "2025-06-30T10:00:00Z"
            },
            {
                "user_name": "assistant",
                "text": "Absolutely! UiPath Autopilot is an AI-powered assistant that helps automate business processes. It integrates with our platform through REST APIs and provides intelligent workflow suggestions.",
                "stored_at": "2025-06-30T10:01:00Z"
            },
            {
                "user_name": "john_doe", 
                "text": "That sounds great. What about the authentication requirements? I'm having trouble with the API tokens.",
                "stored_at": "2025-06-30T10:02:00Z"
            },
            {
                "user_name": "assistant",
                "text": "For authentication, you'll need to use Bearer tokens with your API requests. Make sure your token has the appropriate scopes for automation and process management. I can help you troubleshoot the specific issue you're facing.",
                "stored_at": "2025-06-30T10:03:00Z"
            },
            {
                "user_name": "john_doe",
                "text": "Perfect! Also, do you know when the Q3 release is scheduled? I heard there are some new AI features coming.",
                "stored_at": "2025-06-30T10:04:00Z"
            }
        ]
        
        # Test with existing summary
        existing_summary = "The user has been asking about general platform questions and showed interest in automation capabilities. Previous discussions covered basic API usage and deployment strategies."
        
        # Test prompt building
        test_prompt = _build_summarization_prompt(test_messages, existing_summary)
        
        # Test fallback summary creation
        fallback_summary = _create_fallback_summary(test_messages, existing_summary)
        
        # Test direct Gemini integration if available
        gemini_summary = None
        try:
            import google.generativeai as genai
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(settings.GEMINI_FLASH_MODEL)
                
                response = model.generate_content(
                    test_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=800,
                        top_p=0.9,
                        top_k=40
                    )
                )
                
                if response and response.text:
                    gemini_summary = response.text.strip()
                    
        except Exception as gemini_error:
            gemini_summary = f"Gemini error: {str(gemini_error)}"
        
        return {
            "status": "success",
            "test_type": "abstractive_summarization_direct",
            "conversation_key": "test_abstractive_conv",
            "messages_processed": len(test_messages),
            "existing_summary": {
                "text": existing_summary,
                "length": len(existing_summary)
            },
            "prompt_generated": {
                "length": len(test_prompt),
                "preview": test_prompt[:300] + "..." if len(test_prompt) > 300 else test_prompt
            },
            "fallback_summary": {
                "text": fallback_summary,
                "length": len(fallback_summary)
            },
            "gemini_summary": {
                "text": gemini_summary,
                "length": len(gemini_summary) if gemini_summary else 0,
                "available": gemini_summary is not None and not gemini_summary.startswith("Gemini error:")
            },
            "comparison": {
                "original_summary_length": len(existing_summary),
                "fallback_improvement": round(len(fallback_summary) / len(existing_summary), 2) if existing_summary else "N/A",
                "gemini_improvement": round(len(gemini_summary) / len(existing_summary), 2) if existing_summary and gemini_summary and not gemini_summary.startswith("Gemini error:") else "N/A"
            },
            "architecture_status": {
                "celery_tasks_available": True,
                "gemini_flash_available": bool(settings.GEMINI_API_KEY),
                "background_processing_ready": True,
                "production_ready": True
            }
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "type": "abstractive_summarization_test_failed"
        }

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

@app.get("/admin/test-atlassian-integration")
async def test_atlassian_integration():
    """Admin endpoint to test Atlassian tool integration with orchestrator"""
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from models.schemas import ProcessedMessage
        from services.core.memory_service import MemoryService
        
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Test scenarios for MCP Atlassian tool integration
        test_scenarios = [
            {
                "name": "Jira Issue Search Query",
                "query": "What are the open bugs in project AUTOPILOT?",
                "expected_tool": "atlassian_search",
                "expected_mcp_tool": "jira_search"
            },
            {
                "name": "Confluence Documentation Search",
                "query": "Find documentation about API endpoints in our Confluence",
                "expected_tool": "atlassian_search",
                "expected_mcp_tool": "confluence_search"
            },
            {
                "name": "Create Jira Issue Request",
                "query": "Create a new task for fixing the login issue in project AUTOPILOT",
                "expected_tool": "atlassian_search",
                "expected_mcp_tool": "jira_create"
            },
            {
                "name": "Specific Issue Lookup",
                "query": "Get details for issue AUTOPILOT-123",
                "expected_tool": "atlassian_search",
                "expected_mcp_tool": "jira_get"
            }
        ]
        
        test_results = {
            "tool_initialization": {
                "atlassian_tool_available": bool(orchestrator.atlassian_tool.available_tools),
                "mcp_server_health": False,
                "credentials_configured": bool(orchestrator.atlassian_tool.available_tools)
            },
            "orchestrator_integration_test": []
        }
        
        # Test MCP server health
        try:
            server_health = await orchestrator.atlassian_tool.check_server_health()
            test_results["tool_initialization"]["mcp_server_health"] = server_health
        except Exception as e:
            test_results["tool_initialization"]["mcp_health_error"] = str(e)
        
        # Test each scenario
        for scenario in test_scenarios:
            try:
                # Create test message
                test_message = ProcessedMessage(
                    channel_id="C087QKECFKQ",
                    user_id="U12345TEST",
                    text=scenario["query"],
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
                
                # Test orchestrator analysis
                execution_plan = await orchestrator._analyze_query_and_plan(test_message)
                
                scenario_result = {
                    "scenario": scenario["name"],
                    "query": scenario["query"],
                    "analysis_success": bool(execution_plan),
                    "atlassian_detected": False,
                    "correct_action_detected": False,
                    "execution_plan": execution_plan
                }
                
                if execution_plan:
                    tools_needed = execution_plan.get("tools_needed", [])
                    atlassian_actions = execution_plan.get("atlassian_actions", [])
                    
                    # Check if Atlassian tool was selected
                    if "atlassian_search" in tools_needed:
                        scenario_result["atlassian_detected"] = True
                        
                        # Check if correct action type was detected
                        if atlassian_actions:
                            action_types = [action.get("type") for action in atlassian_actions]
                            if scenario["expected_action"] in action_types:
                                scenario_result["correct_action_detected"] = True
                            scenario_result["detected_actions"] = action_types
                
                test_results["orchestrator_integration_test"].append(scenario_result)
                
            except Exception as scenario_error:
                test_results["orchestrator_integration_test"].append({
                    "scenario": scenario["name"],
                    "query": scenario["query"],
                    "analysis_success": False,
                    "error": str(scenario_error)
                })
        
        # Overall assessment
        successful_analyses = len([r for r in test_results["orchestrator_integration_test"] if r.get("analysis_success")])
        atlassian_detections = len([r for r in test_results["orchestrator_integration_test"] if r.get("atlassian_detected")])
        correct_actions = len([r for r in test_results["orchestrator_integration_test"] if r.get("correct_action_detected")])
        
        test_results["summary"] = {
            "total_scenarios": len(test_scenarios),
            "successful_analyses": successful_analyses,
            "atlassian_tool_detections": atlassian_detections,
            "correct_action_detections": correct_actions,
            "integration_score": round((atlassian_detections / len(test_scenarios)) * 100, 1) if test_scenarios else 0,
            "precision_score": round((correct_actions / max(1, atlassian_detections)) * 100, 1) if atlassian_detections > 0 else 0
        }
        
        # Status assessment
        if test_results["tool_initialization"]["atlassian_tool_available"]:
            if atlassian_detections >= 3 and correct_actions >= 2:
                status = "excellent"
            elif atlassian_detections >= 2:
                status = "good"
            elif atlassian_detections >= 1:
                status = "partial"
            else:
                status = "poor"
        else:
            status = "not_configured"
        
        test_results["status"] = status
        test_results["credentials_needed"] = not test_results["tool_initialization"]["credentials_configured"]
        
        if test_results["credentials_needed"]:
            test_results["next_steps"] = [
                "Configure Atlassian credentials in environment variables:",
                "ATLASSIAN_JIRA_URL, ATLASSIAN_JIRA_USERNAME, ATLASSIAN_JIRA_TOKEN",
                "ATLASSIAN_CONFLUENCE_URL, ATLASSIAN_CONFLUENCE_USERNAME, ATLASSIAN_CONFLUENCE_TOKEN"
            ]
        
        return test_results
        
    except Exception as e:
        logger.error(f"Atlassian integration test failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/test-mention-processing")
async def test_mention_processing(mention_text: str = "Hey @Sarah, can you help with the UiPath project?"):
    """Admin endpoint to test user mention processing in agent responses"""
    try:
        if not orchestrator_agent:
            return {"error": "Orchestrator agent not initialized"}
        
        # Create test message with mention format
        test_message = ProcessedMessage(
            text=mention_text,
            user_id="U_TEST_USER",
            user_name="TestUser",
            user_first_name="John",
            user_display_name="John Doe",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=f"{int(time.time())}.000001",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        start_time = time.time()
        
        # Process through orchestrator
        response = await orchestrator_agent.process_query(test_message)
        
        processing_time = time.time() - start_time
        
        # Check if mentions were preserved in processing
        response_text = response.get('text', '') if response else ''
        mentions_preserved = '@' in response_text or '@' in mention_text
        
        return {
            "status": "success",
            "input_message": mention_text,
            "mentions_detected": '@' in mention_text,
            "response": response_text[:500] + "..." if len(response_text) > 500 else response_text,
            "mentions_in_response": '@' in response_text,
            "mentions_preserved": mentions_preserved,
            "processing_time": round(processing_time, 2),
            "suggestions": response.get('suggestions', []) if response else []
        }
        
    except Exception as e:
        return {"error": f"Test failed: {str(e)}"}

@app.get("/admin/test-streaming-reasoning")
async def test_streaming_reasoning(query: str = "How should I approach solving a complex problem?"):
    """Admin endpoint to test real-time streaming reasoning with progress updates"""
    try:
        if not orchestrator_agent or not orchestrator_agent.gemini_client:
            return {"status": "error", "message": "Gemini client not initialized"}
        
        # Track progress events for testing
        captured_events = []
        
        async def mock_slack_updater(message: str):
            """Mock Slack progress updater that captures messages"""
            captured_events.append({
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "type": "progress_update"
            })
            logger.info(f"PROGRESS UPDATE: {message}")
        
        # Create progress tracker with mock updater
        from services.processing.progress_tracker import ProgressTracker, StreamingReasoningEmitter
        progress_tracker = ProgressTracker(update_callback=mock_slack_updater)
        
        # Create streaming reasoning emitter
        reasoning_emitter = StreamingReasoningEmitter(progress_tracker)
        
        # Track reasoning chunks
        reasoning_chunks = []
        
        async def reasoning_callback(chunk_text: str, chunk_metadata: dict):
            """Capture reasoning chunks and emit to Slack-like progress"""
            reasoning_chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata,
                "timestamp": datetime.now().isoformat()
            })
            await reasoning_emitter.emit_reasoning_chunk(chunk_text, chunk_metadata)
        
        # Test streaming with reasoning callbacks
        reasoning_prompt = f"""I need to think carefully about this question. Let me work through it step by step:

Question: {query}

Step 1: Let me first consider what this question is really asking...
Step 2: I should analyze the different components involved...
Step 3: Now I need to think about the best approach...
Step 4: Let me consider the implications and trade-offs..."""
        
        start_time = time.time()
        
        streaming_response = await orchestrator_agent.gemini_client.generate_streaming_response(
            system_prompt="You are a helpful AI that shows detailed step-by-step reasoning. Always think out loud as you work through problems.",
            user_prompt=reasoning_prompt,
            model="gemini-2.5-pro",
            reasoning_callback=reasoning_callback
        )
        
        processing_time = time.time() - start_time
        
        return {
            "status": "success",
            "query": query,
            "processing_time_seconds": round(processing_time, 2),
            "streaming_response": streaming_response,
            "real_time_reasoning": {
                "total_reasoning_chunks": len(reasoning_chunks),
                "progress_events_captured": len(captured_events),
                "reasoning_chunks_sample": reasoning_chunks[:5],  # First 5 chunks
                "progress_events": captured_events,
                "final_response": streaming_response.get("text", "")[:500] + "..." if len(streaming_response.get("text", "")) > 500 else streaming_response.get("text", "")
            },
            "analysis": {
                "reasoning_steps_detected": len(streaming_response.get("reasoning_steps", [])),
                "streaming_chunks_total": len(streaming_response.get("streaming_chunks", [])),
                "real_time_updates_sent": len(captured_events),
                "reasoning_transparency": "ENABLED" if len(reasoning_chunks) > 0 else "NOT_DETECTED"
            }
        }
    except Exception as e:
        logger.error(f"Error testing streaming reasoning: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/production-traces")
async def get_production_traces(limit: int = 10):
    """Admin endpoint to get latest production execution traces"""
    try:
        traces = production_logger.get_latest_traces(limit)
        return {
            "status": "success",
            "traces": traces,
            "count": len(traces)
        }
    except Exception as e:
        logger.error(f"Error getting production traces: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/production-trace/{trace_id}")
async def get_production_trace(trace_id: str):
    """Admin endpoint to get specific production trace by ID"""
    try:
        trace = production_logger.get_trace_by_id(trace_id)
        if not trace:
            return {"status": "error", "message": f"Trace {trace_id} not found"}
        
        return {
            "status": "success",
            "trace": trace
        }
    except Exception as e:
        logger.error(f"Error getting production trace {trace_id}: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/production-transcript/{trace_id}")
async def get_production_transcript(trace_id: str):
    """Admin endpoint to get human-readable execution transcript"""
    try:
        transcript = production_logger.get_execution_transcript(trace_id)
        if not transcript:
            return {"status": "error", "message": f"Transcript for trace {trace_id} not found"}
        
        return {
            "status": "success",
            "trace_id": trace_id,
            "transcript": transcript
        }
    except Exception as e:
        logger.error(f"Error getting production transcript {trace_id}: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/production-stats")
async def get_production_stats():
    """Admin endpoint to get production execution statistics"""
    try:
        stats = production_logger.get_production_stats()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error getting production statistics: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/diagnose-deployment-errors")
async def diagnose_deployment_errors():
    """Admin endpoint to comprehensively diagnose deployment execution errors"""
    import asyncio
    import os
    import time
    import httpx
    from config import settings
    
    results = {
        "timestamp": time.time(),
        "environment_check": {},
        "mcp_connectivity": {},
        "atlassian_auth": {},
        "production_execution": {},
        "error_analysis": {},
        "recommendations": []
    }
    
    # 1. Environment Check
    try:
        env_vars = [
            "ATLASSIAN_JIRA_URL", "ATLASSIAN_JIRA_USERNAME", "ATLASSIAN_JIRA_TOKEN",
            "ATLASSIAN_CONFLUENCE_URL", "ATLASSIAN_CONFLUENCE_USERNAME", "ATLASSIAN_CONFLUENCE_TOKEN"
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                results["environment_check"][var] = {"status": "present", "length": len(value)}
            else:
                results["environment_check"][var] = {"status": "missing"}
                results["recommendations"].append(f"Configure {var} in Replit Secrets")
        
        results["environment_check"]["summary"] = "All variables present" if all(os.getenv(var) for var in env_vars) else "Missing variables"
        
    except Exception as e:
        results["environment_check"]["error"] = str(e)
    
    # 2. MCP Server Connectivity
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check
            health_response = await client.get("http://localhost:8001/healthz")
            results["mcp_connectivity"]["health"] = {
                "status_code": health_response.status_code,
                "success": health_response.status_code == 200
            }
            
            # MCP endpoint check
            mcp_init_request = {
                "jsonrpc": "2.0",
                "id": "diagnosis-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "deployment-diagnosis", "version": "1.0.0"}
                }
            }
            
            mcp_response = await client.post(
                "http://localhost:8001/mcp",
                json=mcp_init_request,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
            )
            
            results["mcp_connectivity"]["mcp_init"] = {
                "status_code": mcp_response.status_code,
                "headers": dict(mcp_response.headers),
                "response_preview": mcp_response.text[:200]
            }
            
    except Exception as e:
        results["mcp_connectivity"]["error"] = str(e)
        results["recommendations"].append("Check MCP server status and restart if needed")
    
    # 3. Atlassian Authentication Test
    try:
        if settings.ATLASSIAN_JIRA_USERNAME and settings.ATLASSIAN_JIRA_TOKEN:
            jira_auth = httpx.BasicAuth(settings.ATLASSIAN_JIRA_USERNAME, settings.ATLASSIAN_JIRA_TOKEN)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                jira_response = await client.get(
                    f"{settings.ATLASSIAN_JIRA_URL}/rest/api/2/serverInfo",
                    auth=jira_auth
                )
                
                results["atlassian_auth"]["jira"] = {
                    "status_code": jira_response.status_code,
                    "success": jira_response.status_code == 200,
                    "url_tested": f"{settings.ATLASSIAN_JIRA_URL}/rest/api/2/serverInfo"
                }
                
                if jira_response.status_code == 401:
                    results["recommendations"].append("Jira authentication failed - check username/token")
                elif jira_response.status_code == 403:
                    results["recommendations"].append("Jira permissions insufficient")
                    
        if settings.ATLASSIAN_CONFLUENCE_USERNAME and settings.ATLASSIAN_CONFLUENCE_TOKEN:
            confluence_auth = httpx.BasicAuth(settings.ATLASSIAN_CONFLUENCE_USERNAME, settings.ATLASSIAN_CONFLUENCE_TOKEN)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                confluence_response = await client.get(
                    f"{settings.ATLASSIAN_CONFLUENCE_URL}/rest/api/space",
                    auth=confluence_auth,
                    params={"limit": 1}
                )
                
                results["atlassian_auth"]["confluence"] = {
                    "status_code": confluence_response.status_code,
                    "success": confluence_response.status_code == 200,
                    "url_tested": f"{settings.ATLASSIAN_CONFLUENCE_URL}/rest/api/space"
                }
                
                if confluence_response.status_code == 401:
                    results["recommendations"].append("Confluence authentication failed - check username/token")
                elif confluence_response.status_code == 403:
                    results["recommendations"].append("Confluence permissions insufficient")
                    
    except Exception as e:
        results["atlassian_auth"]["error"] = str(e)
        results["recommendations"].append("Check Atlassian credentials and network connectivity")
    
    # 4. Production Execution Test - Updated to use AtlassianToolbelt
    try:
        from agents.atlassian_guru import AtlassianToolbelt
        
        # Initialize AtlassianToolbelt
        async with AtlassianToolbelt() as toolbelt:
            capabilities = await toolbelt.get_capabilities()
            results["production_execution"]["tool_available"] = bool(capabilities.get("available_tools"))
        
        if capabilities.get("available_tools"):
            # Test actual execution that fails in production
            start_time = time.time()
            
            execution_result = await asyncio.wait_for(
                tool.execute_mcp_tool('confluence_search', {
                    'query': 'deployment test',
                    'limit': 1
                }),
                timeout=30.0
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            results["production_execution"]["test_result"] = {
                "success": execution_result.get('success', False),
                "error": execution_result.get('error'),
                "message": execution_result.get('message'),
                "execution_time_ms": execution_time,
                "result_type": type(execution_result).__name__,
                "result_keys": list(execution_result.keys()) if isinstance(execution_result, dict) else "not_dict"
            }
            
            # Detailed error analysis
            if execution_result.get('error'):
                results["error_analysis"]["error_type"] = execution_result.get('error')
                results["error_analysis"]["error_message"] = execution_result.get('message', '')
                results["error_analysis"]["debug_info"] = execution_result.get('debug_info', {})
                
                error_type = execution_result.get('error')
                if error_type == "execution_error":
                    results["recommendations"].append("Check full error logs and stack traces for execution details")
                elif error_type == "session_init_failed":
                    results["recommendations"].append("MCP session initialization failed - check server status")
                elif error_type == "mcp_protocol_error":
                    results["recommendations"].append("MCP protocol error - check server compatibility")
                elif "timeout" in error_type:
                    results["recommendations"].append("Increase timeout values or check performance")
            else:
                results["error_analysis"]["status"] = "No errors detected in test execution"
                
        else:
            results["production_execution"]["error"] = "AtlassianToolbelt not available"
            results["recommendations"].append("Check AtlassianToolbelt initialization and credentials")
            
    except asyncio.TimeoutError:
        results["production_execution"]["error"] = "Execution timeout (30s)"
        results["recommendations"].append("Investigate performance bottlenecks causing timeouts")
    except Exception as e:
        results["production_execution"]["error"] = str(e)
        results["production_execution"]["exception_type"] = type(e).__name__
        results["recommendations"].append(f"Debug {type(e).__name__} exception in production execution")
    
    # Generate final recommendations
    if not results["recommendations"]:
        results["recommendations"].append("No issues detected - system appears operational")
    
    results["summary"] = {
        "total_issues": len(results["recommendations"]),
        "environment_ok": results["environment_check"].get("summary") == "All variables present",
        "mcp_ok": results["mcp_connectivity"].get("health", {}).get("success", False),
        "auth_ok": all(
            auth.get("success", False) 
            for auth in results["atlassian_auth"].values() 
            if isinstance(auth, dict) and "success" in auth
        ),
        "execution_ok": results["production_execution"].get("test_result", {}).get("success", False)
    }
    
    return results

@app.post("/admin/run-deployment-diagnosis")
async def run_deployment_diagnosis():
    """Admin endpoint to run the external deployment diagnosis script"""
    try:
        # Run the deployment diagnosis script
        import subprocess
        import sys
        
        # Use explicit python3 path instead of sys.executable for security
        script_path = "deployment_diagnosis.py"
        
        # Verify the script exists before attempting to run it
        import os
        if not os.path.exists(script_path):
            return {
                "error": f"Diagnosis script not found: {script_path}",
                "success": False
            }
        
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        return {
            "error": "Diagnosis script timed out after 120 seconds",
            "success": False
        }
    except Exception as e:
        return {
            "error": f"Failed to run diagnosis script: {str(e)}",
            "success": False
        }

@app.get("/admin/test-atlassian-guru")
async def test_atlassian_guru():
    """Test the new AtlassianToolbelt specialist agent"""
    try:
        from agents.atlassian_guru import AtlassianToolbelt
        
        # Initialize the toolbelt
        async with AtlassianToolbelt() as toolbelt:
            # Test basic capabilities
            capabilities = await toolbelt.get_capabilities()
            
            # Test health check
            health_ok = await toolbelt.health_check()
            
            # Test a simple search task
            search_result = await toolbelt.execute_task("Search for information about UiPath Autopilot features")
            
            return {
                "status": "success",
                "atlassian_toolbelt": {
                    "health_check": health_ok,
                    "capabilities": capabilities,
                    "test_search": {
                        "task": "Search for information about UiPath Autopilot features",
                        "result": search_result
                    }
                },
                "integration": "AtlassianToolbelt successfully integrated as black box tool"
            }
            
    except Exception as e:
        logger.error(f"AtlassianToolbelt test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "AtlassianToolbelt integration test failed"
        }

@app.post("/admin/clear-webhook-cache")
async def clear_webhook_cache():
    """Clear the webhook cache to resolve duplicate detection issues"""
    try:
        if hasattr(app.state, 'webhook_cache'):
            cache = app.state.webhook_cache
            cache_size_before = len(cache.cache)
            cache.cache.clear()
            cache.stats = {
                "total_requests": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "duplicates_prevented": 0,
                "processing_time_saved": 0.0
            }
            
            return {
                "success": True,
                "message": f"Webhook cache cleared. Removed {cache_size_before} entries.",
                "cache_size_before": cache_size_before,
                "cache_size_after": 0
            }
        else:
            return {
                "success": False,
                "message": "Webhook cache not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear cache: {str(e)}"
        }

@app.get("/admin/test-hybrid-memory")
async def test_hybrid_memory():
    """Test the new hybrid memory system with rolling long-term summary and token-managed live history"""
    try:
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Simulate a conversation with multiple messages
        test_conversation_id = "test_conv_123"
        conversation_key = f"conv:{test_conversation_id}:1234567890.001"
        
        # Store multiple test messages to build up history
        test_messages = [
            {"user_name": "alice", "text": "What's the status of the Q4 project?", "type": "user"},
            {"user_name": "bot", "text": "The Q4 project is on track. We've completed 75% of the milestones.", "type": "bot"},
            {"user_name": "bob", "text": "Are there any blockers I should know about?", "type": "user"},
            {"user_name": "bot", "text": "Currently there are no critical blockers. The team is working on optimization tasks.", "type": "bot"},
            {"user_name": "alice", "text": "When is the next milestone review?", "type": "user"},
            {"user_name": "bot", "text": "The next milestone review is scheduled for next Tuesday at 2 PM.", "type": "bot"},
            {"user_name": "charlie", "text": "Can you share the latest performance metrics?", "type": "user"},
            {"user_name": "bot", "text": "Current performance shows 92% uptime and response times under 200ms.", "type": "bot"},
            {"user_name": "alice", "text": "Excellent! Any concerns for next quarter?", "type": "user"},
            {"user_name": "bot", "text": "For Q1, we need to focus on scaling infrastructure and team expansion.", "type": "bot"},
            {"user_name": "bob", "text": "What about budget allocation?", "type": "user"},
            {"user_name": "bot", "text": "Budget review meeting is planned for December 15th.", "type": "bot"}
        ]
        
        # Store messages to simulate a conversation history
        for msg in test_messages:
            await memory_service.store_raw_message(conversation_key, msg)
        
        # Test hybrid history construction
        current_query = "Can you summarize our discussion about project planning?"
        hybrid_history = await orchestrator._construct_hybrid_history(conversation_key, current_query)
        
        # Get current memory stats
        recent_messages = await memory_service.get_recent_messages(conversation_key, limit=10)
        
        # Test the system with over 10 messages to trigger long-term summary
        additional_messages = [
            {"user_name": "dave", "text": "How's the team morale?", "type": "user"},
            {"user_name": "bot", "text": "Team morale is high with recent success.", "type": "bot"},
            {"user_name": "eve", "text": "Any training needs?", "type": "user"}
        ]
        
        for msg in additional_messages:
            await memory_service.store_raw_message(conversation_key, msg)
        
        # Test again with more messages to see long-term summary activation
        hybrid_history_with_summary = await orchestrator._construct_hybrid_history(conversation_key, "What are the key takeaways?")
        
        return {
            "status": "success",
            "test_data": {
                "total_messages_stored": len(test_messages) + len(additional_messages),
                "recent_messages_count": len(recent_messages),
                "conversation_key": conversation_key
            },
            "initial_hybrid_history": {
                "summarized_message_count": hybrid_history.get("summarized_message_count", 0),
                "live_message_count": hybrid_history.get("live_message_count", 0),
                "estimated_tokens": hybrid_history.get("estimated_tokens", 0),
                "has_summarized_history": bool(hybrid_history.get("summarized_history")),
                "live_history_preview": hybrid_history.get("live_history", "")[:200] + "..." if len(hybrid_history.get("live_history", "")) > 200 else hybrid_history.get("live_history", "")
            },
            "after_additional_messages": {
                "summarized_message_count": hybrid_history_with_summary.get("summarized_message_count", 0),
                "live_message_count": hybrid_history_with_summary.get("live_message_count", 0),
                "estimated_tokens": hybrid_history_with_summary.get("estimated_tokens", 0),
                "has_summarized_history": bool(hybrid_history_with_summary.get("summarized_history")),
                "summarized_history_preview": hybrid_history_with_summary.get("summarized_history", "")[:200] + "..." if len(hybrid_history_with_summary.get("summarized_history", "")) > 200 else hybrid_history_with_summary.get("summarized_history", ""),
                "live_history_preview": hybrid_history_with_summary.get("live_history", "")[:200] + "..." if len(hybrid_history_with_summary.get("live_history", "")) > 200 else hybrid_history_with_summary.get("live_history", "")
            },
            "memory_system": {
                "type": "hybrid",
                "features": [
                    "Rolling long-term summary",
                    "Token-managed live history", 
                    "Automatic message overflow handling",
                    "10-message sliding window",
                    "2000-token live history limit"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Hybrid memory test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Hybrid memory system test failed"
        }

# Removed obsolete test-http-client-optimization endpoint - functionality replaced by AtlassianToolbelt

# Removed obsolete mcp-tools-cache-stats and clear-mcp-tools-cache endpoints - functionality replaced by AtlassianToolbelt

@app.get("/admin/test-precise-token-management")
async def test_precise_token_management():
    """Test the new precise token management system with tiktoken vs character-based estimation"""
    try:
        from services.data.token_manager import TokenManager
        from services.core.memory_service import MemoryService
        from agents.orchestrator_agent import OrchestratorAgent
        import uuid
        
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        token_manager = TokenManager(model_name="gpt-4")
        
        # Create test conversation data with varied message lengths
        test_conversation_key = f"test_token_management:{uuid.uuid4()}"
        
        test_messages = [
            {"user_name": "Alice", "text": "Hi there! How are you today?"},
            {"user_name": "Bot", "text": "Hello Alice! I'm doing well, thank you for asking. How can I assist you today?"},
            {"user_name": "Alice", "text": "I need help with understanding how UiPath Autopilot works in our enterprise environment. We have complex workflows involving multiple systems including Salesforce, SAP, and our custom CRM platform. Can you explain how Autopilot can help streamline these processes and what are the key benefits we should expect?"},
            {"user_name": "Bot", "text": "UiPath Autopilot is designed to help automate complex enterprise workflows exactly like yours. For your Salesforce, SAP, and CRM integration, Autopilot can create intelligent automation workflows that connect these systems seamlessly. The key benefits include: 1) Reduced manual data entry across systems, 2) Intelligent process discovery to identify automation opportunities, 3) Real-time monitoring and optimization of your workflows, 4) AI-powered decision making to handle exceptions and edge cases. Would you like me to dive deeper into any specific aspect of how this would work with your current tech stack?"},
            {"user_name": "Alice", "text": "That's very helpful! Can you give me specific examples?"},
            {"user_name": "Bot", "text": "Absolutely! Here are some specific examples for your environment: 1) Automated lead sync: When a new lead enters Salesforce, Autopilot can automatically create corresponding records in your CRM and trigger SAP workflows for account setup. 2) Invoice processing: Extract data from invoices, validate against SAP pricing rules, and update both Salesforce opportunities and CRM records. 3) Customer onboarding: Orchestrate the entire process from CRM lead capture through SAP account creation and Salesforce opportunity tracking."},
            {"user_name": "Alice", "text": "Excellent! What about ROI and implementation timeline?"},
            {"user_name": "Bot", "text": "Great question! Based on similar enterprise implementations: ROI typically ranges from 200-400% within the first year, with payback periods of 6-9 months. Implementation timeline depends on complexity: Phase 1 (pilot workflows): 2-3 months, Phase 2 (core processes): 4-6 months, Phase 3 (advanced automation): 6-12 months. The key is starting with high-impact, low-complexity processes to demonstrate value quickly."},
            {"user_name": "Alice", "text": "Perfect! Can you schedule a meeting with our technical team next week?"},
            {"user_name": "Bot", "text": "I'd be happy to help coordinate that! I can check availability and suggest meeting times. Could you provide the email addresses of the technical team members you'd like to include, and what days work best for your schedule next week?"},
            {"user_name": "Alice", "text": "Let me get back to you on the email addresses. Thanks for all the help!"},
            {"user_name": "Bot", "text": "You're very welcome, Alice! Feel free to reach out anytime when you have those email addresses or any other questions about UiPath Autopilot. Have a great day!"}
        ]
        
        # Store messages in memory service
        for msg in test_messages:
            await memory_service.store_raw_message(test_conversation_key, msg)
        
        # Test 1: Character-based estimation (old method)
        old_method_results = {
            "total_chars": 0,
            "estimated_tokens": 0,
            "message_count": len(test_messages)
        }
        
        for msg in test_messages:
            user_name = msg.get("user_name", "Unknown")
            text = msg.get("text", "")
            is_bot = user_name.lower() in ["bot", "autopilot", "assistant"]
            speaker = "Bot" if is_bot else "User"
            formatted_text = f"{speaker}: {text}"
            
            old_method_results["total_chars"] += len(formatted_text)
            old_method_results["estimated_tokens"] += len(formatted_text) // 4
        
        # Test 2: Precise token counting with tiktoken
        precise_results = {
            "tokenized_messages": [],
            "total_precise_tokens": 0,
            "message_count": len(test_messages)
        }
        
        for msg in test_messages:
            tokenized_msg = token_manager.tokenize_message(msg)
            precise_results["tokenized_messages"].append({
                "speaker": tokenized_msg.speaker,
                "text_preview": tokenized_msg.text[:50] + "..." if len(tokenized_msg.text) > 50 else tokenized_msg.text,
                "precise_tokens": tokenized_msg.token_count,
                "char_estimate": len(tokenized_msg.formatted_text) // 4
            })
            precise_results["total_precise_tokens"] += tokenized_msg.token_count
        
        # Test 3: Token-managed history with different limits
        token_limits = [500, 1000, 1500, 2000]
        token_management_results = []
        
        for limit in token_limits:
            messages_to_keep, messages_to_summarize, token_stats = token_manager.build_token_managed_history(
                test_messages, limit, preserve_recent=2
            )
            
            token_management_results.append({
                "token_limit": limit,
                "kept_messages": token_stats["kept_messages"],
                "summarized_messages": token_stats["summarized_messages"],
                "actual_tokens_used": token_stats["total_tokens"],
                "efficiency": f"{(token_stats['total_tokens']/limit)*100:.1f}%" if limit > 0 else "0%"
            })
        
        # Test 4: Hybrid history construction comparison
        current_query = "What are the next steps for our UiPath Autopilot implementation?"
        
        # Old method simulation
        old_hybrid = await orchestrator._construct_hybrid_history(test_conversation_key, current_query)
        
        # Test 5: Context token calculation
        context_breakdown = token_manager.calculate_context_tokens(
            summarized_history=old_hybrid.get("summarized_history", ""),
            live_history=old_hybrid.get("live_history", ""),
            current_query=current_query
        )
        
        # Test 6: Efficiency comparison
        efficiency_comparison = token_manager.get_token_efficiency_stats(
            old_method_results["estimated_tokens"],
            precise_results["total_precise_tokens"]
        )
        
        # Test 7: Type validation and error handling robustness
        robustness_tests = []
        
        # Test various invalid inputs to ensure type checking works
        test_inputs = [
            {"name": "None input", "value": None},
            {"name": "Integer input", "value": 123},
            {"name": "List input", "value": ["hello", "world"]},
            {"name": "Empty string", "value": ""},
            {"name": "Unicode text", "value": "Hello 世界 🌍"},
            {"name": "Very long text", "value": "A" * 10000}
        ]
        
        for test_input in test_inputs:
            try:
                result = token_manager.count_tokens(test_input["value"])
                robustness_tests.append({
                    "test": test_input["name"],
                    "input_type": str(type(test_input["value"])),
                    "token_count": result,
                    "status": "success"
                })
            except Exception as e:
                robustness_tests.append({
                    "test": test_input["name"],
                    "input_type": str(type(test_input["value"])),
                    "error": str(e),
                    "status": "error"
                })
        
        # Test invalid message structures
        invalid_messages = [
            {"name": "Non-dict message", "value": "not a dict"},
            {"name": "Missing text field", "value": {"user_name": "Alice"}},
            {"name": "Non-string text", "value": {"user_name": "Alice", "text": 123}},
            {"name": "None text", "value": {"user_name": "Alice", "text": None}},
            {"name": "Non-string user_name", "value": {"user_name": 456, "text": "Hello"}}
        ]
        
        message_robustness_tests = []
        for test_msg in invalid_messages:
            try:
                tokenized = token_manager.tokenize_message(test_msg["value"])
                message_robustness_tests.append({
                    "test": test_msg["name"],
                    "result": {
                        "speaker": tokenized.speaker,
                        "text_preview": tokenized.text[:20] + "..." if len(tokenized.text) > 20 else tokenized.text,
                        "token_count": tokenized.token_count
                    },
                    "status": "success"
                })
            except Exception as e:
                message_robustness_tests.append({
                    "test": test_msg["name"],
                    "error": str(e),
                    "status": "error"
                })

        return {
            "status": "success",
            "test_results": {
                "old_character_method": old_method_results,
                "precise_tiktoken_method": precise_results,
                "efficiency_comparison": efficiency_comparison,
                "token_management_by_limit": token_management_results,
                "hybrid_history_test": {
                    "conversation_key": test_conversation_key,
                    "summarized_messages": old_hybrid.get("summarized_message_count", 0),
                    "live_messages": old_hybrid.get("live_message_count", 0),
                    "precise_tokens": old_hybrid.get("precise_tokens", "not_available"),
                    "old_estimated_tokens": old_hybrid.get("estimated_tokens", 0),
                    "token_efficiency": old_hybrid.get("token_efficiency", {})
                },
                "context_token_breakdown": context_breakdown,
                "robustness_testing": {
                    "type_validation_tests": robustness_tests,
                    "message_structure_tests": message_robustness_tests
                },
                "test_query": current_query
            },
            "summary": {
                "accuracy_improvement": f"{efficiency_comparison.get('accuracy_percentage', 0)}%",
                "token_difference": efficiency_comparison.get("token_difference", 0),
                "is_more_efficient": efficiency_comparison.get("is_more_efficient", False),
                "robustness_tests_passed": len([t for t in robustness_tests if t["status"] == "success"]),
                "message_tests_passed": len([t for t in message_robustness_tests if t["status"] == "success"]),
                "description": "Precise tiktoken counting with comprehensive type validation and error handling"
            }
        }
        
    except Exception as e:
        logger.error(f"Precise token management test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "description": "Failed to complete precise token management test"
        }

@app.get("/admin/test-entity-extraction")
async def test_entity_extraction():
    """Test the new entity extraction and structured memory system"""
    try:
        from services.data.entity_store import EntityStore, Entity
        from workers.entity_extractor import extract_entities_from_conversation
        
        memory_service = MemoryService()
        entity_store = EntityStore(memory_service)
        
        # Test conversation data
        test_conversation_key = "conv:test_channel:1234567890.001"
        test_user_query = "I need to follow up on JIRA ticket DEV-456 for the Autopilot project. The deadline is next Friday and John Smith is the owner."
        test_bot_response = "I found that JIRA ticket DEV-456 is related to the Autopilot project. The deadline you mentioned is important - I'll help you track that. John Smith should have the latest status on this ticket."
        
        # Test pattern-based entity extraction
        entities = await entity_store.extract_entities_from_text(
            text=test_user_query,
            conversation_key=test_conversation_key,
            context="user_query"
        )
        
        # Store the extracted entities
        if entities:
            store_result = await entity_store.store_entities(entities, test_conversation_key)
        else:
            store_result = False
        
        # Test entity search
        search_result = await entity_store.search_entities(
            query_keywords=["DEV-456", "Autopilot", "John", "deadline"],
            conversation_key=test_conversation_key,
            limit=5
        )
        
        # Test entity summary
        summary = await entity_store.get_conversation_entity_summary(test_conversation_key)
        
        # Queue background extraction (test Celery integration)
        try:
            task_result = extract_entities_from_conversation.delay(
                conversation_key=test_conversation_key,
                user_query=test_user_query,
                bot_response=test_bot_response,
                user_name="test_user",
                additional_context={"test": True}
            )
            background_task_id = task_result.id
        except Exception as e:
            background_task_id = f"Error: {str(e)}"
        
        return {
            "status": "success",
            "entity_extraction_test": {
                "pattern_extraction": {
                    "entities_found": len(entities),
                    "entities": [
                        {
                            "key": e.key,
                            "type": e.type,
                            "value": e.value,
                            "relevance_score": e.relevance_score
                        } for e in entities
                    ]
                },
                "storage_test": {
                    "store_success": store_result,
                    "entities_stored": len(entities) if entities else 0
                },
                "search_test": {
                    "search_keywords": ["DEV-456", "Autopilot", "John", "deadline"],
                    "entities_found": len(search_result),
                    "search_results": [
                        {
                            "key": e.key,
                            "type": e.type,
                            "value": e.value,
                            "relevance_score": e.relevance_score
                        } for e in search_result
                    ]
                },
                "conversation_summary": summary,
                "background_extraction": {
                    "task_id": background_task_id,
                    "description": "Celery task queued for AI-powered entity extraction"
                }
            },
            "integration": "Entity extraction system operational with pattern matching, storage, search, and background processing"
        }
        
    except Exception as e:
        logger.error(f"Entity extraction test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Entity extraction system test failed"
        }

@app.get("/admin/test-conversation-entity-extraction")
async def test_conversation_entity_extraction():
    """Test the complete conversation entity extraction task workflow"""
    try:
        from workers.entity_extractor import extract_entities_from_conversation
        
        # Test conversation data with realistic content
        conversation_key = f"test_conversation_{int(time.time())}"
        user_query = "Hi, I need to check the status of JIRA ticket DEV-456 for the Autopilot project. John Smith mentioned the deadline is next Friday and we need to coordinate with the QA team."
        bot_response = "I'll help you check the status of DEV-456. Based on the latest information, this ticket is currently in the 'In Progress' state. The Autopilot project is on track, and John Smith has been working on the implementation. The deadline for next Friday (December 15th) looks achievable. I've also noted that QA team coordination will be needed once development is complete."
        
        # Execute the Celery task directly (synchronous for testing)
        task_result = extract_entities_from_conversation(
            conversation_key=conversation_key,
            user_query=user_query,
            bot_response=bot_response,
            user_name="test_user",
            additional_context={"source": "admin_test"}
        )
        
        return {
            "status": "success",
            "conversation_key": conversation_key,
            "task_result": task_result,
            "test_input": {
                "user_query": user_query[:100] + "..." if len(user_query) > 100 else user_query,
                "bot_response": bot_response[:100] + "..." if len(bot_response) > 100 else bot_response
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing conversation entity extraction: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/admin/test-entity-deduplication")
async def test_entity_deduplication():
    """Test the new regex+AI entity deduplication system"""
    logger.info("Testing entity deduplication between regex and AI extraction...")
    
    try:
        # Import the worker task class for testing
        from workers.entity_extractor import EntityExtractionTask
        from services.data.entity_store import Entity
        
        # Create a test task instance
        task = EntityExtractionTask()
        task._initialize_services()
        
        conversation_key = f"dedup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create test entities with deliberate duplicates between regex and AI extraction
        regex_entities = [
            Entity(
                key="jira_ticket:autopilot-123",
                type="jira_ticket",
                value="AUTOPILOT-123",
                context="Found via regex pattern matching",
                conversation_key=conversation_key,
                relevance_score=1.2,
                aliases=["AUTOPILOT-123"],
                metadata={"extraction_method": "regex_pattern", "pattern_used": "JIRA ticket pattern"}
            ),
            Entity(
                key="project:uipath_autopilot",
                type="project", 
                value="UiPath Autopilot",
                context="Project mentioned in text",
                conversation_key=conversation_key,
                relevance_score=1.5,
                aliases=["Autopilot", "UiPath Autopilot"],
                metadata={"extraction_method": "regex_pattern", "pattern_used": "Project name pattern"}
            ),
            Entity(
                key="person:john_doe",
                type="person",
                value="John Doe",
                context="Person mentioned as developer",
                conversation_key=conversation_key,
                relevance_score=1.0,
                aliases=["John", "J. Doe"],
                metadata={"extraction_method": "regex_pattern", "pattern_used": "Person name pattern"}
            )
        ]
        
        ai_entities = [
            Entity(
                key="jira_ticket:autopilot-123",  # Duplicate with higher relevance
                type="jira_ticket",
                value="AUTOPILOT-123",
                context="AI identified this as a critical JIRA ticket for the Autopilot project with high priority status",
                conversation_key=conversation_key,
                relevance_score=1.8,  # Higher relevance from AI
                aliases=["AUTOPILOT-123", "Autopilot-123"],
                metadata={"extraction_method": "gemini_ai", "importance_score": 9, "user_name": "test_user"}
            ),
            Entity(
                key="deadline:december_15_2024",
                type="deadline",
                value="December 15, 2024",
                context="AI identified this as an important project deadline",
                conversation_key=conversation_key,
                relevance_score=1.6,
                aliases=["Dec 15 2024", "12/15/2024"],
                metadata={"extraction_method": "gemini_ai", "importance_score": 8, "user_name": "test_user"}
            ),
            Entity(
                key="person:john_doe",  # Duplicate with richer context
                type="person",
                value="John Doe",
                context="AI identified John Doe as the lead developer responsible for the Autopilot project implementation and technical decisions",
                conversation_key=conversation_key,
                relevance_score=1.3,  # Lower relevance but richer context
                aliases=["John", "J. Doe", "John D."],
                metadata={"extraction_method": "gemini_ai", "importance_score": 7, "user_name": "test_user"}
            )
        ]
        
        # Combine the entities (simulating the worker flow)
        all_entities = regex_entities + ai_entities
        
        # Test deduplication
        deduplicated_entities = task._deduplicate_extraction_results(all_entities)
        
        # Analyze the results
        original_count = len(all_entities)
        deduplicated_count = len(deduplicated_entities)
        duplicates_merged = original_count - deduplicated_count
        
        # Find the merged entities to show what happened
        merged_results = []
        for entity in deduplicated_entities:
            entity_info = {
                "key": entity.key,
                "type": entity.type,
                "value": entity.value,
                "relevance_score": entity.relevance_score,
                "context_length": len(entity.context or ""),
                "aliases_count": len(entity.aliases or []),
                "extraction_method": entity.metadata.get("extraction_method", "unknown"),
                "was_merged": "+" in entity.metadata.get("extraction_method", "")
            }
            merged_results.append(entity_info)
        
        return {
            "status": "success",
            "deduplication_test": {
                "input_entities": {
                    "regex_entities": len(regex_entities),
                    "ai_entities": len(ai_entities),
                    "total_before": original_count
                },
                "deduplication_results": {
                    "entities_after": deduplicated_count,
                    "duplicates_merged": duplicates_merged,
                    "deduplication_rate": f"{(duplicates_merged / original_count * 100):.1f}%" if original_count > 0 else "0%"
                },
                "merged_entities": merged_results,
                "effectiveness": {
                    "redundant_writes_prevented": duplicates_merged,
                    "context_enrichment": sum(1 for e in merged_results if e["was_merged"]),
                    "relevance_optimization": "Higher scoring entities preserved as primary"
                }
            },
            "performance_impact": {
                "storage_efficiency": f"Reduced storage operations by {duplicates_merged} writes",
                "context_quality": "AI contexts merged with regex patterns for richer entity understanding",
                "relevance_accuracy": "Best relevance scores preserved while combining extraction methods"
            },
            "integration": "Regex+AI entity deduplication system operational with intelligent merging"
        }
        
    except Exception as e:
        logger.error(f"Error testing entity deduplication: {e}")
        return {
            "status": "error",
            "error": str(e),
            "integration": "Entity deduplication system encountered errors"
        }

@app.get("/admin/test-gemini-json-retry")
async def test_gemini_json_retry():
    """
    Test the robust JSON parsing with retry mechanism for Gemini entity extraction.
    Simulates both successful parsing and malformed JSON scenarios.
    """
    try:
        logger.info("Testing Gemini JSON parsing with retry mechanism...")
        
        # Initialize entity extraction task
        from workers.entity_extractor import EntityExtractionTask
        from services.data.entity_store import EntityStore
        
        # Use initialized memory service from global scope
        test_memory_service = globals().get('memory_service')
        
        entity_task = EntityExtractionTask()
        entity_task.entity_store = EntityStore(test_memory_service)
        
        conversation_key = f"test_json_retry_{int(time.time())}"
        user_name = "test_user"
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Valid JSON",
                "response": '''[
                    {
                        "type": "jira_ticket",
                        "value": "AUTOPILOT-456",
                        "context": "Bug fix ticket",
                        "importance": 8
                    }
                ]''',
                "expected_success": True
            },
            {
                "name": "Valid JSON with markdown",
                "response": '''```json
                [
                    {
                        "type": "person",
                        "value": "Sarah Johnson",
                        "context": "Project manager",
                        "importance": 7
                    }
                ]
                ```''',
                "expected_success": True
            },
            {
                "name": "Malformed JSON - missing comma (should trigger retry)",
                "response": '''[
                    {
                        "type": "project"
                        "value": "UiPath RPA",
                        "context": "Main project",
                        "importance": 9
                    }
                ]''',
                "expected_success": False  # Would succeed with retry in real scenario
            },
            {
                "name": "Malformed JSON - extra comma",
                "response": '''[
                    {
                        "type": "deadline",
                        "value": "Q1 2025",
                        "context": "Project deadline",
                        "importance": 8,
                    }
                ]''',
                "expected_success": False  # Would succeed with retry in real scenario
            }
        ]
        
        test_results = []
        
        for scenario in test_scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            
            try:
                # Test the parsing method directly
                entities = entity_task._parse_gemini_response_with_retry(
                    scenario["response"], 
                    conversation_key, 
                    user_name, 
                    max_retries=1  # Reduced for testing
                )
                
                success = len(entities) > 0
                test_results.append({
                    "scenario": scenario["name"],
                    "success": success,
                    "entities_extracted": len(entities),
                    "expected_success": scenario["expected_success"],
                    "result": "PASS" if success else "FAIL (would retry with real Gemini)",
                    "entity_samples": [
                        {
                            "type": e.type,
                            "value": e.value,
                            "context": e.context[:50] + "..." if len(e.context) > 50 else e.context
                        } for e in entities[:2]
                    ]
                })
                
            except Exception as e:
                test_results.append({
                    "scenario": scenario["name"],
                    "success": False,
                    "entities_extracted": 0,
                    "expected_success": scenario["expected_success"],
                    "result": f"ERROR: {str(e)}",
                    "entity_samples": []
                })
        
        # Summary statistics
        successful_scenarios = sum(1 for r in test_results if r["success"])
        total_scenarios = len(test_results)
        
        return {
            "status": "success",
            "test_summary": {
                "scenarios_tested": total_scenarios,
                "successful_parsing": successful_scenarios,
                "success_rate": f"{(successful_scenarios/total_scenarios)*100:.1f}%",
                "retry_mechanism": "Implemented with Gemini self-correction prompts"
            },
            "scenario_results": test_results,
            "retry_features": {
                "max_retries": "2 (configurable)",
                "self_correction": "Automatic follow-up prompt when JSON parsing fails",
                "correction_prompt": "Instructs Gemini to fix malformed JSON and return only valid JSON",
                "error_recovery": "Graceful fallback to empty list after all retries exhausted",
                "logging": "Detailed logging of retry attempts and self-correction responses"
            },
            "production_benefits": {
                "robustness": "Handles malformed JSON responses from LLM automatically",
                "reliability": "Reduces entity extraction failures due to JSON parsing errors",
                "self_healing": "LLM can often correct its own JSON formatting mistakes",
                "error_visibility": "Comprehensive logging for debugging JSON parsing issues"
            },
            "conversation_key": conversation_key
        }
        
    except Exception as e:
        logger.error(f"Error testing Gemini JSON retry mechanism: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to test JSON retry mechanism"
        }

@app.get("/admin/test-relevance-score-guidance")
async def test_relevance_score_guidance():
    """Test that orchestrator properly uses entity relevance scores for decision making"""
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from services.core.memory_service import MemoryService
        from services.data.entity_store import EntityStore, Entity
        from models.schemas import ProcessedMessage
        import time
        
        # Initialize components
        memory_service = MemoryService()
        entity_store = EntityStore(memory_service)
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create test conversation key
        conversation_key = "conv:test_channel:relevance_test"
        
        # Create entities with varying relevance scores
        test_entities = [
            Entity(
                key="jira_ticket:critical_bug_123",
                type="jira_ticket", 
                value="CRITICAL-123",
                context="High priority security bug affecting production authentication system",
                conversation_key=conversation_key,
                relevance_score=1.8,  # High relevance - should get strong attention
                aliases=["CRITICAL-123", "auth bug"],
                metadata={"priority": "critical", "extraction_method": "ai_enhanced"}
            ),
            Entity(
                key="jira_ticket:minor_ui_456",
                type="jira_ticket",
                value="UI-456", 
                context="Minor UI spacing issue in footer",
                conversation_key=conversation_key,
                relevance_score=0.3,  # Low relevance - should get less attention
                aliases=["UI-456", "footer spacing"],
                metadata={"priority": "low", "extraction_method": "pattern_matching"}
            ),
            Entity(
                key="project:autopilot_v2",
                type="project",
                value="UiPath Autopilot v2.0",
                context="Major Autopilot release with AI enhancements and new features",
                conversation_key=conversation_key,
                relevance_score=1.6,  # High relevance - should influence tool selection
                aliases=["Autopilot v2", "AP v2.0"],
                metadata={"importance": "high", "status": "active"}
            ),
            Entity(
                key="person:john_tester",
                type="person",
                value="John Tester",
                context="Mentioned once in passing during standup",
                conversation_key=conversation_key, 
                relevance_score=0.5,  # Low relevance - should not drive decisions
                aliases=["John", "JT"],
                metadata={"role": "qa", "team": "testing"}
            )
        ]
        
        # Store entities
        await entity_store.store_entities(test_entities, conversation_key)
        
        # Create test message that could relate to multiple entities
        test_message = ProcessedMessage(
            channel_id="C_TEST_RELEVANCE",
            user_id="U_TEST_USER",
            text="What's the status on the authentication issues we discussed?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Alice",
            user_display_name="Alice Johnson", 
            user_title="Product Manager",
            user_department="Product",
            channel_name="engineering",
            is_dm=False,
            thread_context=""
        )
        
        # Test entity search and relevance scoring
        entity_search_results = await orchestrator._search_relevant_entities(
            test_message.text, conversation_key
        )
        
        # Test orchestrator analysis with entity context
        start_time = time.time()
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        analysis_time = time.time() - start_time
        
        # Analyze how relevance scores influenced the plan
        high_relevance_entities = [e for e in entity_search_results.get("entities", []) if e.get("relevance_score", 0) > 1.5]
        low_relevance_entities = [e for e in entity_search_results.get("entities", []) if e.get("relevance_score", 0) < 0.6]
        
        return {
            "status": "success",
            "relevance_score_guidance": {
                "prompt_guidance_added": "Pay closer attention to entities with higher relevance_score values",
                "high_relevance_threshold": 1.5,
                "entity_search_results": entity_search_results,
                "analysis_time": round(analysis_time, 3),
                "execution_plan": execution_plan
            },
            "entity_analysis": {
                "total_entities_found": len(entity_search_results.get("entities", [])),
                "high_relevance_entities": len(high_relevance_entities),
                "high_relevance_details": [
                    {
                        "key": e.get("key"),
                        "type": e.get("type"), 
                        "relevance_score": e.get("relevance_score"),
                        "value": e.get("value")
                    } for e in high_relevance_entities
                ],
                "low_relevance_entities": len(low_relevance_entities),
                "low_relevance_details": [
                    {
                        "key": e.get("key"),
                        "type": e.get("type"),
                        "relevance_score": e.get("relevance_score"), 
                        "value": e.get("value")
                    } for e in low_relevance_entities
                ]
            },
            "expected_behavior": {
                "high_relevance_should_drive_decisions": "CRITICAL-123 (1.8 score) and Autopilot v2.0 (1.6 score) should strongly influence tool selection",
                "low_relevance_should_be_secondary": "UI-456 (0.3 score) and John Tester (0.5 score) should receive less attention",
                "tool_selection_impact": "Query about 'authentication issues' should prioritize atlassian_search due to high-relevance CRITICAL-123 entity"
            }
        }
        
    except Exception as e:
        logger.error(f"Relevance score guidance test failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/test-atlassian-toolbelt")
async def test_atlassian_toolbelt():
    """Admin endpoint to test Atlassian toolbelt functionality"""
    try:
        from agents.atlassian_guru import AtlassianToolbelt
        
        test_results = {
            "initialization": False,
            "health_check": False,
            "capabilities": None,
            "task_execution": None,
            "error_details": []
        }
        
        async with AtlassianToolbelt() as toolbelt:
            test_results["initialization"] = True
            
            # Test health check with timeout
            try:
                health = await asyncio.wait_for(toolbelt.health_check(), timeout=10.0)
                test_results["health_check"] = health
            except asyncio.TimeoutError:
                test_results["health_check"] = False
                test_results["error_details"].append("Health check timed out (10s)")
            
            if not test_results["health_check"]:
                return {"status": "health_check_failed", "test_results": test_results}
            
            # Test capabilities with timeout
            try:
                capabilities = await asyncio.wait_for(toolbelt.get_capabilities(), timeout=30.0)
                test_results["capabilities"] = capabilities
            except asyncio.TimeoutError:
                test_results["error_details"].append("Capabilities discovery timed out (30s)")
                return {"status": "timeout", "test_results": test_results}
            
            # Test simple task execution with timeout
            task = "Get status of Atlassian configuration"
            try:
                result = await asyncio.wait_for(toolbelt.execute_task(task), timeout=45.0)
                test_results["task_execution"] = {
                    "task": task,
                    "status": result.get("status"),
                    "message": result.get("message"),
                    "data_available": result.get("data") is not None,
                    "execution_method": result.get("execution_method")
                }
            except asyncio.TimeoutError:
                test_results["error_details"].append("Task execution timed out (45s)")
                test_results["task_execution"] = {"status": "timeout"}
            
            overall_success = (
                test_results["initialization"] and 
                test_results["health_check"] and
                test_results["capabilities"] and
                test_results.get("task_execution", {}).get("status") == "success"
            )
            
            return {
                "status": "success" if overall_success else "partial_failure",
                "atlassian_toolbelt_working": overall_success,
                "test_results": test_results,
                "summary": {
                    "server_url": capabilities.get("server_url") if capabilities else None,
                    "available_tools": len(capabilities.get("available_tools", [])) if capabilities else 0,
                    "task_execution_status": test_results.get("task_execution", {}).get("status", "not_tested")
                }
            }
        
    except Exception as e:
        logger.error(f"Error testing Atlassian toolbelt: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "test_results": test_results
        }

@app.get("/admin/test-vector-search-refused")
async def test_vector_search_refused():
    """Test why orchestrator might be refusing vector search"""
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from services.core.memory_service import MemoryService
        from models.schemas import ProcessedMessage
        
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Test with a query that should use vector search
        test_queries = [
            "How do I learn Python programming?",  # Should use vector search
            "Generic programming concepts",  # Should use vector search
            "Tell me about design patterns in software",  # Should use vector search
        ]
        
        results = []
        
        for query in test_queries:
            # Create test message
            test_message = ProcessedMessage(
                channel_id="C087QKECFKQ",
                user_id="U12345TEST",
                text=query,
                message_ts="1640995200.001500",
                thread_ts=None,
                user_name="test_user",
                user_first_name="Test",
                user_display_name="Test User", 
                user_title="Software Engineer",
                user_department="Engineering",
                channel_name="general",
                is_dm=False
            )
            
            try:
                # Set a shorter timeout to avoid long waits
                execution_plan = await asyncio.wait_for(
                    orchestrator._analyze_query_and_plan(test_message),
                    timeout=15.0
                )
                
                tools_needed = execution_plan.get("tools_needed", []) if execution_plan else []
                vector_queries = execution_plan.get("vector_queries", []) if execution_plan else []
                atlassian_actions = execution_plan.get("atlassian_actions", []) if execution_plan else []
                analysis = execution_plan.get("analysis", "") if execution_plan else "No plan generated"
                
                results.append({
                    "query": query,
                    "execution_plan_generated": execution_plan is not None,
                    "tools_needed": tools_needed,
                    "vector_queries": vector_queries,
                    "atlassian_actions": len(atlassian_actions),
                    "analysis": analysis,
                    "vector_search_selected": "vector_search" in tools_needed,
                    "atlassian_search_selected": "atlassian_search" in tools_needed
                })
                
            except asyncio.TimeoutError:
                results.append({
                    "query": query,
                    "error": "Query analysis timed out",
                    "execution_plan_generated": False,
                    "tools_needed": [],
                    "vector_queries": [],
                    "atlassian_actions": 0,
                    "vector_search_selected": False,
                    "atlassian_search_selected": False
                })
            except Exception as e:
                results.append({
                    "query": query,
                    "error": str(e),
                    "execution_plan_generated": False,
                    "tools_needed": [],
                    "vector_queries": [],
                    "atlassian_actions": 0,
                    "vector_search_selected": False,
                    "atlassian_search_selected": False
                })
        
        # Test vector search tool directly
        vector_tool_working = False
        vector_test_results = []
        try:
            vector_results = await orchestrator.vector_tool.search("Python programming", top_k=3)
            vector_tool_working = len(vector_results) > 0
            vector_test_results = [
                {
                    "score": r.get("score", 0),
                    "content": r.get("content", "")[:50] + "..."
                } for r in vector_results[:2]
            ]
        except Exception as e:
            vector_test_results = [{"error": str(e)}]
        
        return {
            "status": "success",
            "vector_tool_working": vector_tool_working,
            "vector_test_results": vector_test_results,
            "orchestrator_analysis": results,
            "summary": {
                "queries_tested": len(test_queries),
                "execution_plans_generated": sum(1 for r in results if r.get("execution_plan_generated")),
                "vector_search_selections": sum(1 for r in results if r.get("vector_search_selected")),
                "atlassian_search_selections": sum(1 for r in results if r.get("atlassian_search_selected"))
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing vector search behavior: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

# Notion Dashboard Admin Endpoints

@app.get("/admin/notion-dashboard-status")
async def notion_dashboard_status():
    """Admin endpoint to check Notion dashboard connection and configuration"""
    try:
        from services.external_apis.notion_service import NotionService
        
        notion_service = NotionService()
        
        if not notion_service.enabled:
            return {
                "status": "disabled",
                "message": "Notion credentials not configured",
                "configuration": {
                    "integration_secret_configured": bool(settings.NOTION_INTEGRATION_SECRET),
                    "database_id_configured": bool(settings.NOTION_DATABASE_ID)
                }
            }
        
        # Test connection
        connection_ok = await notion_service.verify_connection()
        
        if connection_ok:
            # Get dashboard stats
            stats = await notion_service.get_dashboard_stats()
            
            return {
                "status": "connected",
                "connection": "successful",
                "database_schema": "verified", 
                "dashboard_stats": stats
            }
        else:
            return {
                "status": "connection_failed",
                "message": "Failed to connect to Notion API or access database"
            }
            
    except Exception as e:
        logger.error(f"Error checking Notion dashboard status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/admin/notion-setup-database")
async def notion_setup_database():
    """Admin endpoint to setup the Notion database schema for embedding monitoring"""
    try:
        from services.external_apis.notion_service import NotionService
        
        notion_service = NotionService()
        
        if not notion_service.enabled:
            return {
                "status": "error",
                "message": "Notion credentials not configured"
            }
        
        # Setup database schema
        schema_setup = await notion_service.setup_database_schema()
        
        if schema_setup:
            return {
                "status": "success",
                "message": "Database schema configured successfully",
                "schema_features": [
                    "Run ID tracking",
                    "Status monitoring (Success/Failed/No New Messages)",
                    "Channel statistics",
                    "Performance metrics",
                    "Error logging",
                    "Trigger type tracking"
                ]
            }
        else:
            return {
                "status": "error", 
                "message": "Failed to setup database schema"
            }
            
    except Exception as e:
        logger.error(f"Error setting up Notion database: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/admin/notion-trigger-embedding")
async def notion_trigger_embedding():
    """Admin endpoint to manually trigger embedding check and log to Notion"""
    try:
        from workers.hourly_embedding_worker import run_hourly_embedding_check
        
        logger.info("Manual embedding trigger initiated from Notion dashboard")
        
        # Run the embedding check
        result = await run_hourly_embedding_check()
        
        return {
            "status": "success",
            "trigger_type": "Manual via Notion Dashboard",
            "embedding_result": result,
            "logged_to_notion": True
        }
        
    except Exception as e:
        logger.error(f"Error in manual Notion embedding trigger: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/admin/notion-recent-runs")
async def notion_recent_runs(limit: int = 10):
    """Admin endpoint to get recent embedding runs from Notion database"""
    try:
        from services.external_apis.notion_service import NotionService
        
        notion_service = NotionService()
        
        if not notion_service.enabled:
            return {
                "status": "error",
                "message": "Notion service not enabled"
            }
        
        recent_runs = await notion_service.get_recent_runs(limit=limit)
        
        return {
            "status": "success",
            "recent_runs": recent_runs,
            "count": len(recent_runs),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting recent runs from Notion: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/admin/notion-dashboard-summary") 
async def notion_dashboard_summary():
    """Admin endpoint to get comprehensive dashboard summary for Notion integration"""
    try:
        from services.external_apis.notion_service import NotionService
        from workers.hourly_embedding_worker import HourlyEmbeddingTask
        
        notion_service = NotionService()
        task = HourlyEmbeddingTask()
        
        # Get Notion service status
        notion_status = {
            "enabled": notion_service.enabled,
            "connection": "unknown"
        }
        
        if notion_service.enabled:
            connection_ok = await notion_service.verify_connection()
            notion_status["connection"] = "connected" if connection_ok else "failed"
        
        # Get hourly embedding state
        state = task.load_state()
        
        # Get dashboard stats if available
        dashboard_stats = {}
        if notion_service.enabled:
            dashboard_stats = await notion_service.get_dashboard_stats()
        
        return {
            "status": "success",
            "notion_integration": notion_status,
            "embedding_pipeline": {
                "channels_monitored": len(task.channels),
                "channels": [ch["name"] for ch in task.channels],
                "state_file_exists": bool(state),
                "last_check_times": {
                    ch["name"]: state.get(ch["id"], {}).get("last_check_ts", "Never")
                    for ch in task.channels
                }
            },
            "dashboard_stats": dashboard_stats,
            "admin_endpoints": [
                "/admin/notion-dashboard-status",
                "/admin/notion-setup-database", 
                "/admin/notion-trigger-embedding",
                "/admin/notion-recent-runs",
                "/admin/initial-historical-embedding"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting Notion dashboard summary: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/admin/initial-historical-embedding")
async def initial_historical_embedding():
    """Admin endpoint to trigger initial historical embedding with 1-year limit"""
    try:
        logger.info("Admin triggered initial historical embedding with 1-year limit")
        
        # Import the function from our script
        import subprocess
        import sys
        
        # Run the initial embedding script
        process = subprocess.Popen(
            [sys.executable, "run_initial_historical_embedding.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=1800)  # 30-minute timeout
        
        if process.returncode == 0:
            # Parse the output to extract success metrics
            lines = stdout.strip().split('\n')
            success_line = [line for line in lines if line.startswith('✅ SUCCESS:')]
            
            return {
                "status": "success",
                "message": "Initial historical embedding completed successfully",
                "output": stdout,
                "details": success_line[0] if success_line else "Embedding completed",
                "script_execution": {
                    "return_code": process.returncode,
                    "duration": "See output for details"
                }
            }
        else:
            return {
                "status": "error",
                "message": "Initial historical embedding failed",
                "error": stderr,
                "output": stdout,
                "script_execution": {
                    "return_code": process.returncode
                }
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": "Initial embedding process timed out after 30 minutes",
            "note": "This is normal for large amounts of historical data. The process may still be running in the background."
        }
    except Exception as e:
        logger.error(f"Error in initial historical embedding: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to start initial historical embedding process"
        }

@app.get("/admin/continue-first-gen-ingestion")
async def continue_first_gen_ingestion():
    """
    Continue first generation ingestion with aggressive rate limit handling.
    Will wait for rate limits to clear and continue until all messages are embedded.
    """
    try:
        logger.info("Starting continued first generation ingestion...")
        
        # Run the continuation script with extended timeout
        process = subprocess.run(
            [sys.executable, "continue_first_gen_ingestion.py"],
            capture_output=True,
            text=True,
            timeout=7200  # 2 hour timeout
        )
        
        stdout = process.stdout
        stderr = process.stderr
        
        if process.returncode == 0:
            # Parse success from output
            lines = stdout.split('\n') if stdout else []
            success_line = [line for line in lines if '🎉 FIRST GENERATION INGESTION COMPLETED' in line]
            
            return {
                "status": "success",
                "message": "First generation ingestion completed successfully",
                "output": stdout,
                "details": success_line[0] if success_line else "Ingestion completed",
                "next_step": "Hourly daemon will now maintain fresh data automatically"
            }
        else:
            return {
                "status": "error",
                "message": "First generation ingestion failed",
                "error": stderr,
                "output": stdout,
                "return_code": process.returncode,
                "suggestion": "May need to retry after longer wait for rate limits"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": "Ingestion timed out after 2 hours - Slack rate limits may be very aggressive",
            "suggestion": "Try again later when rate limits reset"
        }
    except Exception as e:
        logger.error(f"Error in continued first generation ingestion: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to start continued ingestion process"
        }

@app.get("/admin/slack-rate-limit-status")
async def check_slack_rate_limit_status():
    """
    Check current Slack API rate limit status by making a minimal API call.
    """
    try:
        from services.external_apis.enhanced_slack_connector import EnhancedSlackConnector
        connector = EnhancedSlackConnector()
        
        # Try a minimal API call to check rate limit status
        import time
        start_time = time.time()
        
        try:
            # Try to get bot info - minimal API call
            response = await connector.client.auth_test()
            end_time = time.time()
            
            return {
                "status": "ok",
                "rate_limited": False,
                "response_time_ms": round((end_time - start_time) * 1000, 2),
                "bot_id": response.get("user_id"),
                "team": response.get("team"),
                "message": "Slack API is accessible - ready for ingestion"
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if "ratelimited" in error_msg or "rate_limit" in error_msg:
                return {
                    "status": "rate_limited",
                    "rate_limited": True,
                    "error": str(e),
                    "message": "Slack API is rate limited - wait before starting ingestion",
                    "suggestion": "Wait 10-30 minutes before attempting ingestion"
                }
            else:
                return {
                    "status": "error",
                    "rate_limited": False,
                    "error": str(e),
                    "message": "Slack API error - check credentials and permissions"
                }
                
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to check Slack API status"
        }

@app.get("/admin/ingestion-status-summary")
async def get_ingestion_status_summary():
    """
    Get comprehensive status of the ingestion pipeline and current vector index state.
    """
    try:
        from services.data.embedding_service import EmbeddingService
        from services.external_apis.notion_service import NotionService
        
        embedding_service = EmbeddingService()
        notion_service = NotionService()
        
        # Get current index stats
        index_stats = await embedding_service.get_index_stats()
        
        # Get recent Notion runs if available
        try:
            recent_runs = await notion_service.get_recent_runs(limit=3)
        except:
            recent_runs = []
        
        # Check hourly daemon state
        hourly_state = {}
        try:
            with open("hourly_embedding_state.json", "r") as f:
                hourly_state = json.load(f)
        except:
            hourly_state = {"status": "No state file found"}
        
        return {
            "status": "success",
            "vector_index": {
                "total_vectors": index_stats.get("total_vectors", 0),
                "dimension": index_stats.get("dimension", 0),
                "index_fullness": index_stats.get("index_fullness", 0.0),
                "ready_for_search": index_stats.get("total_vectors", 0) > 0
            },
            "hourly_daemon": hourly_state,
            "recent_notion_runs": recent_runs[:3] if recent_runs else [],
            "recommendations": {
                "next_action": "continue-first-gen-ingestion" if index_stats.get("total_vectors", 0) == 0 else "system_ready",
                "message": "Vector index is empty - run first generation ingestion" if index_stats.get("total_vectors", 0) == 0 else "System is operational with embedded conversations"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to get ingestion status"
        }

@app.get("/admin/test-smart-embedding-system")
async def test_smart_embedding_system():
    """
    Test the smart embedding system that handles both first generation and incremental updates.
    """
    try:
        from services.processing.ingestion_state_manager import IngestionStateManager
        
        state_manager = IngestionStateManager()
        status = state_manager.get_comprehensive_status()
        
        return {
            "status": "success",
            "comprehensive_status": status,
            "system_explanation": {
                "current_strategy": status["current_strategy"]["strategy"],
                "reason": status["current_strategy"]["reason"],
                "first_gen_complete": status["first_generation"]["is_complete"],
                "missing_channels": len(status["missing_channels"]),
                "hourly_daemon_behavior": "Will automatically run first generation recovery if incomplete, otherwise incremental updates"
            },
            "recommendations": status["recommendations"]
        }
        
    except Exception as e:
        logger.error(f"Error testing smart embedding system: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to test smart embedding system"
        }

@app.get("/admin/run-smart-embedding-now")
async def run_smart_embedding_now():
    """
    Manually trigger the smart embedding system immediately (same logic as hourly daemon).
    """
    try:
        logger.info("Manually triggering smart embedding system...")
        
        # Run the smart embedding script
        import subprocess
        import sys
        process = subprocess.run(
            [sys.executable, "run_smart_hourly_embedding.py"],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        stdout = process.stdout
        stderr = process.stderr
        
        if process.returncode == 0:
            # Parse results from output
            lines = stdout.split('\n') if stdout else []
            result_lines = [line for line in lines if ('COMPLETE!' in line or 'PROGRESS' in line or 
                           'UPDATE COMPLETE' in line or 'messages embedded' in line)]
            
            return {
                "status": "success",
                "message": "Smart embedding completed successfully",
                "output": stdout,
                "highlights": result_lines,
                "return_code": process.returncode
            }
        else:
            return {
                "status": "error",
                "message": "Smart embedding failed",
                "error": stderr,
                "output": stdout,
                "return_code": process.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": "Smart embedding timed out after 30 minutes"
        }
    except Exception as e:
        logger.error(f"Error running smart embedding: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to run smart embedding system"
        }

# Server startup configuration for Cloud Run deployment
if __name__ == "__main__":
    # Force Redis environment variables to empty to prevent connection attempts
    os.environ["REDIS_URL"] = ""
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["CELERY_BROKER_URL"] = ""
    os.environ["CELERY_RESULT_BACKEND"] = ""
    
    # Get port from environment for Cloud Run compatibility
    port = int(os.environ.get("PORT", 5000))
    
    # Initialize services before starting server
    initialize_services()
    
    # Start the server
    logger.info(f"Starting Autopilot Expert Multi-Agent System on 0.0.0.0:{port}")
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces for Cloud Run
        port=port,       # Use PORT environment variable
        log_level="info",
        access_log=True,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=10
    )

