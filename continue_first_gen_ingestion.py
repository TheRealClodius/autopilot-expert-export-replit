#!/usr/bin/env python3
"""
Continue first generation ingestion with aggressive rate limit handling.
This script will wait for rate limits and continue until all messages are processed.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from services.enhanced_slack_connector import EnhancedSlackConnector
from services.enhanced_data_processor import EnhancedDataProcessor
from services.embedding_service import EmbeddingService
from services.notion_service import NotionService
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def continue_first_generation_ingestion():
    """Continue first generation ingestion with aggressive rate limit handling."""
    start_time = datetime.now()
    logger.info("=== CONTINUING FIRST GENERATION INGESTION ===")
    logger.info("Will wait for rate limits and continue until all messages are embedded")
    
    try:
        # Initialize services
        connector = EnhancedSlackConnector()
        data_processor = EnhancedDataProcessor()
        embedding_service = EmbeddingService()
        notion_service = NotionService()
        
        # Get current index stats
        stats = await embedding_service.get_index_stats()
        logger.info(f"Current index stats: {stats}")
        
        # Define channels
        channels = [
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
        
        total_messages_extracted = 0
        total_messages_embedded = 0
        channels_processed = 0
        
        for i, channel in enumerate(channels):
            logger.info(f"\n--- Processing Channel {i+1}/{len(channels)}: {channel['name']} ---")
            
            # Try extraction with exponential backoff for rate limits
            messages = []
            retry_count = 0
            max_retries = 10
            
            while retry_count < max_retries and not messages:
                try:
                    logger.info(f"Extraction attempt {retry_count + 1}/{max_retries} for {channel['name']}")
                    
                    # Extract with rate limit friendly settings
                    messages = await connector.extract_channel_history_complete(
                        channel_id=channel["id"],
                        channel_name=channel["name"],
                        max_messages=1000,  # More conservative limit
                        start_date=None,
                        max_age_days=365
                    )
                    
                    if messages:
                        logger.info(f"✓ Successfully extracted {len(messages)} messages from {channel['name']}")
                        break
                    
                except SlackApiError as e:
                    if e.response['error'] == 'ratelimited':
                        retry_count += 1
                        wait_time = min(300, 60 * (2 ** retry_count))  # Exponential backoff, max 5 minutes
                        logger.warning(f"Rate limited on {channel['name']}. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Slack API error for {channel['name']}: {e}")
                        break
                except Exception as e:
                    logger.error(f"Error extracting {channel['name']}: {e}")
                    retry_count += 1
                    await asyncio.sleep(30)
            
            if not messages:
                logger.warning(f"Could not extract messages from {channel['name']} after {max_retries} attempts")
                continue
            
            total_messages_extracted += len(messages)
            
            # Process messages
            processed_messages = await data_processor.process_slack_messages(messages)
            logger.info(f"✓ Processed {len(processed_messages)} messages for embedding")
            
            # Embed with conservative batching and rate limiting
            if processed_messages:
                embedded_count = 0
                batch_size = 10  # Very conservative batch size
                
                for batch_start in range(0, len(processed_messages), batch_size):
                    batch = processed_messages[batch_start:batch_start + batch_size]
                    
                    try:
                        batch_embedded = await embedding_service.embed_and_store_messages(batch)
                        embedded_count += batch_embedded
                        logger.info(f"✓ Embedded batch: {batch_embedded}/{len(batch)} messages")
                        
                        # Aggressive rate limiting between batches
                        if batch_start + batch_size < len(processed_messages):
                            await asyncio.sleep(5)  # 5-second delay between batches
                            
                    except Exception as e:
                        logger.error(f"Error embedding batch: {e}")
                        # Wait longer on embedding errors
                        await asyncio.sleep(10)
                        continue
                
                total_messages_embedded += embedded_count
                logger.info(f"✓ Channel complete: {embedded_count}/{len(processed_messages)} messages embedded")
            
            channels_processed += 1
            
            # Long delay between channels to avoid rate limits
            if i < len(channels) - 1:
                logger.info("Rate limiting delay between channels: 10 seconds...")
                await asyncio.sleep(10)
        
        # Final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Get final index stats
        final_stats = await embedding_service.get_index_stats()
        
        logger.info(f"\n=== FIRST GENERATION INGESTION COMPLETED ===")
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Channels processed: {channels_processed}/{len(channels)}")
        logger.info(f"Total messages extracted: {total_messages_extracted}")
        logger.info(f"Total messages embedded: {total_messages_embedded}")
        logger.info(f"Final index stats: {final_stats}")
        
        if total_messages_embedded > 0:
            logger.info(f"Embedding rate: {total_messages_embedded/max(duration, 1):.2f} messages/second")
            logger.info(f"Success rate: {total_messages_embedded/max(total_messages_extracted, 1)*100:.1f}%")
        
        # Log to Notion
        run_data = {
            "status": "First Generation Ingestion Complete",
            "channels_checked": channels_processed,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": int(duration),
            "errors": f"Completed with rate limit handling. Extracted {total_messages_extracted}, embedded {total_messages_embedded}"
        }
        
        page_id = await notion_service.log_embedding_run(run_data)
        if page_id:
            logger.info(f"✓ Logged to Notion: {page_id}")
        
        return {
            "success": True,
            "channels_processed": channels_processed,
            "messages_extracted": total_messages_extracted,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": duration,
            "final_stats": final_stats
        }
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(continue_first_generation_ingestion())
    
    if result["success"]:
        print(f"\n🎉 FIRST GENERATION INGESTION COMPLETED!")
        print(f"   📊 {result['messages_embedded']} messages embedded")
        print(f"   📁 {result['channels_processed']} channels processed")
        print(f"   ⏱️  {result['duration_seconds']:.1f} seconds")
        print(f"   📈 Index now contains vectors for searchable conversations")
    else:
        print(f"\n❌ INGESTION FAILED: {result['error']}")