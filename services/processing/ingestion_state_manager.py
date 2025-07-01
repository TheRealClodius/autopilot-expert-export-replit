"""
Ingestion State Manager - Coordinates between first generation and hourly daemon.
Ensures no messages are lost if first generation ingestion fails partway through.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class IngestionStateManager:
    """
    Manages the coordination between first generation ingestion and hourly daemon.
    Tracks completion status and ensures gap-free message processing.
    """
    
    def __init__(self):
        self.first_gen_state_file = "first_generation_state.json"
        self.hourly_state_file = "hourly_embedding_state.json"
        self.channels = [
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
    
    def get_first_generation_state(self) -> Dict[str, Any]:
        """Get the current state of first generation ingestion."""
        try:
            with open(self.first_gen_state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "status": "not_started",
                "channels": {},
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
    
    def update_first_generation_progress(self, channel_id: str, channel_name: str, 
                                       messages_processed: int, latest_timestamp: str,
                                       total_extracted: int, status: str = "in_progress"):
        """Update progress for a specific channel during first generation ingestion."""
        state = self.get_first_generation_state()
        
        state["channels"][channel_id] = {
            "channel_name": channel_name,
            "messages_processed": messages_processed,
            "total_extracted": total_extracted,
            "latest_timestamp": latest_timestamp,
            "status": status,  # "in_progress", "completed", "failed"
            "last_updated": datetime.now().isoformat()
        }
        
        # Update overall status
        all_completed = all(
            ch.get("status") == "completed" 
            for ch in state["channels"].values()
        )
        
        if all_completed and len(state["channels"]) == len(self.channels):
            state["status"] = "completed"
        elif any(ch.get("status") == "failed" for ch in state["channels"].values()):
            state["status"] = "partial_failure"
        else:
            state["status"] = "in_progress"
        
        state["last_updated"] = datetime.now().isoformat()
        
        with open(self.first_gen_state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Updated first generation state for {channel_name}: {messages_processed} messages processed")
    
    def mark_first_generation_complete(self):
        """Mark first generation ingestion as fully completed."""
        state = self.get_first_generation_state()
        state["status"] = "completed"
        state["completed_at"] = datetime.now().isoformat()
        state["last_updated"] = datetime.now().isoformat()
        
        with open(self.first_gen_state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info("First generation ingestion marked as complete")
    
    def is_first_generation_complete(self) -> bool:
        """Check if first generation ingestion is fully completed."""
        state = self.get_first_generation_state()
        return state.get("status") == "completed"
    
    def get_missing_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels that need first generation ingestion (not completed)."""
        if self.is_first_generation_complete():
            return []
        
        state = self.get_first_generation_state()
        missing_channels = []
        
        for channel in self.channels:
            channel_state = state["channels"].get(channel["id"])
            if not channel_state or channel_state.get("status") != "completed":
                missing_channels.append({
                    **channel,
                    "needs_first_gen": True,
                    "current_state": channel_state
                })
        
        return missing_channels
    
    def should_hourly_daemon_run_first_gen(self) -> Dict[str, Any]:
        """
        Determine if hourly daemon should run first generation logic instead of incremental.
        Returns strategy and channels to process.
        """
        if self.is_first_generation_complete():
            return {
                "strategy": "incremental",
                "reason": "First generation completed, run normal hourly checks",
                "channels": self.channels
            }
        
        missing_channels = self.get_missing_channels()
        
        if missing_channels:
            return {
                "strategy": "first_generation_recovery",
                "reason": f"First generation incomplete, {len(missing_channels)} channels need historical ingestion",
                "channels": missing_channels,
                "missing_count": len(missing_channels)
            }
        
        return {
            "strategy": "incremental",
            "reason": "All channels processed, switching to incremental mode",
            "channels": self.channels
        }
    
    def get_hourly_state(self) -> Dict[str, Any]:
        """Get hourly daemon state."""
        try:
            with open(self.hourly_state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "last_run": None,
                "channels": {},
                "created_at": datetime.now().isoformat()
            }
    
    def update_hourly_state(self, channel_id: str, latest_timestamp: str, messages_embedded: int):
        """Update hourly daemon state after successful processing."""
        state = self.get_hourly_state()
        
        state["channels"][channel_id] = {
            "latest_timestamp": latest_timestamp,
            "last_check": datetime.now().isoformat(),
            "messages_embedded": messages_embedded
        }
        state["last_run"] = datetime.now().isoformat()
        
        with open(self.hourly_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of both first generation and hourly systems."""
        first_gen_state = self.get_first_generation_state()
        hourly_state = self.get_hourly_state()
        strategy = self.should_hourly_daemon_run_first_gen()
        
        return {
            "first_generation": {
                "status": first_gen_state.get("status", "not_started"),
                "channels_processed": len(first_gen_state.get("channels", {})),
                "total_channels": len(self.channels),
                "is_complete": self.is_first_generation_complete()
            },
            "hourly_daemon": {
                "last_run": hourly_state.get("last_run"),
                "channels_tracked": len(hourly_state.get("channels", {}))
            },
            "current_strategy": strategy,
            "missing_channels": self.get_missing_channels(),
            "recommendations": self._get_recommendations(strategy)
        }
    
    def _get_recommendations(self, strategy: Dict[str, Any]) -> Dict[str, str]:
        """Get actionable recommendations based on current state."""
        if strategy["strategy"] == "first_generation_recovery":
            return {
                "action": "run_first_generation_recovery",
                "message": f"Hourly daemon will automatically attempt first generation ingestion for {strategy['missing_count']} channels",
                "priority": "high"
            }
        elif strategy["strategy"] == "incremental":
            return {
                "action": "monitor_hourly",
                "message": "System is in normal operation mode with hourly incremental updates",
                "priority": "normal"
            }
        else:
            return {
                "action": "investigate",
                "message": "Unknown strategy detected - manual investigation needed",
                "priority": "critical"
            }