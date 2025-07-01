#!/usr/bin/env python3
"""
Standalone script for hourly embedding task execution via cron.
This bypasses Celery entirely and runs the task directly.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    """Run the hourly embedding check directly."""
    try:
        print(f"[{datetime.now()}] Starting hourly embedding check...")
        
        # Import and run the embedding function directly
        from workers.hourly_embedding_worker import run_hourly_embedding_check
        
        # Execute the main embedding logic
        result = await run_hourly_embedding_check()
        
        print(f"[{datetime.now()}] Hourly embedding check completed successfully")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error in hourly embedding check: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())