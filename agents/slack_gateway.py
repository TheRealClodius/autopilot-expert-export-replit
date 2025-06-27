"""
Slack Gateway Agent - Handles incoming Slack messages and outgoing responses.
Acts as the interface between Slack and the internal agent system.
"""

import logging
from typing import Optional, Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import settings
from models.schemas import SlackEvent, ProcessedMessage

logger = logging.getLogger(__name__)

class SlackGateway:
    """
    Gateway for all Slack interactions.
    Processes incoming messages and sends responses back to Slack.
    """
    
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.bot_user_id = settings.SLACK_BOT_USER_ID
        
    async def process_message(self, event_data: SlackEvent) -> Optional[ProcessedMessage]:
        """
        Process incoming Slack message and extract relevant information.
        
        Args:
            event_data: Raw Slack event data
            
        Returns:
            ProcessedMessage if the message should be processed, None otherwise
        """
        try:
            event = event_data.event
            
            # Extract basic message information
            text = event.get("text", "").strip()
            user_id = event.get("user")
            channel_id = event.get("channel")
            thread_ts = event.get("thread_ts")
            message_ts = event.get("ts")
            
            if not text or not user_id or not channel_id:
                return None
                
            # Check if this is a mention or DM
            is_dm = await self._is_direct_message(channel_id)
            is_mention = f"<@{self.bot_user_id}>" in text if self.bot_user_id else False
            is_thread_reply = thread_ts is not None
            
            # Only process if it's a DM, mention, or thread reply to bot
            if not (is_dm or is_mention or (is_thread_reply and await self._is_bot_thread(channel_id, thread_ts))):
                return None
            
            # Clean the message text (remove mentions)
            clean_text = self._clean_message_text(text)
            
            # Get user information
            user_info = await self._get_user_info(user_id)
            
            # Get channel information
            channel_info = await self._get_channel_info(channel_id)
            
            # Get thread context if this is a threaded message
            thread_context = None
            if thread_ts:
                thread_context = await self._get_thread_context(channel_id, thread_ts)
            
            processed_message = ProcessedMessage(
                text=clean_text,
                user_id=user_id,
                user_name=user_info.get("name", "Unknown"),
                user_email=user_info.get("profile", {}).get("email", ""),
                channel_id=channel_id,
                channel_name=channel_info.get("name", "Unknown"),
                is_dm=is_dm,
                is_mention=is_mention,
                thread_ts=thread_ts,
                message_ts=message_ts,
                thread_context=thread_context
            )
            
            logger.info(f"Processed message from {user_info.get('name')} in {channel_info.get('name')}")
            return processed_message
            
        except Exception as e:
            logger.error(f"Error processing Slack message: {e}")
            return None
    
    async def send_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Send response back to Slack.
        
        Args:
            response_data: Dictionary containing response information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            channel_id = response_data.get("channel_id")
            text = response_data.get("text")
            thread_ts = response_data.get("thread_ts")
            
            if not channel_id or not text:
                logger.error("Missing channel_id or text in response data")
                return False
            
            # Send message to Slack
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts,
                unfurl_links=False,
                unfurl_media=False
            )
            
            if response["ok"]:
                logger.info(f"Successfully sent response to channel {channel_id}")
                return True
            else:
                logger.error(f"Failed to send Slack message: {response.get('error')}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack response: {e}")
            return False
    
    async def send_thinking_indicator(self, channel_id: str, thread_ts: Optional[str] = None) -> Optional[str]:
        """
        Send a thinking indicator message to Slack.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp if replying in thread
            
        Returns:
            Message timestamp of the thinking indicator for later editing
        """
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text="🤔 Thinking...",
                thread_ts=thread_ts,
                unfurl_links=False,
                unfurl_media=False
            )
            
            if response["ok"]:
                logger.info(f"Sent thinking indicator to {channel_id}")
                return response["ts"]
            else:
                logger.error(f"Failed to send thinking indicator: {response.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending thinking indicator: {e}")
            return None
    
    async def update_message(self, channel_id: str, message_ts: str, new_text: str) -> bool:
        """
        Update an existing Slack message.
        
        Args:
            channel_id: Slack channel ID
            message_ts: Timestamp of message to update
            new_text: New text content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=new_text,
                unfurl_links=False,
                unfurl_media=False
            )
            
            if response["ok"]:
                logger.info(f"Updated message {message_ts} in {channel_id}")
                return True
            else:
                logger.error(f"Failed to update message: {response.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return False

    async def send_error_response(self, channel_id: str, error_message: str, thread_ts: Optional[str] = None) -> bool:
        """Send error message to Slack"""
        try:
            self.client.chat_postMessage(
                channel=channel_id,
                text=f"⚠️ {error_message}",
                thread_ts=thread_ts
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
            return False
    
    async def _is_direct_message(self, channel_id: str) -> bool:
        """Check if the channel is a direct message"""
        try:
            return channel_id.startswith("D")
        except Exception:
            return False
    
    async def _is_bot_thread(self, channel_id: str, thread_ts: str) -> bool:
        """Check if the thread was started by the bot"""
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1
            )
            
            if response["ok"] and response["messages"]:
                original_message = response["messages"][0]
                return original_message.get("user") == self.bot_user_id
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking bot thread: {e}")
            return False
    
    def _clean_message_text(self, text: str) -> str:
        """Clean message text by removing mentions and formatting"""
        import re
        
        # Remove bot mentions
        text = re.sub(r'<@[A-Z0-9]+>', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    async def _get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information from Slack"""
        try:
            response = self.client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
            return {"name": "Unknown"}
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {"name": "Unknown"}
    
    async def _get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information from Slack"""
        try:
            response = self.client.conversations_info(channel=channel_id)
            if response["ok"]:
                return response["channel"]
            return {"name": "Unknown"}
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_id}: {e}")
            return {"name": "Unknown"}
    
    async def _get_thread_context(self, channel_id: str, thread_ts: str, limit: int = 5) -> Optional[str]:
        """Get recent context from thread"""
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=limit
            )
            
            if response["ok"] and response["messages"]:
                context_messages = []
                for msg in response["messages"][-limit:]:
                    user_id = msg.get("user", "Unknown")
                    text = msg.get("text", "")
                    if text:
                        context_messages.append(f"{user_id}: {text}")
                
                return "\n".join(context_messages)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting thread context: {e}")
            return None
