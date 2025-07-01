"""
Hourly embedding worker for incremental message processing.
Checks for new messages every hour and embeds only if new content is found.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from celery import Task
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import settings
from services.embedding_service import EmbeddingService
from services.slack_connector import SlackConnector
from services.data_processor import DataProcessor
from services.notion_service import NotionService
from models.schemas import ProcessedMessage
from celery_app import celery_app

logger = logging.getLogger(__name__)

class HourlyEmbeddingTask(Task):
    """Celery task for hourly embedding checks with smart new message detection."""
    
    def __init__(self):
        self.state_file = "hourly_embedding_state.json"
        self.channels = [
            {
                "id": "C087QKECFKQ",
                "name": "autopilot-design-patterns",
                "is_private": False
            },
            {
                "id": "C08STCP2YUA", 
                "name": "genai-designsys",
                "is_private": True
            }
        ]
    
    def load_state(self) -> Dict[str, Any]:
        """Load last check timestamps from state file."""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No existing state file, starting fresh")
            return {}
    
    def save_state(self, state: Dict[str, Any]):
        """Save current state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    async def check_for_new_messages(self, channel_id: str, channel_name: str, last_check_ts: Optional[str]) -> Dict[str, Any]:
        """Check if there are new messages in a channel since last check."""
        try:
            slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)
            
            # Calculate time window for check
            now = datetime.now()
            if last_check_ts:
                # Check from last timestamp to now
                oldest_ts = last_check_ts
            else:
                # First run: check last 2 hours to be safe
                oldest_ts = str((now - timedelta(hours=2)).timestamp())
            
            # Get messages in time window
            response = slack_client.conversations_history(
                channel=channel_id,
                oldest=oldest_ts,
                limit=100,  # Should be enough for 1 hour of activity
                inclusive=False  # Don't include the exact timestamp we already processed
            )
            
            messages = response.get("messages", [])
            
            # Filter out bot messages and system messages
            human_messages = [
                msg for msg in messages 
                if not msg.get("bot_id") and msg.get("type") == "message" and msg.get("text")
            ]
            
            result = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "total_messages": len(messages),
                "human_messages": len(human_messages),
                "new_messages_found": len(human_messages) > 0,
                "latest_ts": messages[0]["ts"] if messages else last_check_ts,
                "check_window_start": oldest_ts,
                "check_window_end": str(now.timestamp())
            }
            
            logger.info(f"Channel {channel_name}: {len(human_messages)} new messages found")
            return result
            
        except SlackApiError as e:
            if e.response["error"] == "not_in_channel":
                logger.warning(f"Bot not in channel {channel_name}, skipping")
                return {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "error": "not_in_channel",
                    "new_messages_found": False,
                    "latest_ts": last_check_ts
                }
            else:
                logger.error(f"Slack API error for {channel_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error checking {channel_name}: {e}")
            raise
    
    async def process_new_messages(self, channel_id: str, channel_name: str, since_ts: str) -> Dict[str, Any]:
        """Process and embed new messages found in channel."""
        try:
            # Initialize services
            slack_connector = SlackConnector()
            data_processor = DataProcessor()
            embedding_service = EmbeddingService()
            
            # Extract messages since last check
            end_time = datetime.now()
            start_time = datetime.fromtimestamp(float(since_ts))
            
            logger.info(f"Extracting messages from {channel_name} since {start_time}")
            
            raw_messages = await slack_connector.extract_channel_messages(
                channel_id=channel_id,
                start_time=start_time,
                end_time=end_time,
                batch_size=50
            )
            
            if not raw_messages:
                logger.info(f"No messages extracted from {channel_name}")
                return {
                    "channel_name": channel_name,
                    "messages_extracted": 0,
                    "messages_embedded": 0,
                    "status": "no_messages"
                }
            
            # Process messages
            logger.info(f"Processing {len(raw_messages)} messages from {channel_name}")
            processed_messages = await data_processor.process_messages(raw_messages)
            
            # Embed and store
            logger.info(f"Embedding {len(processed_messages)} processed messages")
            embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
            
            result = {
                "channel_name": channel_name,
                "messages_extracted": len(raw_messages),
                "messages_processed": len(processed_messages),
                "messages_embedded": embedded_count,
                "status": "success"
            }
            
            logger.info(f"Successfully embedded {embedded_count} new messages from {channel_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing messages from {channel_name}: {e}")
            return {
                "channel_name": channel_name,
                "messages_extracted": 0,
                "messages_embedded": 0,
                "status": "error",
                "error": str(e)
            }

