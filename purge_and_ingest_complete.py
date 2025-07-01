#!/usr/bin/env python3
"""
Complete purge and ingestion script for first-generation embedding.
Handles rate limits gracefully with automatic retry and recovery.
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

async def purge_vector_index():
    """Purge all vectors from the Pinecone index."""
    logger.info("=== PURGING EXISTING VECTOR INDEX ===")
    
    try:
        embedding_service = EmbeddingService()
        
        # Get current index stats
        stats_before = await embedding_service.get_index_stats()
        logger.info(f"Index stats before purge: {stats_before}")
        
        # Purge all vectors
        result = await embedding_service.purge_all_vectors()
        logger.info(f"✓ Purged vectors: {result}")
        
        # Wait for purge to complete
        logger.info("Waiting for purge to complete...")
        await asyncio.sleep(5)
        
        # Verify purge
        stats_after = await embedding_service.get_index_stats()
        logger.info(f"Index stats after purge: {stats_after}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error purging index: {e}")
        return False

async def wait_for_rate_limit_reset(error_message: str, base_delay: int = 60):
    """Wait for Slack rate limit to reset with exponential backoff."""
    logger.warning(f"Rate limit hit: {error_message}")
    
    # Parse rate limit info if available
    delay = base_delay
    if "retry_after" in error_message.lower():
        # Try to extract retry_after time if provided
        try:
            import re
            match = re.search(r'retry_after["\']?\s*:\s*(\d+)', error_message)
            if match:
                delay = int(match.group(1)) + 5  # Add 5 seconds buffer
        except:
            pass
    
    logger.info(f"Waiting {delay} seconds for rate limit reset...")
    await asyncio.sleep(delay)

async def extract_with_rate_limit_handling(connector, channel_id, channel_name, max_retries=5):
    """Extract messages with automatic rate limit handling and retry."""
    retry_count = 0
    base_delay = 60
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting extraction for {channel_name} (attempt {retry_count + 1}/{max_retries})")
            
            messages = await connector.extract_channel_history_complete(
                channel_id=channel_id,
                channel_name=channel_name,
                max_messages=5000,  # Large limit for complete ingestion
                start_date=None,  # Uses 1-year default
                max_age_days=365
            )
            
            logger.info(f"✓ Successfully extracted {len(messages)} messages from {channel_name}")
            return messages
            
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Max retries reached for {channel_name}")
                    return []
                
                # Wait with exponential backoff
                delay = base_delay * (2 ** (retry_count - 1))
                await wait_for_rate_limit_reset(str(e), delay)
                continue
            else:
                logger.error(f"Non-rate-limit Slack API error for {channel_name}: {e}")
                return []
        except Exception as e:
            logger.error(f"Unexpected error extracting {channel_name}: {e}")
            retry_count += 1
            if retry_count >= max_retries:
                return []
            
            # Wait before retry
            await asyncio.sleep(30)
    
    return []

async def run_complete_first_generation_ingestion():
    """
    Run complete first-generation ingestion with rate limit handling.
    This will be the comprehensive initial embedding of all accessible data.
    """
    start_time = datetime.now()
    logger.info("=== FIRST GENERATION COMPLETE INGESTION ===")
    logger.info("This will purge existing data and ingest all messages from the last year")
    
    try:
        # Step 1: Purge existing index
        logger.info("\nStep 1: Purging existing vector index...")
        purge_success = await purge_vector_index()
        if not purge_success:
            logger.error("Failed to purge index, continuing anyway...")
        
        # Step 2: Initialize services
        logger.info("\nStep 2: Initializing services...")
        connector = EnhancedSlackConnector()
        data_processor = EnhancedDataProcessor()
        embedding_service = EmbeddingService()
        notion_service = NotionService()
        
        # Step 3: Define channels for complete ingestion
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
        
        # Track overall statistics
        total_messages_extracted = 0
        total_messages_embedded = 0
        channels_processed = 0
        channels_failed = 0
        
        logger.info(f"\nStep 3: Processing {len(channels)} channels with complete historical data...")
        
        for i, channel in enumerate(channels):
            try:
                logger.info(f"\n--- Processing Channel {i+1}/{len(channels)}: {channel['name']} ---")
                
                # Extract with rate limit handling
                messages = await extract_with_rate_limit_handling(
                    connector, channel["id"], channel["name"]
                )
                
                if not messages:
                    logger.warning(f"No messages extracted from {channel['name']}")
                    channels_failed += 1
                    continue
                
                total_messages_extracted += len(messages)
                logger.info(f"✓ Extracted {len(messages)} messages from {channel['name']}")
                
                # Process messages for embedding
                processed_messages = await data_processor.process_slack_messages(messages)
                logger.info(f"✓ Processed {len(processed_messages)} messages for embedding")
                
                # Embed and store in batches with rate limit handling
                if processed_messages:
                    embedded_count = 0
                    batch_size = 20  # Conservative batch size
                    
                    for batch_start in range(0, len(processed_messages), batch_size):
                        batch = processed_messages[batch_start:batch_start + batch_size]
                        
                        try:
                            batch_embedded = await embedding_service.embed_and_store_messages(batch)
                            embedded_count += batch_embedded
                            logger.info(f"✓ Embedded batch of {batch_embedded} messages")
                            
                            # Rate limiting between batches
                            if batch_start + batch_size < len(processed_messages):
                                await asyncio.sleep(2)  # 2-second delay between batches
                                
                        except Exception as e:
                            logger.error(f"Error embedding batch: {e}")
                            # Continue with next batch
                            continue
                    
                    total_messages_embedded += embedded_count
                    logger.info(f"✓ Total embedded for {channel['name']}: {embedded_count}/{len(processed_messages)}")
                
                channels_processed += 1
                
                # Rate limiting between channels
                if i < len(channels) - 1:
                    logger.info("Rate limiting delay between channels: 5 seconds...")
                    await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error processing channel {channel['name']}: {e}")
                channels_failed += 1
                continue
        
        # Step 4: Calculate final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"\n=== FIRST GENERATION INGESTION COMPLETED ===")
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Channels processed: {channels_processed}/{len(channels)}")
        logger.info(f"Channels failed: {channels_failed}")
        logger.info(f"Total messages extracted: {total_messages_extracted}")
        logger.info(f"Total messages embedded: {total_messages_embedded}")
        logger.info(f"Embedding rate: {total_messages_embedded/max(duration, 1):.2f} messages/second")
        logger.info(f"Success rate: {total_messages_embedded/max(total_messages_extracted, 1)*100:.1f}%")
        
        # Step 5: Log to Notion dashboard
        run_data = {
            "status": "First Generation Complete Ingestion",
            "channels_checked": channels_processed,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": int(duration),
            "errors": f"Processed {channels_processed}/{len(channels)} channels. Extracted {total_messages_extracted} messages, embedded {total_messages_embedded}. Rate: {total_messages_embedded/max(duration, 1):.2f} msg/sec"
        }
        
        page_id = await notion_service.log_embedding_run(run_data)
        if page_id:
            logger.info(f"✓ Logged to Notion dashboard: {page_id}")
        
        # Step 6: Get final index stats
        final_stats = await embedding_service.get_index_stats()
        logger.info(f"Final index stats: {final_stats}")
        
        return {
            "success": True,
            "channels_processed": channels_processed,
            "channels_failed": channels_failed,
            "messages_extracted": total_messages_extracted,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": duration,
            "success_rate": total_messages_embedded/max(total_messages_extracted, 1)*100,
            "notion_page_id": page_id,
            "final_stats": final_stats
        }
        
    except Exception as e:
        logger.error(f"Complete ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = asyncio.run(run_complete_first_generation_ingestion())
    
    if result["success"]:
        print(f"\n🎉 FIRST GENERATION INGESTION COMPLETED SUCCESSFULLY!")
        print(f"   📊 {result['messages_embedded']} messages embedded")
        print(f"   📁 {result['channels_processed']} channels processed")
        print(f"   ⏱️  {result['duration_seconds']:.1f} seconds duration")
        print(f"   ✅ {result['success_rate']:.1f}% success rate")
        if result.get('notion_page_id'):
            print(f"   📝 Logged to Notion: {result['notion_page_id']}")
        print(f"\n🔄 Hourly daemon will now maintain fresh data automatically")
    else:
        print(f"\n❌ INGESTION FAILED: {result['error']}")