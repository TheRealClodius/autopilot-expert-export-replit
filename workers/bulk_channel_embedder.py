"""
Background worker for bulk channel message embedding.
Handles rate limiting, pagination, and incremental processing.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from celery import Task

from config import settings
from services.embedding_service import EmbeddingService
from services.data_processor import DataProcessor
from models.schemas import ProcessedMessage
from celery_app import celery_app

logger = logging.getLogger(__name__)

@dataclass
class ChannelConfig:
    """Configuration for a channel to be embedded."""
    id: str
    name: str
    is_private: bool = False
    last_embedded_ts: Optional[str] = None
    total_messages_embedded: int = 0

@dataclass
class ProcessingStats:
    """Statistics for bulk processing session."""
    channels_processed: int = 0
    total_messages_extracted: int = 0
    total_messages_embedded: int = 0
    errors: List[str] = None
    start_time: datetime = None
    end_time: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.start_time is None:
            self.start_time = datetime.now()

class BulkChannelEmbedder:
    """
    Handles bulk embedding of channel messages with intelligent rate limiting.
    """
    
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.embedding_service = EmbeddingService()
        self.data_processor = DataProcessor()
        
        # Rate limiting configuration
        self.base_delay = 2.0  # Base delay between API calls
        self.max_delay = 30.0  # Maximum delay on rate limit
        self.batch_size = 100  # Messages per API call
        self.embedding_batch_size = 20  # Messages per embedding batch
        
        # Channels to process
        self.channels = [
            ChannelConfig(
                id="C087QKECFKQ",
                name="autopilot-design-patterns",
                is_private=False
            ),
            ChannelConfig(
                id="C08STCP2YUA", 
                name="genai-designsys",
                is_private=True
            )
        ]
    
    async def smart_rate_limit_delay(self, api_call_count: int = 0, last_error: Optional[str] = None):
        """
        Intelligent rate limiting based on API usage patterns.
        """
        if last_error and "ratelimited" in last_error.lower():
            delay = min(self.max_delay, self.base_delay * (2 ** min(api_call_count, 4)))
            logger.warning(f"Rate limited, waiting {delay:.1f}s")
            await asyncio.sleep(delay)
        else:
            # Standard delay to stay under limits
            delay = self.base_delay + (api_call_count * 0.1)
            await asyncio.sleep(min(delay, 5.0))
    
    async def get_channel_history_batch(
        self, 
        channel_id: str, 
        cursor: Optional[str] = None,
        oldest: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a batch of channel history with error handling.
        """
        try:
            params = {
                "channel": channel_id,
                "limit": self.batch_size,
                "inclusive": True
            }
            
            if cursor:
                params["cursor"] = cursor
            if oldest:
                params["oldest"] = oldest
            
            response = self.client.conversations_history(**params)
            
            if response["ok"]:
                return {
                    "messages": response["messages"],
                    "has_more": response.get("has_more", False),
                    "next_cursor": response.get("response_metadata", {}).get("next_cursor"),
                    "error": None
                }
            else:
                return {
                    "messages": [],
                    "has_more": False,
                    "next_cursor": None,
                    "error": response.get("error", "unknown")
                }
                
        except SlackApiError as e:
            error_msg = str(e)
            logger.error(f"Slack API error in channel {channel_id}: {error_msg}")
            return {
                "messages": [],
                "has_more": False,
                "next_cursor": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Error getting history for {channel_id}: {error_msg}")
            return {
                "messages": [],
                "has_more": False,
                "next_cursor": None,
                "error": error_msg
            }
    
    async def extract_all_channel_messages(
        self, 
        channel_config: ChannelConfig,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract ALL messages from a channel with pagination and rate limiting.
        """
        logger.info(f"Starting full extraction for {channel_config.name} ({channel_config.id})")
        
        all_messages = []
        cursor = None
        api_call_count = 0
        last_error = None
        
        # Start from last embedded message if available
        oldest_ts = channel_config.last_embedded_ts
        
        while True:
            # Rate limiting delay
            await self.smart_rate_limit_delay(api_call_count, last_error)
            
            # Get batch
            batch_result = await self.get_channel_history_batch(
                channel_config.id, 
                cursor=cursor,
                oldest=oldest_ts
            )
            
            api_call_count += 1
            
            # Handle errors
            if batch_result["error"]:
                last_error = batch_result["error"]
                
                if "ratelimited" in last_error.lower():
                    logger.warning(f"Rate limited on {channel_config.name}, backing off...")
                    continue
                elif "not_in_channel" in last_error.lower():
                    logger.error(f"Bot not in channel {channel_config.name}")
                    break
                else:
                    logger.error(f"API error for {channel_config.name}: {last_error}")
                    break
            
            # Process messages
            messages = batch_result["messages"]
            
            if not messages:
                logger.info(f"No more messages in {channel_config.name}")
                break
            
            # Filter out already processed messages
            new_messages = []
            for msg in messages:
                if oldest_ts and msg.get("ts", "0") <= oldest_ts:
                    continue
                new_messages.append(msg)
            
            all_messages.extend(new_messages)
            
            logger.info(f"Extracted batch of {len(new_messages)} messages from {channel_config.name} (total: {len(all_messages)})")
            
            # Check limits
            if max_messages and len(all_messages) >= max_messages:
                logger.info(f"Reached max message limit ({max_messages}) for {channel_config.name}")
                all_messages = all_messages[:max_messages]
                break
            
            # Check if more pages available
            if not batch_result["has_more"] or not batch_result["next_cursor"]:
                logger.info(f"Reached end of {channel_config.name} history")
                break
            
            cursor = batch_result["next_cursor"]
            
            # Safety check - prevent infinite loops
            if api_call_count > 1000:  # Reasonable limit for very large channels
                logger.warning(f"Hit API call limit for {channel_config.name}")
                break
        
        logger.info(f"Completed extraction for {channel_config.name}: {len(all_messages)} total messages")
        return all_messages
    
    async def process_and_embed_messages(
        self, 
        messages: List[Dict[str, Any]], 
        channel_config: ChannelConfig
    ) -> int:
        """
        Process and embed messages in batches.
        """
        if not messages:
            return 0
        
        logger.info(f"Processing {len(messages)} messages for {channel_config.name}")
        
        # Convert to ProcessedMessage format
        processed_messages = []
        
        for msg in messages:
            if not msg.get("text") or not msg["text"].strip():
                continue
                
            try:
                processed_msg = ProcessedMessage(
                    text=msg["text"],
                    user_id=msg.get("user", "unknown"),
                    user_name=msg.get("user", "unknown"),
                    user_first_name=msg.get("user", "unknown"),
                    user_display_name=msg.get("user", "unknown"),
                    user_title="Unknown",
                    user_department="Unknown",
                    channel_id=channel_config.id,
                    channel_name=channel_config.name,
                    message_ts=msg["ts"],
                    thread_ts=msg.get("thread_ts"),
                    is_dm=False
                )
                processed_messages.append(processed_msg)
                
            except Exception as e:
                logger.warning(f"Error processing message in {channel_config.name}: {e}")
                continue
        
        if not processed_messages:
            logger.warning(f"No valid messages to embed for {channel_config.name}")
            return 0
        
        logger.info(f"Embedding {len(processed_messages)} valid messages for {channel_config.name}")
        
        # Embed in batches to manage memory and API limits
        total_embedded = 0
        
        for i in range(0, len(processed_messages), self.embedding_batch_size):
            batch = processed_messages[i:i + self.embedding_batch_size]
            
            try:
                # Add delay between embedding batches
                if i > 0:
                    await asyncio.sleep(3.0)
                
                embedded_count = await self.embedding_service.embed_and_store_messages(batch)
                total_embedded += embedded_count
                
                logger.info(f"Embedded batch {i//self.embedding_batch_size + 1}: {embedded_count}/{len(batch)} messages")
                
            except Exception as e:
                logger.error(f"Error embedding batch for {channel_config.name}: {e}")
                continue
        
        # Update channel config
        if processed_messages:
            latest_ts = max(msg.message_ts for msg in processed_messages)
            channel_config.last_embedded_ts = latest_ts
            channel_config.total_messages_embedded += total_embedded
        
        logger.info(f"Completed embedding for {channel_config.name}: {total_embedded} messages embedded")
        return total_embedded
    
    async def process_all_channels(self, max_messages_per_channel: Optional[int] = None) -> ProcessingStats:
        """
        Process all configured channels.
        """
        stats = ProcessingStats()
        
        logger.info(f"Starting bulk channel embedding for {len(self.channels)} channels")
        
        for channel_config in self.channels:
            try:
                logger.info(f"Processing channel: {channel_config.name}")
                
                # Extract messages
                messages = await self.extract_all_channel_messages(
                    channel_config, 
                    max_messages=max_messages_per_channel
                )
                
                stats.total_messages_extracted += len(messages)
                
                if messages:
                    # Process and embed
                    embedded_count = await self.process_and_embed_messages(messages, channel_config)
                    stats.total_messages_embedded += embedded_count
                    
                    logger.info(f"Channel {channel_config.name} complete: {embedded_count} embedded")
                else:
                    logger.warning(f"No messages extracted from {channel_config.name}")
                
                stats.channels_processed += 1
                
                # Delay between channels
                await asyncio.sleep(5.0)
                
            except Exception as e:
                error_msg = f"Error processing {channel_config.name}: {str(e)}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
                continue
        
        stats.end_time = datetime.now()
        duration = stats.end_time - stats.start_time
        
        logger.info(f"Bulk embedding complete in {duration.total_seconds():.1f}s")
        logger.info(f"Channels processed: {stats.channels_processed}")
        logger.info(f"Messages extracted: {stats.total_messages_extracted}")
        logger.info(f"Messages embedded: {stats.total_messages_embedded}")
        
        if stats.errors:
            logger.warning(f"Errors encountered: {len(stats.errors)}")
            for error in stats.errors:
                logger.warning(f"  {error}")
        
        return stats

@celery_app.task(bind=True)
def bulk_embed_channels_task(self, max_messages_per_channel: Optional[int] = None):
    """
    Celery task for bulk channel embedding.
    """
    async def run_embedding():
        embedder = BulkChannelEmbedder()
        return await embedder.process_all_channels(max_messages_per_channel)
    
    try:
        # Run the async function
        stats = asyncio.run(run_embedding())
        
        return {
            "status": "success",
            "channels_processed": stats.channels_processed,
            "total_messages_extracted": stats.total_messages_extracted,
            "total_messages_embedded": stats.total_messages_embedded,
            "duration_seconds": (stats.end_time - stats.start_time).total_seconds(),
            "errors": stats.errors
        }
        
    except Exception as e:
        logger.error(f"Bulk embedding task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "channels_processed": 0,
            "total_messages_extracted": 0,
            "total_messages_embedded": 0
        }

# Standalone function for direct execution
async def run_bulk_embedding(max_messages_per_channel: Optional[int] = None):
    """
    Run bulk embedding directly (not as Celery task).
    """
    embedder = BulkChannelEmbedder()
    return await embedder.process_all_channels(max_messages_per_channel)

if __name__ == "__main__":
    # Direct execution
    import sys
    
    max_messages = None
    if len(sys.argv) > 1:
        try:
            max_messages = int(sys.argv[1])
        except ValueError:
            print("Usage: python bulk_channel_embedder.py [max_messages_per_channel]")
            sys.exit(1)
    
    print("Starting bulk channel embedding...")
    
    stats = asyncio.run(run_bulk_embedding(max_messages))
    
    print(f"\n=== BULK EMBEDDING COMPLETE ===")
    print(f"Channels processed: {stats.channels_processed}")
    print(f"Messages extracted: {stats.total_messages_extracted}")
    print(f"Messages embedded: {stats.total_messages_embedded}")
    print(f"Duration: {(stats.end_time - stats.start_time).total_seconds():.1f}s")
    
    if stats.errors:
        print(f"\nErrors ({len(stats.errors)}):")
        for error in stats.errors:
            print(f"  - {error}")
    else:
        print("\n✅ No errors encountered")