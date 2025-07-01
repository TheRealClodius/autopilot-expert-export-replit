"""
Notion service for embedding pipeline monitoring and control.
Provides dashboard integration with real-time updates and control capabilities.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

try:
    from notion_client import Client
    from notion_client.errors import APIError
    NOTION_AVAILABLE = True
except ImportError:
    Client = None
    APIError = Exception
    NOTION_AVAILABLE = False

from config import settings

logger = logging.getLogger(__name__)

class NotionService:
    """Service for Notion dashboard integration with embedding pipeline monitoring."""
    
    def __init__(self):
        """Initialize Notion client with integration credentials."""
        self.integration_secret = settings.NOTION_INTEGRATION_SECRET
        self.database_id = settings.NOTION_DATABASE_ID
        
        if not self.integration_secret or not self.database_id:
            logger.warning("Notion credentials not configured - dashboard features disabled")
            self.client = None
            self.enabled = False
        else:
            try:
                self.client = Client(auth=self.integration_secret)
                self.enabled = True
                logger.info("Notion service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Notion client: {e}")
                self.client = None
                self.enabled = False
    
    async def verify_connection(self) -> bool:
        """Verify Notion API connection and database access."""
        if not self.enabled:
            return False
        
        try:
            # Test database access
            response = self.client.databases.query(database_id=self.database_id, page_size=1)
            logger.info("Notion connection verified successfully")
            return True
        except APIError as e:
            logger.error(f"Notion API error during verification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Notion verification: {e}")
            return False
    
    async def setup_database_schema(self) -> bool:
        """Ensure the database has the correct schema for embedding runs."""
        if not self.enabled:
            return False
        
        try:
            # Get current database schema
            db_response = self.client.databases.retrieve(database_id=self.database_id)
            current_properties = db_response.get("properties", {})
            
            # Define required schema
            required_properties = {
                "Run ID": {"title": {}},
                "Timestamp": {"date": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Success", "color": "green"},
                            {"name": "Partial Success", "color": "yellow"},
                            {"name": "Failed", "color": "red"},
                            {"name": "No New Messages", "color": "gray"}
                        ]
                    }
                },
                "Channels Checked": {"number": {"format": "number"}},
                "New Messages Found": {"number": {"format": "number"}},
                "Messages Embedded": {"number": {"format": "number"}},
                "Duration (seconds)": {"number": {"format": "number_with_commas"}},
                "Trigger Type": {
                    "select": {
                        "options": [
                            {"name": "Hourly Auto", "color": "blue"},
                            {"name": "Manual", "color": "purple"},
                            {"name": "Reset", "color": "orange"}
                        ]
                    }
                },
                "Errors": {"rich_text": {}}
            }
            
            # Update database schema if needed
            properties_to_update = {}
            for prop_name, prop_config in required_properties.items():
                if prop_name not in current_properties:
                    properties_to_update[prop_name] = prop_config
            
            if properties_to_update:
                self.client.databases.update(
                    database_id=self.database_id,
                    properties=properties_to_update
                )
                logger.info(f"Updated database schema with {len(properties_to_update)} new properties")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup database schema: {e}")
            return False
    
    async def log_embedding_run(self, run_data: Dict[str, Any]) -> Optional[str]:
        """Log an embedding run to the Notion database."""
        if not self.enabled:
            logger.warning("Notion service disabled - skipping run logging")
            return None
        
        try:
            # Generate unique run ID
            timestamp = datetime.now(timezone.utc)
            run_id = f"EMB-{timestamp.strftime('%Y%m%d-%H%M%S')}"
            
            # Prepare page properties
            properties = {
                "Run ID": {
                    "title": [{"text": {"content": run_id}}]
                },
                "Timestamp": {
                    "date": {"start": timestamp.isoformat()}
                },
                "Status": {
                    "select": {"name": run_data.get("status", "Unknown")}
                },
                "Channels Checked": {
                    "number": run_data.get("channels_checked", 0)
                },
                "New Messages Found": {
                    "number": run_data.get("new_messages_found", 0)
                },
                "Messages Embedded": {
                    "number": run_data.get("messages_embedded", 0)
                },
                "Duration (seconds)": {
                    "number": run_data.get("duration_seconds", 0)
                },
                "Trigger Type": {
                    "select": {"name": run_data.get("trigger_type", "Unknown")}
                }
            }
            
            # Add errors if present
            if run_data.get("errors"):
                properties["Errors"] = {
                    "rich_text": [{"text": {"content": str(run_data["errors"])}}]
                }
            
            # Create page in database
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            logger.info(f"Created Notion page for embedding run: {run_id} (Page ID: {page_id})")
            
            # Add detailed content to the page
            await self._add_run_details(page_id, run_data)
            
            return page_id
            
        except Exception as e:
            logger.error(f"Failed to log embedding run to Notion: {e}")
            return None
    
    async def _add_run_details(self, page_id: str, run_data: Dict[str, Any]):
        """Add detailed content blocks to the embedding run page."""
        try:
            blocks = []
            
            # Add summary section
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Embedding Run Summary"}}]
                }
            })
            
            # Add channel details if available
            if "channel_details" in run_data:
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"text": {"content": "Channel Details"}}]
                    }
                })
                
                for channel_info in run_data["channel_details"]:
                    channel_text = (
                        f"**{channel_info.get('name', 'Unknown')}** "
                        f"({channel_info.get('id', 'Unknown ID')})\n"
                        f"• New messages: {channel_info.get('new_messages', 0)}\n"
                        f"• Embedded: {channel_info.get('embedded', 0)}\n"
                        f"• Last check: {channel_info.get('last_check', 'Never')}\n"
                    )
                    
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": channel_text}}]
                        }
                    })
            
            # Add execution details
            if run_data.get("execution_details"):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"text": {"content": "Execution Details"}}]
                    }
                })
                
                details_text = str(run_data["execution_details"])
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": details_text}}],
                        "language": "plain text"
                    }
                })
            
            # Add blocks to page
            if blocks:
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=blocks
                )
                
        except Exception as e:
            logger.error(f"Failed to add run details to Notion page: {e}")
    
    async def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent embedding runs from the database."""
        if not self.enabled:
            return []
        
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                sorts=[{"property": "Timestamp", "direction": "descending"}],
                page_size=limit
            )
            
            runs = []
            for page in response["results"]:
                properties = page["properties"]
                
                run_info = {
                    "page_id": page["id"],
                    "run_id": self._extract_text_property(properties.get("Run ID")),
                    "timestamp": self._extract_date_property(properties.get("Timestamp")),
                    "status": self._extract_select_property(properties.get("Status")),
                    "channels_checked": self._extract_number_property(properties.get("Channels Checked")),
                    "new_messages_found": self._extract_number_property(properties.get("New Messages Found")),
                    "messages_embedded": self._extract_number_property(properties.get("Messages Embedded")),
                    "duration_seconds": self._extract_number_property(properties.get("Duration (seconds)")),
                    "trigger_type": self._extract_select_property(properties.get("Trigger Type")),
                    "errors": self._extract_text_property(properties.get("Errors"))
                }
                runs.append(run_info)
            
            return runs
            
        except Exception as e:
            logger.error(f"Failed to get recent runs from Notion: {e}")
            return []
    
    def _extract_text_property(self, prop: Optional[Dict]) -> str:
        """Extract text content from a Notion text property."""
        if not prop or prop["type"] not in ["title", "rich_text"]:
            return ""
        
        content_key = "title" if prop["type"] == "title" else "rich_text"
        content = prop.get(content_key, [])
        
        if content and len(content) > 0:
            return content[0].get("text", {}).get("content", "")
        return ""
    
    def _extract_date_property(self, prop: Optional[Dict]) -> Optional[str]:
        """Extract date from a Notion date property."""
        if not prop or prop["type"] != "date":
            return None
        
        date_obj = prop.get("date")
        if date_obj:
            return date_obj.get("start")
        return None
    
    def _extract_select_property(self, prop: Optional[Dict]) -> str:
        """Extract selection from a Notion select property."""
        if not prop or prop["type"] != "select":
            return ""
        
        select_obj = prop.get("select")
        if select_obj:
            return select_obj.get("name", "")
        return ""
    
    def _extract_number_property(self, prop: Optional[Dict]) -> int:
        """Extract number from a Notion number property."""
        if not prop or prop["type"] != "number":
            return 0
        
        return prop.get("number", 0) or 0
    
    async def update_run_status(self, page_id: str, status: str, additional_data: Optional[Dict] = None) -> bool:
        """Update the status of an existing embedding run."""
        if not self.enabled:
            return False
        
        try:
            properties = {
                "Status": {"select": {"name": status}}
            }
            
            if additional_data:
                if "messages_embedded" in additional_data:
                    properties["Messages Embedded"] = {"number": additional_data["messages_embedded"]}
                if "duration_seconds" in additional_data:
                    properties["Duration (seconds)"] = {"number": additional_data["duration_seconds"]}
                if "errors" in additional_data:
                    properties["Errors"] = {"rich_text": [{"text": {"content": str(additional_data["errors"])}}]}
            
            self.client.pages.update(page_id=page_id, properties=properties)
            logger.info(f"Updated Notion page {page_id} with status: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update run status in Notion: {e}")
            return False
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics for the embedding pipeline."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            # Get recent runs for statistics
            recent_runs = await self.get_recent_runs(limit=50)
            
            if not recent_runs:
                return {"enabled": True, "total_runs": 0}
            
            # Calculate statistics
            total_runs = len(recent_runs)
            successful_runs = len([r for r in recent_runs if r["status"] == "Success"])
            total_messages_embedded = sum(r["messages_embedded"] for r in recent_runs)
            average_duration = sum(r["duration_seconds"] for r in recent_runs) / total_runs if total_runs > 0 else 0
            
            last_run = recent_runs[0] if recent_runs else None
            
            stats = {
                "enabled": True,
                "total_runs": total_runs,
                "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
                "total_messages_embedded": total_messages_embedded,
                "average_duration_seconds": round(average_duration, 2),
                "last_run": last_run,
                "recent_runs_summary": recent_runs[:5]  # Last 5 runs
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {"enabled": True, "error": str(e)}