"""
Enhanced Data Processor - Handles SlackMessage objects with proper thread relationships.
Creates properly structured embeddings that preserve thread context and message ordering.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
from dataclasses import asdict

from services.external_apis.enhanced_slack_connector import SlackMessage

logger = logging.getLogger(__name__)

class EnhancedDataProcessor:
    """
    Enhanced processor for SlackMessage objects with proper thread context.
    """
    
    def __init__(self):
        self.max_chunk_size = 1500  # Increased for richer context
        self.chunk_overlap = 300
        
    async def process_slack_messages(self, messages: List[SlackMessage]) -> List[Dict[str, Any]]:
        """
        Process SlackMessage objects for embedding storage.
        
        Args:
            messages: List of SlackMessage objects with proper thread relationships
            
        Returns:
            List of processed messages ready for embedding
        """
        try:
            logger.info(f"Processing {len(messages)} SlackMessage objects...")
            
            processed_messages = []
            thread_contexts = self._build_thread_contexts(messages)
            
            for message in messages:
                try:
                    processed_message = await self._process_single_slack_message(
                        message, thread_contexts
                    )
                    if processed_message:
                        processed_messages.append(processed_message)
                        
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {e}")
                    continue
            
            # Remove duplicates by ID
            processed_messages = self._remove_duplicates_by_id(processed_messages)
            
            logger.info(f"Successfully processed {len(processed_messages)} messages")
            return processed_messages
            
        except Exception as e:
            logger.error(f"Error processing SlackMessage batch: {e}")
            return []
    
    def _build_thread_contexts(self, messages: List[SlackMessage]) -> Dict[str, Dict[str, Any]]:
        """Build context maps for thread relationships"""
        
        thread_contexts = {}
        
        # Group messages by thread
        threads = {}
        for msg in messages:
            if msg.thread_ts:
                if msg.thread_ts not in threads:
                    threads[msg.thread_ts] = []
                threads[msg.thread_ts].append(msg)
        
        # Build context for each thread
        for thread_ts, thread_messages in threads.items():
            # Sort by thread position
            thread_messages.sort(key=lambda x: x.thread_position)
            
            # Find parent (position 0 or not in thread_messages)
            parent = None
            for msg in messages:
                if msg.ts == thread_ts and not msg.is_thread_reply:
                    parent = msg
                    break
            
            thread_contexts[thread_ts] = {
                "parent": parent,
                "replies": [msg for msg in thread_messages if msg.is_thread_reply],
                "total_replies": len([msg for msg in thread_messages if msg.is_thread_reply]),
                "participants": list(set(msg.user_name for msg in thread_messages))
            }
        
        return thread_contexts
    
    async def _process_single_slack_message(
        self, 
        message: SlackMessage, 
        thread_contexts: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Process a single SlackMessage with thread context"""
        
        try:
            # Skip very short messages
            if len(message.text.strip()) < 10:
                return None
            
            # Create rich content for embedding
            content = self._create_rich_embeddable_content(message, thread_contexts)
            
            # Extract comprehensive metadata
            metadata = self._extract_comprehensive_metadata(message, thread_contexts)
            
            # Generate deterministic ID
            message_id = self._generate_deterministic_id(message)
            
            processed_message = {
                "id": message_id,
                "content": content,
                "text": message.text,
                "metadata": metadata,
                "timestamp": message.timestamp.isoformat(),
                "ts": message.ts,
                "processed_at": datetime.now().isoformat(),
                "message_type": "thread_reply" if message.is_thread_reply else "parent_message"
            }
            
            # Handle long content by chunking
            if len(content) > self.max_chunk_size:
                return await self._chunk_long_content(processed_message, message)
            
            return processed_message
            
        except Exception as e:
            logger.error(f"Error processing SlackMessage: {e}")
            return None
    
    def _create_rich_embeddable_content(
        self, 
        message: SlackMessage, 
        thread_contexts: Dict[str, Dict[str, Any]]
    ) -> str:
        """Create rich content for embedding with thread context"""
        
        content_parts = []
        
        # Add main message text
        content_parts.append(message.text)
        
        # Add thread context if this is a thread reply
        if message.is_thread_reply and message.thread_ts in thread_contexts:
            thread_context = thread_contexts[message.thread_ts]
            parent = thread_context["parent"]
            
            if parent:
                content_parts.append(f"[Thread Reply to: {parent.text[:100]}...]")
                content_parts.append(f"[Thread Position: {message.thread_position}/{thread_context['total_replies']}]")
                
                # Add participants context
                participants = thread_context["participants"]
                if len(participants) > 1:
                    content_parts.append(f"[Thread Participants: {', '.join(participants)}]")
        
        # Add user context
        if message.user_name and message.user_name != "Unknown User":
            content_parts.append(f"Author: {message.user_name}")
        
        # Add channel context
        if message.channel_name and message.channel_name != "unknown-channel":
            content_parts.append(f"Channel: #{message.channel_name}")
        
        # Add channel purpose for additional context
        if message.channel_purpose and len(message.channel_purpose) > 10:
            content_parts.append(f"Channel Context: {message.channel_purpose}")
        
        # Add temporal context
        time_str = message.timestamp.strftime("%Y-%m-%d %H:%M")
        content_parts.append(f"Time: {time_str}")
        
        # Add reaction context
        if message.reactions:
            reaction_names = [r.get("name", "unknown") for r in message.reactions]
            content_parts.append(f"Reactions: {', '.join(reaction_names)}")
        
        # Add file context
        if message.files:
            file_types = [f.get("filetype", "unknown") for f in message.files]
            content_parts.append(f"Files: {', '.join(set(file_types))}")
        
        return " | ".join(content_parts)
    
    def _extract_comprehensive_metadata(
        self, 
        message: SlackMessage, 
        thread_contexts: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract comprehensive metadata including thread relationships"""
        
        metadata = {
            # Basic message info
            "source": "slack",
            "message_id": message.id,
            "channel_id": message.channel_id,
            "channel_name": message.channel_name,
            "channel_purpose": message.channel_purpose,
            "user_id": message.user_id,
            "user_name": message.user_name,
            "user_email": message.user_email,
            "timestamp": message.timestamp.isoformat(),
            "ts": message.ts,
            
            # Thread information
            "is_thread_reply": message.is_thread_reply,
            "thread_ts": message.thread_ts,
            "parent_message_id": message.parent_message_id,
            "thread_position": message.thread_position,
            "reply_count": message.reply_count,
            
            # Content metadata
            "message_length": len(message.text),
            "has_reactions": len(message.reactions) > 0,
            "has_files": len(message.files) > 0,
            "has_attachments": len(message.attachments) > 0,
            
            # Temporal metadata
            "day_of_week": message.timestamp.strftime("%A"),
            "hour_of_day": message.timestamp.hour,
            "date": message.timestamp.date().isoformat()
        }
        
        # Add thread context metadata
        if message.thread_ts and message.thread_ts in thread_contexts:
            thread_context = thread_contexts[message.thread_ts]
            metadata.update({
                "thread_participant_count": len(thread_context["participants"]),
                "thread_participants": thread_context["participants"],
                "thread_total_replies": thread_context["total_replies"]
            })
            
            # Add parent message info for thread replies
            if message.is_thread_reply and thread_context["parent"]:
                parent = thread_context["parent"]
                metadata.update({
                    "parent_user_name": parent.user_name,
                    "parent_text_preview": parent.text[:100],
                    "parent_timestamp": parent.timestamp.isoformat()
                })
        
        # Add reaction details
        if message.reactions:
            metadata["reaction_types"] = [r.get("name", "unknown") for r in message.reactions]
            metadata["reaction_count"] = sum(r.get("count", 0) for r in message.reactions)
        
        # Add file details
        if message.files:
            metadata["file_types"] = [f.get("filetype", "unknown") for f in message.files]
            metadata["file_names"] = [f.get("name", "unknown") for f in message.files]
        
        return metadata
    
    def _generate_deterministic_id(self, message: SlackMessage) -> str:
        """Generate a deterministic ID for the message"""
        
        # Use channel_id + ts for uniqueness
        base_id = f"{message.channel_id}_{message.ts}"
        
        # Add thread position for thread replies to ensure uniqueness
        if message.is_thread_reply:
            base_id += f"_reply_{message.thread_position}"
        
        return base_id
    
    async def _chunk_long_content(
        self, 
        processed_message: Dict[str, Any], 
        original_message: SlackMessage
    ) -> Dict[str, Any]:
        """Handle long content by intelligent chunking"""
        
        content = processed_message["content"]
        
        # Simple chunking for now - could be enhanced with semantic chunking
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.max_chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                last_period = content.rfind(".", start, end)
                if last_period > start:
                    end = last_period + 1
            
            chunk = content[start:end]
            chunks.append(chunk)
            start = max(start + self.max_chunk_size - self.chunk_overlap, end)
        
        # For now, return the first chunk with metadata indicating truncation
        first_chunk = chunks[0]
        processed_message["content"] = first_chunk
        processed_message["metadata"]["is_chunked"] = True
        processed_message["metadata"]["total_chunks"] = len(chunks)
        processed_message["metadata"]["chunk_index"] = 0
        
        return processed_message
    
    def _remove_duplicates_by_id(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate messages by ID"""
        
        seen_ids = set()
        unique_messages = []
        
        for message in messages:
            message_id = message.get("id")
            if message_id and message_id not in seen_ids:
                seen_ids.add(message_id)
                unique_messages.append(message)
        
        if len(unique_messages) != len(messages):
            logger.info(f"Removed {len(messages) - len(unique_messages)} duplicate messages")
        
        return unique_messages
    
    def get_processing_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of processed messages"""
        
        if not messages:
            return {"total": 0}
        
        parent_count = sum(1 for msg in messages if msg.get("message_type") == "parent_message")
        reply_count = sum(1 for msg in messages if msg.get("message_type") == "thread_reply")
        
        users = set(msg.get("metadata", {}).get("user_name") for msg in messages)
        users.discard(None)
        users.discard("Unknown User")
        
        channels = set(msg.get("metadata", {}).get("channel_name") for msg in messages)
        channels.discard(None)
        channels.discard("unknown-channel")
        
        return {
            "total": len(messages),
            "parent_messages": parent_count,
            "thread_replies": reply_count,
            "unique_users": len(users),
            "unique_channels": len(channels),
            "users": list(users),
            "channels": list(channels)
        }