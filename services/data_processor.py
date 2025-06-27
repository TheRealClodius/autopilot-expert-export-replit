"""
Data Processor Service - Cleans and formats Slack messages for embedding.
Handles text preprocessing, metadata extraction, and chunking strategies.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Service for processing and cleaning Slack message data.
    Prepares messages for embedding and vector storage.
    """
    
    def __init__(self):
        self.max_chunk_size = 1000
        self.chunk_overlap = 200
        
    async def process_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of Slack messages for embedding.
        
        Args:
            messages: List of raw Slack messages
            
        Returns:
            List of processed messages ready for embedding
        """
        try:
            logger.info(f"Processing {len(messages)} messages...")
            
            processed_messages = []
            
            for message in messages:
                try:
                    processed_message = await self._process_single_message(message)
                    if processed_message:
                        processed_messages.append(processed_message)
                except Exception as e:
                    logger.error(f"Error processing message {message.get('id', 'unknown')}: {e}")
                    continue
            
            # Remove duplicates
            processed_messages = self._remove_duplicates(processed_messages)
            
            logger.info(f"Successfully processed {len(processed_messages)} messages")
            return processed_messages
            
        except Exception as e:
            logger.error(f"Error processing message batch: {e}")
            return []
    
    async def _process_single_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single Slack message.
        
        Args:
            message: Raw Slack message
            
        Returns:
            Processed message or None if message should be skipped
        """
        try:
            # Clean and normalize text
            text = self._clean_message_text(message.get("text", ""))
            
            if not text or len(text.strip()) < 10:  # Skip very short messages
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(message)
            
            # Create content for embedding
            content = self._create_embeddable_content(text, metadata)
            
            # Generate unique ID
            message_id = self._generate_message_id(message)
            
            processed_message = {
                "id": message_id,
                "content": content,
                "text": text,
                "metadata": metadata,
                "timestamp": message.get("timestamp"),
                "processed_at": datetime.now().isoformat()
            }
            
            # Handle long messages by chunking
            if len(content) > self.max_chunk_size:
                return await self._chunk_long_message(processed_message)
            
            return processed_message
            
        except Exception as e:
            logger.error(f"Error processing single message: {e}")
            return None
    
    def _clean_message_text(self, text: str) -> str:
        """
        Clean and normalize message text.
        
        Args:
            text: Raw message text
            
        Returns:
            Cleaned text
        """
        try:
            if not text:
                return ""
            
            # Remove Slack-specific formatting
            # Remove user mentions but keep readable format
            text = re.sub(r'<@([A-Z0-9]+)>', r'@user', text)
            
            # Remove channel mentions but keep readable format
            text = re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', text)
            
            # Remove URL formatting but keep URL
            text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2 (\1)', text)
            text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
            
            # Remove email formatting
            text = re.sub(r'<mailto:([^|>]+)\|([^>]+)>', r'\2', text)
            text = re.sub(r'<mailto:([^>]+)>', r'\1', text)
            
            # Clean up multiple spaces and newlines
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Remove excessive punctuation
            text = re.sub(r'[!]{3,}', '!', text)
            text = re.sub(r'[?]{3,}', '?', text)
            text = re.sub(r'[.]{3,}', '...', text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning message text: {e}")
            return text
    
    def _extract_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from message.
        
        Args:
            message: Raw message dictionary
            
        Returns:
            Metadata dictionary
        """
        try:
            metadata = {
                "source": "slack",
                "channel_id": message.get("channel_id", ""),
                "channel_name": message.get("channel_name", ""),
                "channel_purpose": message.get("channel_purpose", ""),
                "user_id": message.get("user_id", ""),
                "user_name": message.get("user_name", ""),
                "user_email": message.get("user_email", ""),
                "timestamp": message.get("timestamp", ""),
                "is_thread_reply": message.get("is_thread_reply", False),
                "reply_count": message.get("reply_count", 0),
                "has_reactions": len(message.get("reactions", [])) > 0,
                "has_files": len(message.get("files", [])) > 0,
                "has_attachments": len(message.get("attachments", [])) > 0
            }
            
            # Add thread information if available
            if message.get("thread_ts"):
                metadata["thread_ts"] = message["thread_ts"]
            
            # Extract file information
            files = message.get("files", [])
            if files:
                metadata["file_types"] = [f.get("filetype", "unknown") for f in files]
                metadata["file_names"] = [f.get("name", "unknown") for f in files]
            
            # Extract reaction types
            reactions = message.get("reactions", [])
            if reactions:
                metadata["reaction_types"] = [r.get("name", "unknown") for r in reactions]
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {"source": "slack"}
    
    def _create_embeddable_content(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Create content optimized for embedding.
        
        Args:
            text: Cleaned message text
            metadata: Message metadata
            
        Returns:
            Content string for embedding
        """
        try:
            # Start with the main text
            content_parts = [text]
            
            # Add contextual information
            if metadata.get("channel_name"):
                content_parts.append(f"Channel: {metadata['channel_name']}")
            
            if metadata.get("user_name"):
                content_parts.append(f"User: {metadata['user_name']}")
            
            # Add channel purpose if available and relevant
            channel_purpose = metadata.get("channel_purpose", "").strip()
            if channel_purpose and len(channel_purpose) > 10:
                content_parts.append(f"Context: {channel_purpose}")
            
            # Add thread context
            if metadata.get("is_thread_reply"):
                content_parts.append("(Thread reply)")
            elif metadata.get("reply_count", 0) > 0:
                content_parts.append(f"(Has {metadata['reply_count']} replies)")
            
            # Add file context
            if metadata.get("has_files"):
                file_types = metadata.get("file_types", [])
                if file_types:
                    content_parts.append(f"Files: {', '.join(file_types)}")
            
            return " | ".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error creating embeddable content: {e}")
            return text
    
    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """
        Generate a unique, deterministic ID for the message.
        
        Args:
            message: Message dictionary
            
        Returns:
            Unique message ID
        """
        try:
            # Create ID from channel, timestamp, and user
            id_components = [
                message.get("channel_id", ""),
                message.get("ts", ""),
                message.get("user_id", "")
            ]
            
            # Add thread timestamp if it's a threaded message
            if message.get("thread_ts"):
                id_components.append(message["thread_ts"])
            
            id_string = "_".join(id_components)
            
            # Create hash for consistent, shorter ID
            message_hash = hashlib.md5(id_string.encode()).hexdigest()[:12]
            
            return f"slack_{message_hash}"
            
        except Exception as e:
            logger.error(f"Error generating message ID: {e}")
            return f"slack_{datetime.now().timestamp()}"
    
    async def _chunk_long_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk long messages into smaller pieces.
        
        Args:
            message: Processed message that's too long
            
        Returns:
            List of chunked messages
        """
        try:
            content = message["content"]
            text = message["text"]
            
            # Simple sentence-based chunking
            sentences = re.split(r'[.!?]+', text)
            
            chunks = []
            current_chunk = ""
            current_content = ""
            chunk_index = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if adding this sentence would exceed chunk size
                test_chunk = current_chunk + " " + sentence if current_chunk else sentence
                test_content = self._create_embeddable_content(test_chunk, message["metadata"])
                
                if len(test_content) > self.max_chunk_size and current_chunk:
                    # Save current chunk
                    chunk_message = message.copy()
                    chunk_message["id"] = f"{message['id']}_chunk_{chunk_index}"
                    chunk_message["text"] = current_chunk
                    chunk_message["content"] = current_content
                    chunk_message["metadata"]["chunk_index"] = chunk_index
                    chunk_message["metadata"]["is_chunk"] = True
                    
                    chunks.append(chunk_message)
                    
                    # Start new chunk with overlap
                    overlap_sentences = sentences[max(0, len(sentences) - 2):]
                    current_chunk = sentence
                    current_content = test_content
                    chunk_index += 1
                else:
                    current_chunk = test_chunk
                    current_content = test_content
            
            # Add final chunk
            if current_chunk:
                chunk_message = message.copy()
                chunk_message["id"] = f"{message['id']}_chunk_{chunk_index}"
                chunk_message["text"] = current_chunk
                chunk_message["content"] = current_content
                chunk_message["metadata"]["chunk_index"] = chunk_index
                chunk_message["metadata"]["is_chunk"] = True
                
                chunks.append(chunk_message)
            
            logger.info(f"Chunked long message into {len(chunks)} pieces")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking long message: {e}")
            return [message]  # Return original if chunking fails
    
    def _remove_duplicates(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate messages based on ID.
        
        Args:
            messages: List of processed messages
            
        Returns:
            Deduplicated list of messages
        """
        try:
            seen_ids = set()
            unique_messages = []
            
            for message in messages:
                message_id = message.get("id")
                if message_id and message_id not in seen_ids:
                    seen_ids.add(message_id)
                    unique_messages.append(message)
            
            removed_count = len(messages) - len(unique_messages)
            if removed_count > 0:
                logger.info(f"Removed {removed_count} duplicate messages")
            
            return unique_messages
            
        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return messages