@celery_app.task(bind=True, base=HourlyEmbeddingTask, name='hourly_embedding_check')
def hourly_embedding_check(self):
    """
    Hourly Celery task that checks for new messages and embeds them if found.
    
    This task:
    1. Checks each configured channel for new messages since last run
    2. If new messages found, processes and embeds them
    3. If no new messages, does nothing (efficient)
    4. Updates state file with latest timestamps
    """
    
    async def run_hourly_check():
        start_time = datetime.now()
        logger.info("Starting hourly embedding check...")
        
        # Load previous state
        state = self.load_state()
        
        results = {
            "check_time": start_time.isoformat(),
            "channels_checked": 0,
            "channels_with_new_messages": 0,
            "total_messages_embedded": 0,
            "channel_results": [],
            "errors": []
        }
        
        for channel_config in self.channels:
            channel_id = channel_config["id"]
            channel_name = channel_config["name"]
            
            try:
                # Get last check timestamp for this channel
                last_check_ts = state.get(channel_id, {}).get("last_check_ts")
                
                # Check for new messages
                check_result = await self.check_for_new_messages(
                    channel_id, channel_name, last_check_ts
                )
                
                results["channels_checked"] += 1
                
                if check_result.get("error"):
                    # Channel access error, skip but don't fail
                    logger.warning(f"Skipping {channel_name}: {check_result['error']}")
                    check_result["action"] = "skipped"
                    results["channel_results"].append(check_result)
                    continue
                
                if check_result["new_messages_found"]:
                    # Process the new messages
                    logger.info(f"Processing {check_result['human_messages']} new messages from {channel_name}")
                    
                    process_result = await self.process_new_messages(
                        channel_id, channel_name, last_check_ts or check_result["check_window_start"]
                    )
                    
                    # Combine results
                    check_result.update(process_result)
                    check_result["action"] = "processed"
                    
                    results["channels_with_new_messages"] += 1
                    results["total_messages_embedded"] += process_result.get("messages_embedded", 0)
                    
                    # Update state with new timestamp
                    if channel_id not in state:
                        state[channel_id] = {}
                    state[channel_id]["last_check_ts"] = check_result["latest_ts"]
                    state[channel_id]["last_successful_check"] = start_time.isoformat()
                    state[channel_id]["total_messages_embedded"] = state[channel_id].get("total_messages_embedded", 0) + process_result.get("messages_embedded", 0)
                
                else:
                    # No new messages
                    logger.info(f"No new messages in {channel_name}")
                    check_result["action"] = "no_new_messages"
                    
                    # Still update last check time even if no messages
                    if channel_id not in state:
                        state[channel_id] = {}
                    state[channel_id]["last_check_ts"] = check_result["latest_ts"]
                    state[channel_id]["last_check_time"] = start_time.isoformat()
                
                results["channel_results"].append(check_result)
                
                # Small delay between channels
                await asyncio.sleep(1.0)
                
            except Exception as e:
                error_msg = f"Error processing {channel_name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                
                results["channel_results"].append({
                    "channel_name": channel_name,
                    "action": "error",
                    "error": str(e)
                })
        
        # Save updated state
        self.save_state(state)
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        results["duration_seconds"] = duration.total_seconds()
        results["end_time"] = end_time.isoformat()
        
        if results["channels_with_new_messages"] > 0:
            logger.info(f"Hourly check complete: {results['total_messages_embedded']} messages embedded from {results['channels_with_new_messages']} channels")
        else:
            logger.info("Hourly check complete: No new messages found in any channel")
        
        return results
    
    try:
        # Run the async function
        return asyncio.run(run_hourly_check())
        
    except Exception as e:
        logger.error(f"Hourly embedding check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "check_time": datetime.now().isoformat()
        }

