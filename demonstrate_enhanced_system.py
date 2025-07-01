#!/usr/bin/env python3
"""
Demonstrate the enhanced Slack extraction system improvements.
Shows the data structure fixes and thread relationship handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from services.enhanced_slack_connector import EnhancedSlackConnector
from services.enhanced_data_processor import EnhancedDataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstrate_enhancements():
    """Demonstrate the enhanced extraction system improvements."""
    logger.info("=== ENHANCED SLACK EXTRACTION SYSTEM DEMONSTRATION ===")
    
    try:
        # Initialize enhanced services
        connector = EnhancedSlackConnector()
        processor = EnhancedDataProcessor()
        
        # Test with autopilot-design-patterns channel
        channel_id = "C087QKECFKQ"
        channel_name = "autopilot-design-patterns"
        
        logger.info(f"Testing enhanced extraction from {channel_name}...")
        
        # Extract recent messages (last 30 days to ensure we get data)
        start_date = datetime.now() - timedelta(days=30)
        messages = await connector.extract_channel_history_complete(
            channel_id=channel_id,
            channel_name=channel_name,
            max_messages=10,  # Limit to avoid timeout
            start_date=start_date
        )
        
        logger.info(f"✓ EXTRACTED: {len(messages)} messages")
        
        if len(messages) > 0:
            # Analyze thread relationships
            parent_messages = [m for m in messages if m.thread_ts and not m.is_thread_reply]
            reply_messages = [m for m in messages if m.is_thread_reply]
            
            logger.info(f"✓ THREAD ANALYSIS:")
            logger.info(f"  - Parent messages: {len(parent_messages)}")
            logger.info(f"  - Reply messages: {len(reply_messages)}")
            
            # Show sample thread structure
            if parent_messages:
                sample_parent = parent_messages[0]
                logger.info(f"✓ SAMPLE THREAD STRUCTURE:")
                logger.info(f"  - Parent ID: {sample_parent.id}")
                logger.info(f"  - User: {sample_parent.user_name}")
                logger.info(f"  - Timestamp: {sample_parent.timestamp}")
                logger.info(f"  - Reply Count: {sample_parent.reply_count}")
                
                # Find replies to this thread
                thread_replies = [m for m in messages if m.parent_message_id == sample_parent.id]
                for i, reply in enumerate(thread_replies[:2]):  # Show first 2 replies
                    logger.info(f"    Reply {i+1}: {reply.user_name} - Position {reply.thread_position}")
            
            # Process messages
            processed_messages = await processor.process_slack_messages(messages)
            
            logger.info(f"✓ PROCESSED: {len(processed_messages)} messages for embedding")
            
            # Show data quality improvements
            if processed_messages:
                sample = processed_messages[0]
                metadata = sample.get('metadata', {})
                
                logger.info(f"✓ DATA QUALITY ENHANCEMENTS:")
                logger.info(f"  - Deterministic ID: {sample.get('id', 'N/A')}")
                logger.info(f"  - User Name: {metadata.get('user_name', 'N/A')}")
                logger.info(f"  - User Email: {metadata.get('user_email', 'N/A')}")
                logger.info(f"  - Channel Purpose: {metadata.get('channel_purpose', 'N/A')}")
                logger.info(f"  - Thread Position: {metadata.get('thread_position', 'N/A')}")
                logger.info(f"  - Is Thread Reply: {metadata.get('is_thread_reply', 'N/A')}")
                logger.info(f"  - Content Length: {len(sample.get('content', ''))}")
            
            # Get comprehensive summaries
            extraction_summary = connector.get_message_summary(messages)
            processing_summary = processor.get_processing_summary(processed_messages)
            
            logger.info(f"✓ EXTRACTION SUMMARY: {extraction_summary}")
            logger.info(f"✓ PROCESSING SUMMARY: {processing_summary}")
            
        else:
            logger.warning("No messages found in the specified time range")
        
        logger.info("=== ENHANCEMENT DEMONSTRATION COMPLETED ===")
        return True
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(demonstrate_enhancements())