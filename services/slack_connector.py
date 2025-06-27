"""
Slack Connector Service - Extracts messages and data from Slack channels.
Handles authentication, rate limiting, and data extraction.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import time

from config import settings

logger = logging.getLogger(__name__)

class SlackConnector:
    """
    Service for connecting to Slack and extracting conversation data.
    Handles rate limiting and pagination for large data extraction.
    """
    
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.rate_limit_delay = 1.0  # Base delay between API calls
        
    async def extract_channel_messages(
        self, 
        channel_id: str,
        start_time: datetime,
        end_time: datetime,
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Extract messages from a Slack channel within a time range.
        
        Args:
            channel_id: Slack channel ID to extract from
            start_time: Start of time range
            end_time: End of time range
            batch_size: Number of messages per API call
            
        Returns:
            List of message dictionaries
        """
        try:
            logger.info(f"Extracting messages from channel {channel_id} from {start_time} to {end_time}")
            
            messages = []
            cursor = None
            
            # Convert datetime to Slack timestamps
            oldest = str(start_time.timestamp())
            latest = str(end_time.timestamp())
            
            while True:
                try:
                    # Get channel history with pagination
                    # Try different methods based on available permissions
                    response = None
                    
                    # Method 1: Direct conversations_history (works for public channels)
                    try:
                        response = self.client.conversations_history(
                            channel=channel_id,
                            limit=batch_size,
                            oldest=oldest,
                            latest=latest,
                            cursor=cursor
                        )
                    except SlackApiError as api_error:
                        if api_error.response["error"] == "not_in_channel":
                            # Method 2: Try to join the channel first if it's public
                            try:
                                join_response = self.client.conversations_join(channel=channel_id)
                                if join_response["ok"]:
                                    logger.info(f"Successfully joined channel {channel_id}")
                                    response = self.client.conversations_history(
                                        channel=channel_id,
                                        limit=batch_size,
                                        oldest=oldest,
                                        latest=latest,
                                        cursor=cursor
                                    )
                                else:
                                    logger.warning(f"Could not join channel {channel_id}: {join_response.get('error')}")
                            except SlackApiError as join_error:
                                logger.warning(f"Could not join channel {channel_id}: {join_error.response.get('error')}")
                                raise api_error  # Re-raise original error
                        else:
                            raise  # Re-raise for other errors
                    
                    if not response["ok"]:
                        logger.error(f"Slack API error: {response.get('error', 'Unknown error')}")
                        break
                    
                    batch_messages = response.get("messages", [])
                    if not batch_messages:
                        break
                    
                    # Process each message
                    for message in batch_messages:
                        processed_message = await self._process_raw_message(message, channel_id)
                        if processed_message:
                            messages.append(processed_message)
                    
                    # Check for more messages
                    if not response.get("has_more", False):
                        break
                    
                    cursor = response.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except SlackApiError as e:
                    if e.response["error"] == "rate_limited":
                        # Handle rate limiting
                        retry_after = int(e.response.get("headers", {}).get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        logger.error(f"Slack API error: {e.response['error']}")
                        break
                
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    break
            
            # Get threaded messages for each message that has replies
            threaded_messages = await self._extract_threaded_messages(messages, channel_id)
            messages.extend(threaded_messages)
            
            logger.info(f"Extracted {len(messages)} messages from channel {channel_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error extracting channel messages: {e}")
            return []
    
    async def _extract_threaded_messages(
        self, 
        messages: List[Dict[str, Any]], 
        channel_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract threaded replies for messages that have threads.
        
        Args:
            messages: List of parent messages
            channel_id: Channel ID
            
        Returns:
            List of threaded messages
        """
        try:
            threaded_messages = []
            
            for message in messages:
                if message.get("reply_count", 0) > 0:
                    thread_ts = message.get("thread_ts") or message.get("ts")
                    
                    if thread_ts:
                        thread_replies = await self._get_thread_replies(channel_id, thread_ts)
                        threaded_messages.extend(thread_replies)
                        
                        # Rate limiting
                        await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"Extracted {len(threaded_messages)} threaded messages")
            return threaded_messages
            
        except Exception as e:
            logger.error(f"Error extracting threaded messages: {e}")
            return []
    
    async def _get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Get replies for a specific thread"""
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000  # Get all replies
            )
            
            if not response["ok"]:
                return []
            
            thread_messages = []
            for message in response.get("messages", [])[1:]:  # Skip parent message
                processed_message = await self._process_raw_message(message, channel_id, thread_ts)
                if processed_message:
                    thread_messages.append(processed_message)
            
            return thread_messages
            
        except Exception as e:
            logger.error(f"Error getting thread replies: {e}")
            return []
    
    async def _process_raw_message(
        self, 
        raw_message: Dict[str, Any], 
        channel_id: str,
        thread_ts: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process a raw Slack message into a structured format.
        
        Args:
            raw_message: Raw message from Slack API
            channel_id: Channel ID
            thread_ts: Thread timestamp if this is a threaded message
            
        Returns:
            Processed message dictionary or None if message should be skipped
        """
        try:
            # Skip bot messages and system messages
            if (raw_message.get("bot_id") or 
                raw_message.get("subtype") in ["bot_message", "channel_join", "channel_leave"]):
                return None
            
            # Skip empty messages
            text = raw_message.get("text", "").strip()
            if not text:
                return None
            
            # Get message timestamp
            ts = raw_message.get("ts")
            if not ts:
                return None
            
            message_datetime = datetime.fromtimestamp(float(ts))
            
            # Get user information
            user_id = raw_message.get("user")
            user_info = await self._get_user_info(user_id) if user_id else {}
            
            # Get channel information
            channel_info = await self._get_channel_info(channel_id)
            
            processed_message = {
                "id": f"{channel_id}_{ts}",
                "text": text,
                "timestamp": message_datetime.isoformat(),
                "ts": ts,
                "user_id": user_id,
                "user_name": user_info.get("name", "Unknown"),
                "user_email": user_info.get("profile", {}).get("email", ""),
                "channel_id": channel_id,
                "channel_name": channel_info.get("name", "Unknown"),
                "channel_purpose": channel_info.get("purpose", {}).get("value", ""),
                "thread_ts": thread_ts or raw_message.get("thread_ts"),
                "is_thread_reply": thread_ts is not None,
                "reply_count": raw_message.get("reply_count", 0),
                "reactions": raw_message.get("reactions", []),
                "files": raw_message.get("files", []),
                "attachments": raw_message.get("attachments", [])
            }
            
            return processed_message
            
        except Exception as e:
            logger.error(f"Error processing raw message: {e}")
            return None
    
    async def _get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information with caching"""
        try:
            # Simple caching could be added here
            response = self.client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
            return {}
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {}
    
    async def _get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information with caching"""
        try:
            # Simple caching could be added here
            response = self.client.conversations_info(channel=channel_id)
            if response["ok"]:
                return response["channel"]
            return {}
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_id}: {e}")
            return {}
    
    async def get_workspace_channels(self) -> List[Dict[str, Any]]:
        """Get list of all channels in the workspace"""
        try:
            channels = []
            cursor = None
            
            while True:
                response = self.client.conversations_list(
                    types="public_channel,private_channel",
                    limit=200,
                    cursor=cursor
                )
                
                if not response["ok"]:
                    break
                
                channels.extend(response.get("channels", []))
                
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                
                await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"Found {len(channels)} channels in workspace")
            return channels
            
        except Exception as e:
            logger.error(f"Error getting workspace channels: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Test Slack connection and permissions"""
        try:
            response = self.client.auth_test()
            if response["ok"]:
                logger.info(f"Slack connection successful for user: {response.get('user')}")
                return True
            else:
                logger.error(f"Slack auth test failed: {response.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error testing Slack connection: {e}")
            return False
