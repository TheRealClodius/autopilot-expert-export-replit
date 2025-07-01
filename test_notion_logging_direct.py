#!/usr/bin/env python3
"""
Test Notion logging directly to diagnose the database issue.
"""
import os
import asyncio
from datetime import datetime
from services.notion_service import NotionService
from config import settings

async def test_notion_logging():
    """Test direct Notion logging to see what's happening."""
    print("=== Direct Notion Logging Test ===")
    
    # Initialize Notion service
    notion_service = NotionService(settings)
    
    if not notion_service.enabled:
        print("❌ Notion service not enabled")
        return
    
    print(f"✅ Notion service enabled")
    print(f"Database ID: {notion_service.database_id}")
    
    # Test connection
    connection_ok = await notion_service.verify_connection()
    print(f"Connection verified: {connection_ok}")
    
    if not connection_ok:
        print("❌ Connection failed, stopping test")
        return
    
    # Create test embedding run data
    test_run_data = {
        "run_id": f"test_{int(datetime.now().timestamp())}",
        "trigger_type": "Test Run",
        "check_time": datetime.now().isoformat(),
        "channels_checked": 2,
        "channels_with_new_messages": 0,
        "total_messages_embedded": 0,
        "duration_seconds": 1.5,
        "status": "Success",
        "channel_results": [
            {
                "channel_id": "C087QKECFKQ",
                "channel_name": "autopilot-design-patterns",
                "new_messages_found": False,
                "action": "no_new_messages"
            }
        ],
        "errors": []
    }
    
    print(f"🔄 Attempting to log test run...")
    
    # Try to log the run
    page_id = await notion_service.log_embedding_run(test_run_data)
    
    if page_id:
        print(f"✅ Successfully logged to Notion! Page ID: {page_id}")
        print(f"🔗 Check your database for the new entry")
    else:
        print("❌ Failed to log to Notion")
    
    # Try to retrieve recent runs
    print(f"🔄 Attempting to retrieve recent runs...")
    recent_runs = await notion_service.get_recent_runs(limit=5)
    
    if recent_runs:
        print(f"✅ Retrieved {len(recent_runs)} recent runs")
        for i, run in enumerate(recent_runs[:3]):
            print(f"  Run {i+1}: {run.get('run_id', 'Unknown')} - {run.get('status', 'Unknown')}")
    else:
        print("❌ No recent runs found or failed to retrieve")

if __name__ == "__main__":
    asyncio.run(test_notion_logging())