# Convenience function for manual execution
async def run_hourly_embedding_check():
    """Run hourly embedding check directly (not as Celery task)."""
    async def run_hourly_check():
        task = HourlyEmbeddingTask()
        start_time = datetime.now()
        logger.info("Starting hourly embedding check...")
        
        # Load previous state
        state = task.load_state()
        
        results = {
            "check_time": start_time.isoformat(),
            "channels_checked": 0,
            "channels_with_new_messages": 0,
            "total_messages_embedded": 0,
            "channel_results": [],
            "errors": []
        }
        
        for channel_config in task.channels:
            channel_id = channel_config["id"]
            channel_name = channel_config["name"]
            
            try:
                # Get last check timestamp for this channel
                last_check_ts = state.get(channel_id, {}).get("last_check_ts")
                
                # Check for new messages
                check_result = await task.check_for_new_messages(
                    channel_id, channel_name, last_check_ts
                )
                
                results["channels_checked"] += 1
                
                if check_result.get("error"):
                    # Channel access error, skip but don't fail
                    logger.warning(f"Skipping {channel_name}: {check_result['error']}")
                    check_result["action"] = "skipped"
                    results["channel_results"].append(check_result)
                    continue
                
                if check_result["new_messages_found"]:
                    # Process the new messages
                    logger.info(f"Processing {check_result['human_messages']} new messages from {channel_name}")
                    
                    process_result = await task.process_new_messages(
                        channel_id, channel_name, last_check_ts or check_result["check_window_start"]
                    )
                    
                    # Combine results
                    check_result.update(process_result)
                    check_result["action"] = "processed"
                    
                    results["channels_with_new_messages"] += 1
                    results["total_messages_embedded"] += process_result.get("messages_embedded", 0)
                    
                    # Update state with new timestamp
                    if channel_id not in state:
                        state[channel_id] = {}
                    state[channel_id]["last_check_ts"] = check_result["latest_ts"]
                    state[channel_id]["last_successful_check"] = start_time.isoformat()
                    state[channel_id]["total_messages_embedded"] = state[channel_id].get("total_messages_embedded", 0) + process_result.get("messages_embedded", 0)
                
                else:
                    # No new messages
                    logger.info(f"No new messages in {channel_name}")
                    check_result["action"] = "no_new_messages"
                    
                    # Still update last check time even if no messages
                    if channel_id not in state:
                        state[channel_id] = {}
                    state[channel_id]["last_check_ts"] = check_result["latest_ts"]
                    state[channel_id]["last_check_time"] = start_time.isoformat()
                
                results["channel_results"].append(check_result)
                
                # Small delay between channels
                await asyncio.sleep(1.0)
                
            except Exception as e:
                error_msg = f"Error processing {channel_name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                
                results["channel_results"].append({
                    "channel_name": channel_name,
                    "action": "error",
                    "error": str(e)
                })
        
        # Save updated state
        task.save_state(state)
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        results["duration_seconds"] = duration.total_seconds()
        results["end_time"] = end_time.isoformat()
        
        if results["channels_with_new_messages"] > 0:
            logger.info(f"Hourly check complete: {results['total_messages_embedded']} messages embedded from {results['channels_with_new_messages']} channels")
        else:
            logger.info("Hourly check complete: No new messages found in any channel")
        
        return results
    
    return await run_hourly_check()

if __name__ == "__main__":
    # Direct execution for testing
    print("Running hourly embedding check...")
    result = asyncio.run(run_hourly_embedding_check())
    print(json.dumps(result, indent=2))