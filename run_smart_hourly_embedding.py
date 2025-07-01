#!/usr/bin/env python3
"""
Smart hourly embedding that can handle both incremental updates and first generation recovery.
This replaces the simple hourly daemon with intelligent state-aware processing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

from services.ingestion_state_manager import IngestionStateManager
from services.enhanced_slack_connector import EnhancedSlackConnector
from services.enhanced_data_processor import EnhancedDataProcessor
from services.embedding_service import EmbeddingService
from services.notion_service import NotionService
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_smart_hourly_embedding():
    """
    Smart hourly embedding that automatically determines whether to run:
    1. First generation recovery (if incomplete)
    2. Normal incremental updates (if first gen complete)
    """
    start_time = datetime.now()
    logger.info("=== SMART HOURLY EMBEDDING CHECK ===")
    
    try:
        # Initialize services
        state_manager = IngestionStateManager()
        connector = EnhancedSlackConnector()
        data_processor = EnhancedDataProcessor()
        embedding_service = EmbeddingService()
        notion_service = NotionService()
        
        # Determine strategy based on current state
        strategy = state_manager.should_hourly_daemon_run_first_gen()
        logger.info(f"Strategy: {strategy['strategy']} - {strategy['reason']}")
        
        total_messages_embedded = 0
        channels_processed = 0
        errors = []
        
        if strategy["strategy"] == "first_generation_recovery":
            logger.info("🔄 FIRST GENERATION RECOVERY MODE")
            logger.info(f"Processing {len(strategy['channels'])} channels that need historical ingestion")
            
            # Run first generation logic for missing channels
            for channel in strategy["channels"]:
                try:
                    logger.info(f"\n--- First Gen Recovery: {channel['name']} ---")
                    
                    # Extract with rate limit handling (conservative approach)
                    messages = []
                    retry_count = 0
                    max_retries = 3  # Conservative for hourly runs
                    
                    while retry_count < max_retries and not messages:
                        try:
                            messages = await connector.extract_channel_history_complete(
                                channel_id=channel["id"],
                                channel_name=channel["name"],
                                max_messages=500,  # Conservative limit for hourly
                                start_date=None,  # Use 1-year default
                                max_age_days=365
                            )
                            
                            if messages:
                                logger.info(f"✓ Extracted {len(messages)} historical messages")
                                break
                                
                        except SlackApiError as e:
                            if e.response['error'] == 'ratelimited':
                                retry_count += 1
                                if retry_count >= max_retries:
                                    logger.warning(f"Rate limited on {channel['name']}, will retry next hour")
                                    break
                                
                                wait_time = 30 * retry_count  # 30s, 60s, 90s
                                logger.info(f"Rate limited, waiting {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"Slack API error: {e}")
                                break
                        except Exception as e:
                            logger.error(f"Error extracting {channel['name']}: {e}")
                            retry_count += 1
                            if retry_count >= max_retries:
                                break
                            await asyncio.sleep(10)
                    
                    if messages:
                        # Process and embed
                        processed_messages = await data_processor.process_slack_messages(messages)
                        
                        if processed_messages:
                            embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
                            total_messages_embedded += embedded_count
                            
                            # Update first generation state
                            latest_ts = max(msg.timestamp for msg in processed_messages) if processed_messages else "0"
                            state_manager.update_first_generation_progress(
                                channel["id"], 
                                channel["name"],
                                embedded_count,
                                latest_ts,
                                len(messages),
                                "completed" if embedded_count == len(processed_messages) else "partial"
                            )
                            
                            logger.info(f"✓ Embedded {embedded_count}/{len(processed_messages)} messages")
                    
                    channels_processed += 1
                    
                    # Rate limiting between channels
                    if channels_processed < len(strategy["channels"]):
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    error_msg = f"Error processing {channel['name']}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            # Check if first generation is now complete
            if state_manager.is_first_generation_complete():
                state_manager.mark_first_generation_complete()
                logger.info("🎉 FIRST GENERATION INGESTION NOW COMPLETE!")
        
        elif strategy["strategy"] == "incremental":
            logger.info("📈 INCREMENTAL UPDATE MODE")
            logger.info("Checking for new messages since last run")
            
            # Run normal incremental logic
            hourly_state = state_manager.get_hourly_state()
            
            for channel in strategy["channels"]:
                try:
                    logger.info(f"\n--- Incremental Check: {channel['name']} ---")
                    
                    # Get last timestamp for this channel
                    channel_state = hourly_state.get("channels", {}).get(channel["id"], {})
                    last_ts = channel_state.get("latest_timestamp", "0")
                    
                    # Check for new messages
                    now = datetime.now()
                    oldest_ts = str((now - timedelta(hours=2)).timestamp())  # 2-hour window
                    
                    try:
                        response = await connector.client.conversations_history(
                            channel=channel["id"],
                            oldest=max(last_ts, oldest_ts),
                            limit=100,
                            inclusive=False
                        )
                        
                        messages = response.get("messages", [])
                        human_messages = [
                            msg for msg in messages 
                            if not msg.get("bot_id") and msg.get("type") == "message" and msg.get("text")
                        ]
                        
                        if human_messages:
                            logger.info(f"Found {len(human_messages)} new messages")
                            
                            # Process and embed new messages
                            processed_messages = await data_processor.process_slack_messages(human_messages)
                            
                            if processed_messages:
                                embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
                                total_messages_embedded += embedded_count
                                
                                # Update hourly state
                                latest_ts = messages[0]["ts"] if messages else last_ts
                                state_manager.update_hourly_state(channel["id"], latest_ts, embedded_count)
                                
                                logger.info(f"✓ Embedded {embedded_count} new messages")
                        else:
                            logger.info("No new messages found")
                        
                    except SlackApiError as e:
                        if e.response["error"] == "ratelimited":
                            logger.warning(f"Rate limited checking {channel['name']}, will retry next hour")
                        else:
                            logger.error(f"Slack API error for {channel['name']}: {e}")
                    
                    channels_processed += 1
                    
                except Exception as e:
                    error_msg = f"Error checking {channel['name']}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
        
        # Calculate final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Determine status
        if strategy["strategy"] == "first_generation_recovery":
            if state_manager.is_first_generation_complete():
                status = "First Generation Complete"
            elif total_messages_embedded > 0:
                status = "First Generation Progress"
            else:
                status = "First Generation Blocked (Rate Limited)"
        else:
            if total_messages_embedded > 0:
                status = "New Messages Embedded"
            else:
                status = "No New Messages"
        
        logger.info(f"\n=== SMART HOURLY EMBEDDING COMPLETED ===")
        logger.info(f"Strategy: {strategy['strategy']}")
        logger.info(f"Status: {status}")
        logger.info(f"Channels processed: {channels_processed}")
        logger.info(f"Messages embedded: {total_messages_embedded}")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Errors: {len(errors)}")
        
        # Log to Notion
        run_data = {
            "status": status,
            "channels_checked": channels_processed,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": int(duration),
            "errors": f"Strategy: {strategy['strategy']}. " + ("; ".join(errors) if errors else "No errors")
        }
        
        page_id = await notion_service.log_embedding_run(run_data)
        if page_id:
            logger.info(f"✓ Logged to Notion: {page_id}")
        
        return {
            "success": True,
            "strategy": strategy["strategy"],
            "status": status,
            "channels_processed": channels_processed,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": duration,
            "first_gen_complete": state_manager.is_first_generation_complete(),
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Smart hourly embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = asyncio.run(run_smart_hourly_embedding())
    
    if result["success"]:
        if result["strategy"] == "first_generation_recovery":
            if result["first_gen_complete"]:
                print(f"\n🎉 FIRST GENERATION COMPLETE!")
                print(f"   📊 {result['messages_embedded']} messages embedded")
                print(f"   🔄 System now ready for incremental updates")
            else:
                print(f"\n🔄 FIRST GENERATION PROGRESS")
                print(f"   📊 {result['messages_embedded']} messages embedded")
                print(f"   ⏳ Will continue next hour if rate limits clear")
        else:
            print(f"\n📈 INCREMENTAL UPDATE COMPLETE")
            print(f"   📊 {result['messages_embedded']} new messages embedded")
        
        print(f"   📁 {result['channels_processed']} channels processed")
        print(f"   ⏱️  {result['duration_seconds']:.1f} seconds")
    else:
        print(f"\n❌ SMART EMBEDDING FAILED: {result['error']}")