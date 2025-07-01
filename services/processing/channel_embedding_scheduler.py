"""
Scheduling service for automatic channel embedding.
Handles periodic updates and incremental processing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

from config import settings
from workers.bulk_channel_embedder import run_bulk_embedding, ChannelConfig

logger = logging.getLogger(__name__)

class ChannelEmbeddingScheduler:
    """
    Manages automatic scheduling of channel embedding updates.
    """
    
    def __init__(self):
        self.state_file = "channel_embedding_state.json"
        self.channels = [
            ChannelConfig(
                id="C087QKECFKQ",
                name="autopilot-design-patterns",
                is_private=False
            ),
            ChannelConfig(
                id="C08STCP2YUA", 
                name="genai-designsys",
                is_private=True
            )
        ]
        self.load_state()
    
    def load_state(self):
        """Load previous embedding state from disk."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                # Update channel configs with saved state
                for channel in self.channels:
                    channel_state = state.get(channel.id, {})
                    channel.last_embedded_ts = channel_state.get('last_embedded_ts')
                    channel.total_messages_embedded = channel_state.get('total_messages_embedded', 0)
                
                logger.info(f"Loaded embedding state for {len(state)} channels")
                
        except Exception as e:
            logger.warning(f"Could not load embedding state: {e}")
    
    def save_state(self):
        """Save current embedding state to disk."""
        try:
            state = {}
            for channel in self.channels:
                state[channel.id] = {
                    'name': channel.name,
                    'last_embedded_ts': channel.last_embedded_ts,
                    'total_messages_embedded': channel.total_messages_embedded,
                    'last_update': datetime.now().isoformat()
                }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Saved embedding state for {len(state)} channels")
            
        except Exception as e:
            logger.error(f"Could not save embedding state: {e}")
    
    async def run_incremental_update(self, max_messages_per_channel: Optional[int] = None) -> Dict:
        """
        Run incremental update - only embed new messages since last run.
        """
        logger.info("Starting incremental channel embedding update")
        
        try:
            stats = await run_bulk_embedding(max_messages_per_channel)
            
            # Save updated state
            self.save_state()
            
            result = {
                "status": "success",
                "type": "incremental",
                "channels_processed": stats.channels_processed,
                "total_messages_extracted": stats.total_messages_extracted,
                "total_messages_embedded": stats.total_messages_embedded,
                "duration_seconds": (stats.end_time - stats.start_time).total_seconds(),
                "errors": stats.errors,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Incremental update complete: {stats.total_messages_embedded} new messages embedded")
            return result
            
        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return {
                "status": "error",
                "type": "incremental",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_full_refresh(self, max_messages_per_channel: Optional[int] = None) -> Dict:
        """
        Run full refresh - clear state and re-embed everything.
        """
        logger.info("Starting full channel embedding refresh")
        
        try:
            # Clear previous state
            for channel in self.channels:
                channel.last_embedded_ts = None
                channel.total_messages_embedded = 0
            
            stats = await run_bulk_embedding(max_messages_per_channel)
            
            # Save new state
            self.save_state()
            
            result = {
                "status": "success",
                "type": "full_refresh",
                "channels_processed": stats.channels_processed,
                "total_messages_extracted": stats.total_messages_extracted,
                "total_messages_embedded": stats.total_messages_embedded,
                "duration_seconds": (stats.end_time - stats.start_time).total_seconds(),
                "errors": stats.errors,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Full refresh complete: {stats.total_messages_embedded} total messages embedded")
            return result
            
        except Exception as e:
            logger.error(f"Full refresh failed: {e}")
            return {
                "status": "error",
                "type": "full_refresh",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict:
        """Get current embedding status."""
        status = {
            "channels": [],
            "total_messages_embedded": 0,
            "state_file_exists": os.path.exists(self.state_file)
        }
        
        for channel in self.channels:
            channel_status = {
                "id": channel.id,
                "name": channel.name,
                "is_private": channel.is_private,
                "total_messages_embedded": channel.total_messages_embedded,
                "last_embedded_ts": channel.last_embedded_ts,
                "has_previous_data": channel.last_embedded_ts is not None
            }
            
            status["channels"].append(channel_status)
            status["total_messages_embedded"] += channel.total_messages_embedded
        
        return status
    
    async def smart_update(self, force_full_refresh: bool = False) -> Dict:
        """
        Smart update - chooses between incremental and full refresh based on state.
        """
        if force_full_refresh:
            return await self.run_full_refresh()
        
        # Check if we have previous state
        has_state = any(channel.last_embedded_ts for channel in self.channels)
        
        if has_state:
            logger.info("Previous state found, running incremental update")
            return await self.run_incremental_update()
        else:
            logger.info("No previous state, running full refresh")
            return await self.run_full_refresh()

# Utility functions for direct use
async def schedule_incremental_update(max_messages: Optional[int] = None) -> Dict:
    """Run incremental update."""
    scheduler = ChannelEmbeddingScheduler()
    return await scheduler.run_incremental_update(max_messages)

async def schedule_full_refresh(max_messages: Optional[int] = None) -> Dict:
    """Run full refresh."""
    scheduler = ChannelEmbeddingScheduler()
    return await scheduler.run_full_refresh(max_messages)

async def schedule_smart_update(force_full: bool = False) -> Dict:
    """Run smart update."""
    scheduler = ChannelEmbeddingScheduler()
    return await scheduler.smart_update(force_full)

def get_embedding_status() -> Dict:
    """Get embedding status."""
    scheduler = ChannelEmbeddingScheduler()
    return scheduler.get_status()

if __name__ == "__main__":
    import sys
    
    command = sys.argv[1] if len(sys.argv) > 1 else "smart"
    max_messages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    async def main():
        scheduler = ChannelEmbeddingScheduler()
        
        if command == "incremental":
            result = await scheduler.run_incremental_update(max_messages)
        elif command == "full":
            result = await scheduler.run_full_refresh(max_messages)
        elif command == "smart":
            result = await scheduler.smart_update()
        elif command == "status":
            result = scheduler.get_status()
            print(json.dumps(result, indent=2))
            return
        else:
            print("Usage: python channel_embedding_scheduler.py [incremental|full|smart|status] [max_messages]")
            return
        
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())