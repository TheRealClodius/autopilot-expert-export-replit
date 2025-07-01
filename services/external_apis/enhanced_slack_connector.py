"""
Enhanced Slack Connector Service - Fixes thread relationships, metadata extraction, and rate limiting.
Properly handles message ordering, thread nesting, and complete historical data ingestion.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import asyncio
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import time
import json
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)

@dataclass
class SlackMessage:
    """Enhanced message structure with proper thread relationships"""
    id: str
    text: str
    timestamp: datetime
    ts: str
    user_id: str
    user_name: str
    user_email: str
    channel_id: str
    channel_name: str
    channel_purpose: str
    thread_ts: Optional[str] = None
    parent_message_id: Optional[str] = None
    is_thread_reply: bool = False
    thread_position: int = 0  # Position within thread (0 = parent)
    reply_count: int = 0
    reactions: List[Dict] = None
    files: List[Dict] = None
    attachments: List[Dict] = None
    
    def __post_init__(self):
        if self.reactions is None:
            self.reactions = []
        if self.files is None:
            self.files = []
        if self.attachments is None:
            self.attachments = []

class EnhancedSlackConnector:
    """
    Enhanced Slack connector with proper thread relationships and efficient metadata extraction.
    """
    
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.base_delay = 1.0  # Base delay between API calls
        self.max_delay = 30.0  # Maximum delay for exponential backoff
        self.user_cache = {}  # Cache for user information
        self.channel_cache = {}  # Cache for channel information
        
    async def extract_channel_history_complete(
        self, 
        channel_id: str,
        channel_name: str,
        max_messages: int = 1000,
        start_date: Optional[datetime] = None,
        max_age_days: int = 365
    ) -> List[SlackMessage]:
        """
        Extract complete channel history with proper thread relationships.
        
        Args:
            channel_id: Slack channel ID
            channel_name: Channel name for context
            max_messages: Maximum messages to extract (to handle rate limits)
            start_date: Optional start date (defaults to 1 year ago for initial embedding)
            max_age_days: Maximum age of messages to include (default: 365 days)
            
        Returns:
            List of SlackMessage objects with proper thread relationships
        """
        try:
            logger.info(f"Starting complete extraction from channel {channel_name} ({channel_id})")
            
            # Set default start date with 1-year limit for initial embedding
            if start_date is None:
                start_date = datetime.now() - timedelta(days=max_age_days)
                logger.info(f"Using 1-year lookback for initial embedding: {start_date.strftime('%Y-%m-%d')}")
            
            # Enforce maximum age limit
            earliest_allowed = datetime.now() - timedelta(days=max_age_days)
            if start_date < earliest_allowed:
                start_date = earliest_allowed
                logger.info(f"Applied 1-year age limit, adjusted start date to: {start_date.strftime('%Y-%m-%d')}")
            
            # Extract all messages first
            all_messages = await self._extract_messages_with_pagination(
                channel_id, 
                start_date, 
                max_messages
            )
            
            # Build thread relationships
            threaded_messages = await self._build_thread_relationships(all_messages, channel_id)
            
            # Sort messages chronologically, preserving thread order
            sorted_messages = self._sort_messages_with_threads(threaded_messages)
            
            logger.info(f"Successfully extracted {len(sorted_messages)} messages with proper thread relationships")
            return sorted_messages
            
        except Exception as e:
            logger.error(f"Error in complete channel extraction: {e}")
            return []
    
    async def _extract_messages_with_pagination(
        self,
        channel_id: str,
        start_date: datetime,
        max_messages: int
    ) -> List[Dict[str, Any]]:
        """Extract messages with pagination and rate limiting"""
        
        messages = []
        cursor = None
        oldest_ts = str(start_date.timestamp())
        call_count = 0
        max_calls = max_messages // 100  # Limit API calls
        
        logger.info(f"Extracting messages from {start_date.isoformat()}, max {max_calls} API calls")
        
        while call_count < max_calls:
            try:
                # Exponential backoff based on call count
                if call_count > 0:
                    delay = min(self.base_delay * (1.5 ** call_count), self.max_delay)
                    logger.info(f"Rate limiting delay: {delay:.1f}s (call {call_count + 1})")
                    await asyncio.sleep(delay)
                
                response = self.client.conversations_history(
                    channel=channel_id,
                    limit=100,
                    oldest=oldest_ts,
                    cursor=cursor,
                    include_all_metadata=True
                )
                
                if not response["ok"]:
                    logger.error(f"Slack API error: {response.get('error')}")
                    break
                
                batch_messages = response.get("messages", [])
                if not batch_messages:
                    logger.info("No more messages found")
                    break
                
                # Filter and add messages
                valid_messages = [
                    msg for msg in batch_messages 
                    if self._is_valid_message(msg)
                ]
                
                messages.extend(valid_messages)
                call_count += 1
                
                logger.info(f"Extracted {len(valid_messages)} valid messages (total: {len(messages)})")
                
                # Check for more messages
                if not response.get("has_more", False):
                    logger.info("No more pages available")
                    break
                
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    logger.info("No next cursor available")
                    break
                
            except SlackApiError as e:
                if e.response["error"] == "rate_limited":
                    retry_after = int(e.response.get("headers", {}).get("Retry-After", 60))
                    logger.warning(f"Rate limited! Waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error(f"Slack API error: {e.response['error']}")
                    break
            
            except Exception as e:
                logger.error(f"Error during message extraction: {e}")
                break
        
        logger.info(f"Completed extraction: {len(messages)} messages, {call_count} API calls")
        return messages
    
    async def _build_thread_relationships(
        self, 
        messages: List[Dict[str, Any]], 
        channel_id: str
    ) -> List[SlackMessage]:
        """Build proper thread relationships and extract thread replies"""
        
        enhanced_messages = []
        thread_parents = {}  # Map thread_ts to parent message
        
        # First pass: Process parent messages and identify threads
        for raw_msg in messages:
            enhanced_msg = await self._create_enhanced_message(raw_msg, channel_id)
            if enhanced_msg:
                enhanced_messages.append(enhanced_msg)
                
                # Track thread parents
                if enhanced_msg.reply_count > 0:
                    thread_parents[enhanced_msg.ts] = enhanced_msg
        
        # Second pass: Extract thread replies for each parent
        thread_replies = []
        for thread_ts, parent_msg in thread_parents.items():
            logger.info(f"Extracting {parent_msg.reply_count} replies for thread {thread_ts}")
            
            replies = await self._extract_thread_replies(channel_id, thread_ts, parent_msg)
            thread_replies.extend(replies)
            
            # Rate limiting between thread extractions
            await asyncio.sleep(self.base_delay)
        
        # Combine parent messages and replies
        all_messages = enhanced_messages + thread_replies
        
        logger.info(f"Built relationships: {len(enhanced_messages)} parents + {len(thread_replies)} replies = {len(all_messages)} total")
        return all_messages
    
    async def _extract_thread_replies(
        self, 
        channel_id: str, 
        thread_ts: str, 
        parent_msg: SlackMessage
    ) -> List[SlackMessage]:
        """Extract all replies for a specific thread"""
        
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000
            )
            
            if not response["ok"]:
                logger.error(f"Failed to get thread replies: {response.get('error')}")
                return []
            
            thread_messages = response.get("messages", [])
            replies = []
            
            # Skip the first message (parent) and process replies
            for i, raw_reply in enumerate(thread_messages[1:], 1):
                enhanced_reply = await self._create_enhanced_message(
                    raw_reply, 
                    channel_id,
                    thread_ts=thread_ts,
                    parent_message_id=parent_msg.id,
                    thread_position=i
                )
                
                if enhanced_reply:
                    replies.append(enhanced_reply)
            
            logger.info(f"Extracted {len(replies)} replies for thread {thread_ts}")
            return replies
            
        except Exception as e:
            logger.error(f"Error extracting thread replies: {e}")
            return []
    
    async def _create_enhanced_message(
        self,
        raw_message: Dict[str, Any],
        channel_id: str,
        thread_ts: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        thread_position: int = 0
    ) -> Optional[SlackMessage]:
        """Create enhanced message with complete metadata"""
        
        try:
            # Skip invalid messages
            if not self._is_valid_message(raw_message):
                return None
            
            # Extract basic info
            ts = raw_message.get("ts")
            text = raw_message.get("text", "").strip()
            user_id = raw_message.get("user")
            
            # Get cached user and channel info
            user_info = await self._get_cached_user_info(user_id)
            channel_info = await self._get_cached_channel_info(channel_id)
            
            # Create enhanced message
            message = SlackMessage(
                id=f"{channel_id}_{ts}",
                text=text,
                timestamp=datetime.fromtimestamp(float(ts)),
                ts=ts,
                user_id=user_id or "unknown",
                user_name=user_info.get("real_name") or user_info.get("name", "Unknown User"),
                user_email=user_info.get("profile", {}).get("email", ""),
                channel_id=channel_id,
                channel_name=channel_info.get("name", "unknown-channel"),
                channel_purpose=channel_info.get("purpose", {}).get("value", ""),
                thread_ts=thread_ts or raw_message.get("thread_ts"),
                parent_message_id=parent_message_id,
                is_thread_reply=thread_ts is not None,
                thread_position=thread_position,
                reply_count=raw_message.get("reply_count", 0),
                reactions=raw_message.get("reactions", []),
                files=raw_message.get("files", []),
                attachments=raw_message.get("attachments", [])
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating enhanced message: {e}")
            return None
    
    def _is_valid_message(self, message: Dict[str, Any]) -> bool:
        """Check if message should be processed"""
        
        # Skip bot messages
        if message.get("bot_id") or message.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
            return False
        
        # Skip empty messages
        text = message.get("text", "").strip()
        if not text or len(text) < 3:
            return False
        
        # Must have timestamp
        if not message.get("ts"):
            return False
        
        return True
    
    async def _get_cached_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user info with caching"""
        
        if not user_id:
            return {}
        
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        try:
            response = self.client.users_info(user=user_id)
            if response["ok"]:
                user_info = response["user"]
                self.user_cache[user_id] = user_info
                return user_info
            
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
        
        # Cache empty result to avoid repeated failures
        self.user_cache[user_id] = {}
        return {}
    
    async def _get_cached_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel info with caching"""
        
        if channel_id in self.channel_cache:
            return self.channel_cache[channel_id]
        
        try:
            response = self.client.conversations_info(channel=channel_id)
            if response["ok"]:
                channel_info = response["channel"]
                self.channel_cache[channel_id] = channel_info
                return channel_info
            
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_id}: {e}")
        
        # Cache empty result
        self.channel_cache[channel_id] = {}
        return {}
    
    def _sort_messages_with_threads(self, messages: List[SlackMessage]) -> List[SlackMessage]:
        """Sort messages chronologically while preserving thread order"""
        
        # Separate parent messages and replies
        parents = [msg for msg in messages if not msg.is_thread_reply]
        replies = [msg for msg in messages if msg.is_thread_reply]
        
        # Sort parents by timestamp
        parents.sort(key=lambda x: x.timestamp)
        
        # Group replies by thread
        thread_groups = {}
        for reply in replies:
            thread_ts = reply.thread_ts
            if thread_ts not in thread_groups:
                thread_groups[thread_ts] = []
            thread_groups[thread_ts].append(reply)
        
        # Sort replies within each thread by position
        for thread_ts in thread_groups:
            thread_groups[thread_ts].sort(key=lambda x: x.thread_position)
        
        # Interleave parents and their replies in chronological order
        sorted_messages = []
        
        for parent in parents:
            sorted_messages.append(parent)
            
            # Add any replies for this parent
            if parent.ts in thread_groups:
                sorted_messages.extend(thread_groups[parent.ts])
        
        logger.info(f"Sorted {len(sorted_messages)} messages with proper thread nesting")
        return sorted_messages
    
    def get_message_summary(self, messages: List[SlackMessage]) -> Dict[str, Any]:
        """Get summary statistics for extracted messages"""
        
        if not messages:
            return {"total": 0}
        
        parent_count = sum(1 for msg in messages if not msg.is_thread_reply)
        reply_count = sum(1 for msg in messages if msg.is_thread_reply)
        thread_count = len(set(msg.thread_ts for msg in messages if msg.thread_ts))
        
        users = set(msg.user_name for msg in messages)
        date_range = {
            "earliest": min(msg.timestamp for msg in messages),
            "latest": max(msg.timestamp for msg in messages)
        }
        
        return {
            "total": len(messages),
            "parent_messages": parent_count,
            "thread_replies": reply_count,
            "threads": thread_count,
            "unique_users": len(users),
            "users": list(users),
            "date_range": date_range
        }