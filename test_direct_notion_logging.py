"""
Test direct Notion logging to debug the issue.
"""
import os
import asyncio
from services.notion_service import NotionService

async def test_direct_logging():
    """Test logging directly to Notion."""
    
    # Create test data
    test_data = {
        "status": "Success",
        "channels_checked": 2,
        "messages_embedded": 15,
        "duration_seconds": 45.5,
        "errors": []
    }
    
    print("=== TESTING DIRECT NOTION LOGGING ===")
    
    # Initialize service
    notion_service = NotionService()
    
    # Verify connection
    print("Testing connection...")
    connection_ok = await notion_service.verify_connection()
    print(f"Connection: {'✓' if connection_ok else '✗'}")
    
    if not connection_ok:
        print("Cannot proceed without connection")
        return
    
    # Test logging
    print("Attempting to log test run...")
    page_id = await notion_service.log_embedding_run(test_data)
    print(f"Logged page ID: {page_id}")
    
    if page_id:
        print("✓ Successfully logged test embedding run")
    else:
        print("✗ Failed to log embedding run")
    
    # Get recent runs
    print("Fetching recent runs...")
    recent_runs = await notion_service.get_recent_runs(limit=3)
    print(f"Found {len(recent_runs)} recent runs")
    
    for i, run in enumerate(recent_runs):
        print(f"Run {i+1}:")
        print(f"  Run ID: {run.get('run_id', 'N/A')}")
        print(f"  Status: {run.get('status', 'N/A')}")
        print(f"  Channels: {run.get('channels_checked', 0)}")
        print(f"  Duration: {run.get('duration_seconds', 0)}")

if __name__ == "__main__":
    asyncio.run(test_direct_logging())