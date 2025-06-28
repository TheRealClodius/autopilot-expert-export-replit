"""
Adaptive Progress Tracking Service

Provides real-time progress updates for multi-agent operations with intelligent
natural language formatting and error handling integration.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, Union, Awaitable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ProgressEventType(Enum):
    """Types of progress events that can be emitted"""
    THINKING = "thinking"
    SEARCHING = "searching"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETING = "completing"
    ERROR = "error"
    WARNING = "warning"
    RETRY = "retry"
    SUCCESS = "success"


class ProgressEvent:
    """Represents a single progress event with context"""
    
    def __init__(
        self,
        event_type: ProgressEventType,
        action: str,
        context: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_type = event_type
        self.action = action
        self.context = context
        self.details = details or {}
        self.timestamp = timestamp or datetime.now()
        
    def to_natural_language(self) -> str:
        """Convert progress event to natural language message"""
        
        # Contextual and explicit action phrases (no emojis)
        action_phrases = {
            ProgressEventType.THINKING: {
                "analyzing": "Analyzing your request to understand what you need",
                "planning": "Planning the best approach to answer your question",
                "understanding": "Understanding the context and requirements",
                "preparing": "Preparing to gather the information you need"
            },
            ProgressEventType.SEARCHING: {
                "vector_search": "Searching through internal knowledge base",
                "perplexity_search": "Searching the real-time web",
                "document_search": "Looking through project documentation",
                "memory_search": "Reviewing conversation history for context",
                "knowledge_lookup": "Looking up relevant information in our knowledge base"
            },
            ProgressEventType.PROCESSING: {
                "analyzing_results": "Analyzing the search results I found",
                "filtering_results": "Filtering through search results for relevance",
                "gathering_info": "Gathering and organizing relevant information",
                "synthesizing": "Synthesizing information from multiple sources",
                "compiling": "Compiling the most relevant findings"
            },
            ProgressEventType.GENERATING: {
                "response_generation": "Crafting a comprehensive response based on my findings",
                "answer_preparation": "Preparing your answer with the gathered information",
                "formatting": "Formatting the response for clarity",
                "finalizing": "Finalizing your response with all relevant details"
            },
            ProgressEventType.ERROR: {
                "api_error": "Encountered an issue with external service",
                "search_error": "Hit an issue while searching for information",
                "processing_error": "Ran into difficulty processing the results",
                "connection_error": "Experiencing connectivity issues",
                "timeout_error": "Request took longer than expected"
            },
            ProgressEventType.WARNING: {
                "limited_results": "Found limited results, expanding search scope",
                "api_timeout": "Search is taking longer than expected",
                "partial_failure": "Some sources unavailable, using available alternatives",
                "fallback": "Primary method unavailable, switching to backup approach"
            },
            ProgressEventType.RETRY: {
                "retry_search": "Retrying search with refined parameters",
                "retry_api": "Retrying the request after a brief pause",
                "retry_processing": "Attempting to process results again",
                "retry_generation": "Regenerating response with alternative approach"
            }
        }
        
        # Get base phrase
        type_phrases = action_phrases.get(self.event_type, {})
        base_phrase = type_phrases.get(self.action, self.action.replace("_", " ").title())
        
        # Build contextual and explicit message
        if self.context:
            if self.event_type == ProgressEventType.ERROR:
                message = f"{base_phrase}: {self.context}"
            elif self.event_type == ProgressEventType.WARNING:
                message = f"{base_phrase} ({self.context})"
            else:
                # Create more explicit and contextual messages
                if "search" in self.action.lower():
                    if "perplexity" in self.action:
                        message = f"Searching for information about {self.context} on the web"
                    elif "vector" in self.action:
                        message = f"Looking internally for information about {self.context}"
                    else:
                        message = f"{base_phrase} for {self.context}"
                elif "analyzing" in self.action.lower():
                    message = f"Analyzing {self.context}"
                elif "processing" in self.action.lower() or "compiling" in self.action.lower():
                    message = f"{base_phrase} about {self.context}"
                else:
                    message = f"{base_phrase} - {self.context}"
        else:
            message = base_phrase
        
        # Format with italic text for Slack (no emojis)
        return f"_{message}_"


class ProgressTracker:
    """
    Manages progress tracking with adaptive natural language formatting
    and real-time update capabilities.
    """
    
    def __init__(self, update_callback: Optional[Union[Callable[[str], None], Callable[[str], Awaitable[None]]]] = None):
        """
        Initialize progress tracker.
        
        Args:
            update_callback: Function to call when progress updates (e.g., Slack message update)
        """
        self.update_callback = update_callback
        self.events = []
        self.last_update_time = None
        self.update_debounce_seconds = 0.5  # Minimum time between updates
        self.is_updating = False
        
    async def emit_progress(
        self,
        event_type: ProgressEventType,
        action: str,
        context: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a progress event and trigger update if callback is set.
        
        Args:
            event_type: Type of progress event
            action: Specific action being performed
            context: Additional context about the action
            details: Optional detailed information
        """
        try:
            # Create progress event
            event = ProgressEvent(
                event_type=event_type,
                action=action,
                context=context,
                details=details
            )
            
            # Store event
            self.events.append(event)
            
            # Log the event
            logger.info(f"Progress: {event.to_natural_language()}")
            
            # Trigger update if callback is available
            if self.update_callback and not self.is_updating:
                await self._trigger_update(event)
                
        except Exception as e:
            logger.error(f"Error emitting progress event: {e}")
    
    async def _trigger_update(self, event: ProgressEvent) -> None:
        """Trigger progress update with debouncing"""
        try:
            # Check debounce timing
            now = datetime.now()
            if (self.last_update_time and 
                (now - self.last_update_time).total_seconds() < self.update_debounce_seconds):
                return
            
            self.is_updating = True
            
            # Call update callback with natural language message
            message = event.to_natural_language()
            
            if self.update_callback:
                if asyncio.iscoroutinefunction(self.update_callback):
                    await self.update_callback(message)
                else:
                    self.update_callback(message)
                
            self.last_update_time = now
            
        except Exception as e:
            logger.error(f"Error triggering progress update: {e}")
        finally:
            self.is_updating = False
    
    def get_latest_event(self) -> Optional[ProgressEvent]:
        """Get the most recent progress event"""
        return self.events[-1] if self.events else None
    
    def get_event_history(self) -> list[ProgressEvent]:
        """Get full event history"""
        return self.events.copy()
    
    def clear_events(self) -> None:
        """Clear event history"""
        self.events.clear()
        self.last_update_time = None


