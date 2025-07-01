#!/usr/bin/env python3
"""
Simple hourly daemon that runs the embedding task every hour.
This replaces Celery with a straightforward time-based scheduler.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import traceback

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_embedding_task():
    """Run the hourly embedding check task."""
    try:
        print(f"[{datetime.now()}] Starting scheduled embedding task...")
        
        # Import and run the smart embedding function directly
        from run_smart_hourly_embedding import run_smart_hourly_embedding
        
        # Execute the smart embedding logic (handles both first gen recovery and incremental)
        result = await run_smart_hourly_embedding()
        
        print(f"[{datetime.now()}] Embedding task completed successfully")
        print(f"Channels checked: {result.get('channels_checked', 0)}")
        print(f"Messages embedded: {result.get('total_messages_embedded', 0)}")
        
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] ERROR in embedding task: {e}")
        traceback.print_exc()
        return False

def get_next_hour():
    """Get the next hour mark (e.g., if it's 15:30, returns 16:00)."""
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return next_hour

async def main():
    """Main daemon loop."""
    print(f"[{datetime.now()}] Hourly embedding daemon starting...")
    
    # Run initial task
    await run_embedding_task()
    
    while True:
        try:
            # Calculate time until next hour
            next_run = get_next_hour()
            now = datetime.now()
            sleep_seconds = (next_run - now).total_seconds()
            
            print(f"[{now}] Next run scheduled for: {next_run}")
            print(f"[{now}] Sleeping for {int(sleep_seconds/60)} minutes {int(sleep_seconds%60)} seconds...")
            
            # Sleep until next hour
            await asyncio.sleep(sleep_seconds)
            
            # Run the task
            await run_embedding_task()
            
        except KeyboardInterrupt:
            print(f"[{datetime.now()}] Daemon stopped by user")
            break
        except Exception as e:
            print(f"[{datetime.now()}] ERROR in daemon loop: {e}")
            traceback.print_exc()
            # Sleep 5 minutes before retrying
            await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Hourly daemon stopped")
        sys.exit(0)