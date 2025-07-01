#!/usr/bin/env python3
"""
Test the 1-year message filter in the enhanced extraction system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from services.enhanced_slack_connector import EnhancedSlackConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_one_year_filter():
    """Test the 1-year message filter functionality."""
    logger.info("=== Testing 1-Year Message Filter ===")
    
    try:
        connector = EnhancedSlackConnector()
        
        # Test with autopilot-design-patterns channel
        channel_id = "C087QKECFKQ"
        channel_name = "autopilot-design-patterns"
        
        logger.info(f"Testing 1-year filter with {channel_name}...")
        
        # Test 1: Default behavior (should use 1-year lookback)
        logger.info("Test 1: Default 1-year lookback")
        messages_1year = await connector.extract_channel_history_complete(
            channel_id=channel_id,
            channel_name=channel_name,
            max_messages=10
        )
        
        logger.info(f"✓ Default 1-year lookback: {len(messages_1year)} messages")
        
        # Test 2: Explicit 1-year limit
        logger.info("Test 2: Explicit 1-year limit (365 days)")
        messages_365 = await connector.extract_channel_history_complete(
            channel_id=channel_id,
            channel_name=channel_name,
            max_messages=10,
            max_age_days=365
        )
        
        logger.info(f"✓ Explicit 365-day limit: {len(messages_365)} messages")
        
        # Test 3: Shorter period (30 days) for comparison
        logger.info("Test 3: 30-day limit for comparison")
        messages_30 = await connector.extract_channel_history_complete(
            channel_id=channel_id,
            channel_name=channel_name,
            max_messages=10,
            max_age_days=30
        )
        
        logger.info(f"✓ 30-day limit: {len(messages_30)} messages")
        
        # Test 4: Very old start date (should be limited to 1 year)
        logger.info("Test 4: Very old start date (should be capped at 1 year)")
        very_old_date = datetime.now() - timedelta(days=2000)  # ~5.5 years ago
        messages_capped = await connector.extract_channel_history_complete(
            channel_id=channel_id,
            channel_name=channel_name,
            max_messages=10,
            start_date=very_old_date,
            max_age_days=365
        )
        
        logger.info(f"✓ Old start date capped: {len(messages_capped)} messages")
        
        # Show results summary
        logger.info(f"\n=== 1-Year Filter Test Results ===")
        logger.info(f"Default 1-year: {len(messages_1year)} messages")
        logger.info(f"Explicit 365-day: {len(messages_365)} messages")
        logger.info(f"30-day comparison: {len(messages_30)} messages")
        logger.info(f"Capped old date: {len(messages_capped)} messages")
        
        # Validate behavior
        success = True
        
        if len(messages_1year) != len(messages_365):
            logger.error("Default and explicit 365-day should be the same")
            success = False
        
        if len(messages_30) > len(messages_1year):
            logger.error("30-day should have fewer messages than 1-year")
            success = False
        
        if len(messages_capped) != len(messages_1year):
            logger.error("Capped old date should match 1-year limit")
            success = False
        
        if success:
            logger.info("✅ All 1-year filter tests passed!")
        else:
            logger.error("❌ Some tests failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_one_year_filter())
    print(f"\nTest Result: {'✅ PASSED' if result else '❌ FAILED'}")