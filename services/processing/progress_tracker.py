"""
Progress Tracker - Enhanced for fluid reasoning display.
Manages real-time progress updates with sophisticated message editing for reasoning transparency.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)

class ProgressEventType(Enum):
    """Types of progress events for sophisticated tracking"""
    ANALYZING = "analyzing"
    REASONING = "reasoning"
    FLUID_THINKING = "fluid_thinking"
    LIVE_REASONING = "live_reasoning"
    SEARCHING = "searching"
    PROCESSING = "processing"
    GENERATING = "generating"
    SYNTHESIZING = "synthesizing"
    OBSERVING = "observing"
    REPLANNING = "replanning"
    ERROR = "error"
    WARNING = "warning"
    RETRY = "retry"
    THINKING = "thinking"
    CONSIDERING = "considering"

class ReasoningStageManager:
    """Manages reasoning stage progression for smooth message editing"""
    
    def __init__(self):
        self.current_stage = 0
        self.stage_history = []
        self.reasoning_snippets = []
        self.last_update_time = 0
        self.min_update_interval = 1.0  # Minimum 1 second between updates
        
    def should_update_message(self, force: bool = False) -> bool:
        """Determine if message should be updated based on timing and content"""
        current_time = time.time()
        if force or (current_time - self.last_update_time) >= self.min_update_interval:
            self.last_update_time = current_time
            return True
        return False
    
    def add_reasoning_snippet(self, snippet: str, stage_hint: str = None):
        """Add reasoning snippet and potentially advance stage"""
        self.reasoning_snippets.append({
            "text": snippet,
            "timestamp": time.time(),
            "stage_hint": stage_hint
        })
        
        # Keep only recent snippets
        if len(self.reasoning_snippets) > 10:
            self.reasoning_snippets = self.reasoning_snippets[-5:]
    
    def get_current_display_message(self, base_message: str) -> str:
        """Get the current message to display with reasoning context"""
        if self.reasoning_snippets:
            # Get the most recent meaningful snippet
            recent_snippet = self.reasoning_snippets[-1]["text"]
            if len(recent_snippet.strip()) > 15:  # Only show substantial content
                return f"{base_message}\n\n_\"{recent_snippet[:120]}...\"_"
        
        return base_message

class ProgressTracker:
    """
    Enhanced Progress Tracker with fluid reasoning display capabilities.
    Manages real-time progress updates with message editing for reasoning transparency.
    """
    
    def __init__(self, update_callback: Optional[Callable] = None):
        self.update_callback = update_callback
        self.current_message = ""
        self.last_update_time = 0
        self.event_history: List[Dict[str, Any]] = []
        self.reasoning_manager = ReasoningStageManager()
        self.is_in_reasoning_mode = False
        
    async def emit_progress(self, event_type: ProgressEventType, action: str, details: str = "", 
                          reasoning_snippet: str = None, force_update: bool = False):
        """Enhanced progress emission with reasoning snippet support"""
        timestamp = datetime.now().isoformat()
        
        # Create event record
        event = {
            "timestamp": timestamp,
            "event_type": event_type.value,
            "action": action,
            "details": details,
            "reasoning_snippet": reasoning_snippet
        }
        
        self.event_history.append(event)
        logger.debug(f"Progress event: {event_type.value} - {action} - {details}")
        
        # Handle reasoning-specific display logic
        if event_type == ProgressEventType.LIVE_REASONING:
            self.is_in_reasoning_mode = True
            if reasoning_snippet:
                self.reasoning_manager.add_reasoning_snippet(reasoning_snippet, action)
            
            # Use the enhanced message with reasoning context
            display_message = self.reasoning_manager.get_current_display_message(details)
            
            # Only update if enough time has passed or force update
            if self.reasoning_manager.should_update_message(force_update):
                await self._update_slack_message(display_message)
        
        elif event_type in [ProgressEventType.FLUID_THINKING, ProgressEventType.REASONING]:
            self.is_in_reasoning_mode = True
            await self._update_slack_message(details)
        
        else:
            # Standard progress events
            self.is_in_reasoning_mode = False
            await self._update_slack_message(self._format_progress_message(event_type, action, details))
    
    def _format_progress_message(self, event_type: ProgressEventType, action: str, details: str) -> str:
        """Format progress message based on event type"""
        emoji_map = {
            ProgressEventType.ANALYZING: "🔍",
            ProgressEventType.REASONING: "💭",
            ProgressEventType.SEARCHING: "🔎",
            ProgressEventType.PROCESSING: "⚙️",
            ProgressEventType.GENERATING: "✨",
            ProgressEventType.SYNTHESIZING: "🧩",
            ProgressEventType.OBSERVING: "👀",
            ProgressEventType.REPLANNING: "🔄",
            ProgressEventType.ERROR: "❌",
            ProgressEventType.WARNING: "⚠️",
            ProgressEventType.RETRY: "🔄",
            ProgressEventType.THINKING: "💭",
            ProgressEventType.CONSIDERING: "🤔"
        }
        
        emoji = emoji_map.get(event_type, "⚡")
        
        if details:
            return f"{emoji} {details}"
        else:
            return f"{emoji} {action.replace('_', ' ').title()}..."
    
    async def _update_slack_message(self, message: str):
        """Update Slack message via callback"""
        if self.update_callback and message != self.current_message:
            try:
                self.current_message = message
                if asyncio.iscoroutinefunction(self.update_callback):
                    await self.update_callback(message)
                else:
                    self.update_callback(message)
            except Exception as e:
                logger.warning(f"Failed to update Slack message: {e}")
    
    def get_reasoning_summary(self) -> Dict[str, Any]:
        """Get summary of reasoning process for debugging/analysis"""
        return {
            "total_events": len(self.event_history),
            "reasoning_events": len([e for e in self.event_history if "reasoning" in e["event_type"]]),
            "reasoning_snippets": len(self.reasoning_manager.reasoning_snippets),
            "current_stage": self.reasoning_manager.current_stage,
            "in_reasoning_mode": self.is_in_reasoning_mode
        }

# Enhanced streaming reasoning emitter
class StreamingReasoningEmitter:
    """Specialized emitter for streaming reasoning display"""
    
    def __init__(self, progress_tracker: ProgressTracker):
        self.progress_tracker = progress_tracker
        self.accumulated_text = ""
        self.stage_keywords = {
            "understand": "💭 Understanding your request...",
            "approach": "🎯 Considering the best approach...",
            "tools": "🔧 Selecting optimal tools...",
            "strategy": "⚡ Planning execution strategy...",
            "synthesis": "🧩 Preparing to synthesize findings..."
        }
        self.current_stage_index = 0
        
    async def emit_reasoning_chunk(self, chunk_text: str, metadata: Dict[str, Any] = None):
        """Emit a chunk of reasoning with intelligent stage detection"""
        self.accumulated_text += chunk_text
        
        # Detect stage transitions based on content
        stage_detected = False
        for keyword, stage_message in self.stage_keywords.items():
            if keyword in chunk_text.lower() and not stage_detected:
                await self.progress_tracker.emit_progress(
                    ProgressEventType.LIVE_REASONING,
                    "reasoning_stage",
                    stage_message,
                    reasoning_snippet=chunk_text,
                    force_update=True
                )
                stage_detected = True
                break
        
        # If no stage keyword, emit as live reasoning
        if not stage_detected:
            await self.progress_tracker.emit_progress(
                ProgressEventType.LIVE_REASONING,
                "live_thinking",
                "💭 Thinking through your request...",
                reasoning_snippet=chunk_text
            )

# Convenience functions for enhanced progress tracking
async def emit_fluid_reasoning(tracker: ProgressTracker, action: str, details: str, reasoning_snippet: str = None):
    """Emit fluid reasoning progress with snippet"""
    await tracker.emit_progress(ProgressEventType.FLUID_THINKING, action, details, reasoning_snippet)

async def emit_live_reasoning(tracker: ProgressTracker, action: str, details: str, reasoning_snippet: str = None):
    """Emit live reasoning progress with real-time snippet"""
    await tracker.emit_progress(ProgressEventType.LIVE_REASONING, action, details, reasoning_snippet)

async def emit_reasoning(tracker: ProgressTracker, action: str, details: str):
    """Emit general reasoning progress"""
    await tracker.emit_progress(ProgressEventType.REASONING, action, details)

async def emit_searching(tracker: ProgressTracker, action: str, details: str):
    """Emit search progress"""
    await tracker.emit_progress(ProgressEventType.SEARCHING, action, details)

async def emit_processing(tracker: ProgressTracker, action: str, details: str):
    """Emit processing progress"""
    await tracker.emit_progress(ProgressEventType.PROCESSING, action, details)

async def emit_generating(tracker: ProgressTracker, action: str, details: str):
    """Emit generation progress"""
    await tracker.emit_progress(ProgressEventType.GENERATING, action, details)

async def emit_synthesizing(tracker: ProgressTracker, action: str, details: str):
    """Emit synthesis progress"""
    await tracker.emit_progress(ProgressEventType.SYNTHESIZING, action, details)

async def emit_observing(tracker: ProgressTracker, action: str, details: str):
    """Emit observation progress"""
    await tracker.emit_progress(ProgressEventType.OBSERVING, action, details)

async def emit_error(tracker: ProgressTracker, action: str, details: str):
    """Emit error progress"""
    await tracker.emit_progress(ProgressEventType.ERROR, action, details)

async def emit_warning(tracker: ProgressTracker, action: str, details: str):
    """Emit warning progress"""
    await tracker.emit_progress(ProgressEventType.WARNING, action, details)

async def emit_retry(tracker: ProgressTracker, action: str, details: str):
    """Emit retry progress"""
    await tracker.emit_progress(ProgressEventType.RETRY, action, details)

async def emit_thinking(tracker: ProgressTracker, action: str, details: str):
    """Emit thinking progress"""
    await tracker.emit_progress(ProgressEventType.THINKING, action, details)

async def emit_considering(tracker: ProgressTracker, action: str, details: str):
    """Emit considering progress"""
    await tracker.emit_progress(ProgressEventType.CONSIDERING, action, details)

async def emit_analyzing(tracker: ProgressTracker, action: str, details: str):
    """Emit analysis progress"""
    await tracker.emit_progress(ProgressEventType.ANALYZING, action, details)