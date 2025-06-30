"""
Token Management Service for precise token counting and context window optimization.
Uses tiktoken for accurate token counting with model-specific encoders.
"""

import tiktoken
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenizedMessage:
    """Container for a message with its token count and metadata"""
    speaker: str
    text: str
    token_count: int
    original_message: Dict[str, Any]
    formatted_text: str  # "Speaker: text" format

class TokenManager:
    """
    Advanced token management service providing precise token counting and intelligent truncation.
    Supports multiple models and provides smooth transitions between live and summarized memory.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        Initialize token manager with model-specific encoder
        
        Args:
            model_name: Model name for tiktoken encoder (gpt-4, gpt-3.5-turbo, etc.)
        """
        try:
            # Get encoding for the specified model
            self.encoding = tiktoken.encoding_for_model(model_name)
            self.model_name = model_name
            logger.info(f"Token manager initialized with {model_name} encoding")
        except KeyError:
            # Fallback to cl100k_base encoding (used by GPT-4)
            logger.warning(f"Model {model_name} not found, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self.model_name = "gpt-4"
    
    def count_tokens(self, text: str) -> int:
        """
        Count exact tokens in text using model-specific tokenizer
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Exact token count
        """
        # Type validation to prevent non-string inputs
        if not isinstance(text, str):
            logger.warning(f"Non-string input to count_tokens: {type(text)}, returning 0 tokens")
            return 0
            
        if not text:
            return 0
        
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens with tiktoken: {e}")
            # Fallback to character-based approximation for robustness
            try:
                return len(text) // 4
            except Exception as fallback_e:
                logger.error(f"Even fallback token counting failed: {fallback_e}")
                return 0
    
    def tokenize_message(self, message: Dict[str, Any]) -> TokenizedMessage:
        """
        Convert a raw message into a tokenized message with exact token count
        
        Args:
            message: Raw message dictionary
            
        Returns:
            TokenizedMessage with precise token count
        """
        # Type validation for message input
        if not isinstance(message, dict):
            logger.warning(f"Non-dict input to tokenize_message: {type(message)}, using empty message")
            message = {"user_name": "Unknown", "text": ""}
        
        user_name = message.get("user_name", "Unknown")
        text = message.get("text", "")
        
        # Ensure text is string type
        if not isinstance(text, str):
            logger.warning(f"Non-string text in message: {type(text)}, converting to string")
            text = str(text) if text is not None else ""
        
        # Ensure user_name is string type  
        if not isinstance(user_name, str):
            logger.warning(f"Non-string user_name in message: {type(user_name)}, converting to string")
            user_name = str(user_name) if user_name is not None else "Unknown"
        
        # Determine speaker
        is_bot = user_name.lower() in ["bot", "autopilot", "assistant"]
        speaker = "Bot" if is_bot else "User"
        
        # Format message for context
        formatted_text = f"{speaker}: {text}"
        
        # Count exact tokens
        token_count = self.count_tokens(formatted_text)
        
        return TokenizedMessage(
            speaker=speaker,
            text=text,
            token_count=token_count,
            original_message=message,
            formatted_text=formatted_text
        )
    
    def build_token_managed_history(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: int,
        preserve_recent: int = 2
    ) -> Tuple[List[TokenizedMessage], List[TokenizedMessage], Dict[str, int]]:
        """
        Build token-managed history with intelligent truncation and smooth transition handling.
        
        Args:
            messages: List of raw messages (oldest first)
            max_tokens: Maximum tokens for live history
            preserve_recent: Number of most recent messages to always preserve
            
        Returns:
            Tuple of (messages_to_keep, messages_to_summarize, token_stats)
        """
        if not messages:
            return [], [], {"total_tokens": 0, "kept_messages": 0, "summarized_messages": 0}
        
        # Tokenize all messages
        tokenized_messages = [self.tokenize_message(msg) for msg in messages]
        
        # Always preserve the most recent messages
        recent_messages = tokenized_messages[-preserve_recent:] if len(tokenized_messages) >= preserve_recent else tokenized_messages
        older_messages = tokenized_messages[:-preserve_recent] if len(tokenized_messages) > preserve_recent else []
        
        # Calculate tokens for recent messages
        recent_tokens = sum(msg.token_count for msg in recent_messages)
        
        # If recent messages already exceed limit, we need to truncate even them
        if recent_tokens > max_tokens:
            logger.warning(f"Recent {preserve_recent} messages ({recent_tokens} tokens) exceed limit ({max_tokens} tokens)")
            # Keep only what fits, starting from most recent
            kept_messages = []
            current_tokens = 0
            
            for msg in reversed(recent_messages):
                if current_tokens + msg.token_count <= max_tokens:
                    kept_messages.insert(0, msg)
                    current_tokens += msg.token_count
                else:
                    # This message would exceed the limit
                    break
            
            # Everything else goes to summarization
            messages_to_summarize = [msg for msg in tokenized_messages if msg not in kept_messages]
            
            return kept_messages, messages_to_summarize, {
                "total_tokens": current_tokens,
                "kept_messages": len(kept_messages),
                "summarized_messages": len(messages_to_summarize)
            }
        
        # We have room for more than just recent messages
        available_tokens = max_tokens - recent_tokens
        kept_messages = recent_messages.copy()
        messages_to_summarize = []
        
        # Add older messages starting from most recent (working backwards)
        for msg in reversed(older_messages):
            if msg.token_count <= available_tokens:
                kept_messages.insert(0, msg)  # Insert at beginning to maintain order
                available_tokens -= msg.token_count
            else:
                # This message and all older ones need summarization
                remaining_older = older_messages[:older_messages.index(msg) + 1]
                messages_to_summarize = remaining_older
                break
        
        total_tokens = sum(msg.token_count for msg in kept_messages)
        
        return kept_messages, messages_to_summarize, {
            "total_tokens": total_tokens,
            "kept_messages": len(kept_messages),
            "summarized_messages": len(messages_to_summarize)
        }
    
    def format_messages_for_context(self, tokenized_messages: List[TokenizedMessage]) -> str:
        """
        Format tokenized messages into clean context string
        
        Args:
            tokenized_messages: List of tokenized messages
            
        Returns:
            Formatted context string
        """
        if not tokenized_messages:
            return ""
        
        return "\n".join(msg.formatted_text for msg in tokenized_messages)
    
    def calculate_context_tokens(self, 
                                summarized_history: str, 
                                live_history: str, 
                                current_query: str = "") -> Dict[str, int]:
        """
        Calculate total context tokens including all components
        
        Args:
            summarized_history: Long-term summary text
            live_history: Recent message history
            current_query: Current user query
            
        Returns:
            Dictionary with token breakdown
        """
        summary_tokens = self.count_tokens(summarized_history) if summarized_history else 0
        live_tokens = self.count_tokens(live_history) if live_history else 0
        query_tokens = self.count_tokens(current_query) if current_query else 0
        
        total_tokens = summary_tokens + live_tokens + query_tokens
        
        return {
            "summary_tokens": summary_tokens,
            "live_tokens": live_tokens,
            "query_tokens": query_tokens,
            "total_context_tokens": total_tokens
        }
    
    def suggest_summarization_candidates(self, 
                                       messages: List[Dict[str, Any]], 
                                       max_live_tokens: int) -> List[Dict[str, Any]]:
        """
        Suggest which messages should be moved to summarization for smooth transition
        
        Args:
            messages: List of raw messages
            max_live_tokens: Maximum tokens for live history
            
        Returns:
            List of messages that should be summarized
        """
        if len(messages) < 3:
            return []  # Don't summarize unless we have meaningful conversation
        
        tokenized_messages = [self.tokenize_message(msg) for msg in messages]
        total_tokens = sum(msg.token_count for msg in tokenized_messages)
        
        if total_tokens <= max_live_tokens:
            return []  # Everything fits
        
        # Find the oldest 2-3 messages that would create room
        candidates = []
        tokens_to_free = total_tokens - max_live_tokens + 200  # Add buffer
        freed_tokens = 0
        
        for msg in tokenized_messages:  # Start from oldest
            if freed_tokens < tokens_to_free and len(candidates) < 3:
                candidates.append(msg.original_message)
                freed_tokens += msg.token_count
            else:
                break
        
        return candidates
    
    def get_token_efficiency_stats(self, 
                                 old_char_estimate: int, 
                                 precise_token_count: int) -> Dict[str, Any]:
        """
        Compare old character-based estimation with precise token counting
        
        Args:
            old_char_estimate: Previous character-based token estimate
            precise_token_count: Actual token count
            
        Returns:
            Efficiency comparison statistics
        """
        if old_char_estimate == 0:
            return {"accuracy": 0, "efficiency_gain": 0, "token_difference": 0}
        
        accuracy = (1 - abs(old_char_estimate - precise_token_count) / old_char_estimate) * 100
        efficiency_gain = precise_token_count - old_char_estimate
        
        return {
            "old_estimate": old_char_estimate,
            "precise_count": precise_token_count,
            "accuracy_percentage": round(accuracy, 1),
            "efficiency_gain": efficiency_gain,
            "is_more_efficient": efficiency_gain < 0,
            "token_difference": abs(efficiency_gain)
        }