# Convenience functions for common progress patterns
async def emit_thinking(tracker: ProgressTracker, action: str = "analyzing", context: Optional[str] = None):
    """Emit thinking progress event"""
    await tracker.emit_progress(ProgressEventType.THINKING, action, context)

async def emit_searching(tracker: ProgressTracker, action: str = "vector_search", context: Optional[str] = None):
    """Emit searching progress event"""
    await tracker.emit_progress(ProgressEventType.SEARCHING, action, context)

async def emit_processing(tracker: ProgressTracker, action: str = "analyzing_results", context: Optional[str] = None):
    """Emit processing progress event"""
    await tracker.emit_progress(ProgressEventType.PROCESSING, action, context)

async def emit_generating(tracker: ProgressTracker, action: str = "response_generation", context: Optional[str] = None):
    """Emit generating progress event"""
    await tracker.emit_progress(ProgressEventType.GENERATING, action, context)

async def emit_error(tracker: ProgressTracker, action: str = "api_error", context: Optional[str] = None):
    """Emit error progress event"""
    await tracker.emit_progress(ProgressEventType.ERROR, action, context)

async def emit_warning(tracker: ProgressTracker, action: str = "limited_results", context: Optional[str] = None):
    """Emit warning progress event"""
    await tracker.emit_progress(ProgressEventType.WARNING, action, context)

async def emit_retry(tracker: ProgressTracker, action: str = "retry_api", context: Optional[str] = None):
    """Emit retry progress event"""
    await tracker.emit_progress(ProgressEventType.RETRY, action, context)