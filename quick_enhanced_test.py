#!/usr/bin/env python3
"""
Quick test of enhanced Slack extraction system.
Tests the improvements in thread relationships and data quality.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from services.enhanced_slack_connector import EnhancedSlackConnector
from services.enhanced_data_processor import EnhancedDataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def quick_test():
    """Quick test of enhanced extraction system."""
    logger.info("=== Quick Enhanced Extraction Test ===")
    
    try:
        # Initialize enhanced services
        connector = EnhancedSlackConnector()
        processor = EnhancedDataProcessor()
        
        # Test single channel with limited messages
        channel_id = "C087QKECFKQ"  # autopilot-design-patterns
        channel_name = "autopilot-design-patterns"
        
        logger.info(f"Testing enhanced extraction from {channel_name}...")
        
        # Extract recent messages (last 24 hours, max 5 messages)
        start_date = datetime.now() - timedelta(days=1)
        messages = await connector.extract_channel_history_complete(
            channel_id=channel_id,
            channel_name=channel_name,
            max_messages=5,
            start_date=start_date
        )
        
        logger.info(f"✓ Extracted {len(messages)} messages")
        
        # Show thread relationships
        thread_count = len([m for m in messages if m.thread_ts and not m.is_thread_reply])
        reply_count = len([m for m in messages if m.is_thread_reply])
        
        logger.info(f"✓ Found {thread_count} threads with {reply_count} replies")
        
        # Process messages
        processed_messages = await processor.process_slack_messages(messages)
        
        logger.info(f"✓ Processed {len(processed_messages)} messages for embedding")
        
        # Show data quality improvements
        if processed_messages:
            sample = processed_messages[0]
            logger.info("✓ Sample processed message structure:")
            logger.info(f"  - ID: {sample.get('id', 'N/A')}")
            logger.info(f"  - User: {sample.get('metadata', {}).get('user_name', 'N/A')}")
            logger.info(f"  - Channel: {sample.get('metadata', {}).get('channel_name', 'N/A')}")
            logger.info(f"  - Thread Position: {sample.get('metadata', {}).get('thread_position', 'N/A')}")
            logger.info(f"  - Content Length: {len(sample.get('content', ''))}")
        
        # Get summary
        summary = connector.get_message_summary(messages)
        logger.info(f"✓ Extraction Summary: {summary}")
        
        processing_summary = processor.get_processing_summary(processed_messages)
        logger.info(f"✓ Processing Summary: {processing_summary}")
        
        logger.info("=== Enhanced extraction test completed successfully! ===")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(quick_test())