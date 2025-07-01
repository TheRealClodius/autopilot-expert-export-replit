#!/usr/bin/env python3
"""
Initial historical embedding script with 1-year message limit.
Performs complete historical data ingestion for the first time with proper rate limiting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from services.enhanced_slack_connector import EnhancedSlackConnector
from services.enhanced_data_processor import EnhancedDataProcessor
from services.embedding_service import EmbeddingService
from services.notion_service import NotionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_initial_historical_embedding():
    """
    Run initial historical embedding with 1-year message limit.
    This is designed for the first-time complete data ingestion.
    """
    logger.info("=== INITIAL HISTORICAL EMBEDDING WITH 1-YEAR LIMIT ===")
    
    try:
        # Initialize services
        slack_connector = EnhancedSlackConnector()
        data_processor = EnhancedDataProcessor()
        embedding_service = EmbeddingService()
        notion_service = NotionService()
        
        # Define channels for embedding
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
        start_time = datetime.now()
        
        logger.info(f"Starting initial embedding for {len(channels)} channels...")
        logger.info("1-YEAR MESSAGE LIMIT APPLIED - Only messages from last 365 days will be processed")
        
        for channel in channels:
            try:
                logger.info(f"\n--- Processing Channel: {channel['name']} ---")
                
                # Extract complete history with 1-year limit (default)
                messages = await slack_connector.extract_channel_history_complete(
                    channel_id=channel["id"],
                    channel_name=channel["name"],
                    max_messages=2000,  # Generous limit for initial embedding
                    start_date=None,  # Uses default 1-year lookback
                    max_age_days=365  # Explicit 1-year limit
                )
                
                logger.info(f"✓ Extracted {len(messages)} messages from {channel['name']}")
                total_messages_extracted += len(messages)
                
                if len(messages) > 0:
                    # Process messages for embedding
                    processed_messages = await data_processor.process_slack_messages(messages)
                    
                    logger.info(f"✓ Processed {len(processed_messages)} messages for embedding")
                    
                    # Embed and store in batches
                    if processed_messages:
                        embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
                        logger.info(f"✓ Embedded {embedded_count} messages")
                        total_messages_embedded += embedded_count
                    
                    # Show extraction summary
                    extraction_summary = slack_connector.get_message_summary(messages)
                    processing_summary = data_processor.get_processing_summary(processed_messages)
                    
                    logger.info(f"Channel Summary - Extraction: {extraction_summary}")
                    logger.info(f"Channel Summary - Processing: {processing_summary}")
                
                channels_processed += 1
                
                # Rate limiting between channels
                if channels_processed < len(channels):
                    logger.info("Rate limiting delay between channels: 3 seconds...")
                    await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error processing channel {channel['name']}: {e}")
                continue
        
        # Calculate final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"\n=== INITIAL HISTORICAL EMBEDDING COMPLETED ===")
        logger.info(f"Channels processed: {channels_processed}/{len(channels)}")
        logger.info(f"Total messages extracted: {total_messages_extracted}")
        logger.info(f"Total messages embedded: {total_messages_embedded}")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Embedding rate: {total_messages_embedded/max(duration, 1):.2f} messages/second")
        
        # Log to Notion dashboard
        run_data = {
            "status": "Initial Historical Embedding Complete",
            "channels_checked": channels_processed,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": int(duration),
            "errors": f"1-year limit applied. Extracted {total_messages_extracted} messages, embedded {total_messages_embedded}. Processing rate: {total_messages_embedded/max(duration, 1):.2f} msg/sec"
        }
        
        page_id = await notion_service.log_embedding_run(run_data)
        if page_id:
            logger.info(f"✓ Logged to Notion dashboard: {page_id}")
        
        # Get final index stats
        index_stats = await embedding_service.get_index_stats()
        logger.info(f"Final index stats: {index_stats}")
        
        return {
            "success": True,
            "channels_processed": channels_processed,
            "messages_extracted": total_messages_extracted,
            "messages_embedded": total_messages_embedded,
            "duration_seconds": duration,
            "notion_page_id": page_id
        }
        
    except Exception as e:
        logger.error(f"Initial historical embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = asyncio.run(run_initial_historical_embedding())
    
    if result["success"]:
        print(f"\n✅ SUCCESS: Initial historical embedding completed!")
        print(f"   - {result['messages_embedded']} messages embedded")
        print(f"   - {result['channels_processed']} channels processed")
        print(f"   - {result['duration_seconds']:.1f} seconds duration")
        if result.get('notion_page_id'):
            print(f"   - Logged to Notion: {result['notion_page_id']}")
    else:
        print(f"\n❌ FAILED: {result['error']}")