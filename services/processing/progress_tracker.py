"""
Progress Tracker - Enhanced for conversational reasoning display with rich tool results.
Manages real-time progress updates with sophisticated message editing and content previews.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List
from enum import Enum
from datetime import datetime

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
    # New conversational event types
    NARRATING = "narrating"
    TOOL_RESULTS = "tool_results"
    DISCOVERY = "discovery"
    INSIGHT = "insight"
    TRANSITION = "transition"

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

class ToolResultPreview:
    """Manages tool result previews for rich display"""
    
    def __init__(self):
        self.results_by_tool = {}
        self.summary_cache = {}
    
    def add_tool_result(self, tool_name: str, result_data: Dict[str, Any]):
        """Add a tool result for preview generation"""
        if tool_name not in self.results_by_tool:
            self.results_by_tool[tool_name] = []
        
        self.results_by_tool[tool_name].append(result_data)
        # Clear cache when new results added
        if tool_name in self.summary_cache:
            del self.summary_cache[tool_name]
    
    def get_result_preview(self, tool_name: str, max_items: int = 3) -> str:
        """Generate a preview of tool results"""
        if tool_name not in self.results_by_tool:
            return ""
        
        if tool_name in self.summary_cache:
            return self.summary_cache[tool_name]
        
        results = self.results_by_tool[tool_name]
        preview = self._format_tool_results(tool_name, results, max_items)
        self.summary_cache[tool_name] = preview
        return preview
    
    def _format_tool_results(self, tool_name: str, results: List[Dict], max_items: int) -> str:
        """Format tool results into readable preview"""
        if not results:
            return ""
        
        total_count = len(results)
        preview_items = results[:max_items]
        
        if tool_name == "vector_search":
            lines = []
            for item in preview_items:
                content = item.get("content", "")
                user = item.get("user_name", "Team member")
                snippet = self._smart_truncate(content, 80)
                lines.append(f"   • {user}: \"{snippet}\"")
            
            if total_count > max_items:
                lines.append(f"   • ...and {total_count - max_items} more discussions")
            
            return "\n".join(lines)
        
        elif tool_name == "perplexity_search":
            lines = []
            for item in preview_items:
                title = item.get("title", "")
                source = item.get("source", "")
                if title:
                    snippet = self._smart_truncate(title, 60)
                    lines.append(f"   • {snippet}")
                    if source:
                        lines.append(f"     ({source})")
            
            if total_count > max_items:
                lines.append(f"   • ...and {total_count - max_items} more sources")
            
            return "\n".join(lines)
        
        elif tool_name == "atlassian_search":
            lines = []
            for item in preview_items:
                title = item.get("title", "")
                type_name = item.get("type", "item")
                if title:
                    snippet = self._smart_truncate(title, 70)
                    lines.append(f"   • {type_name.title()}: {snippet}")
            
            if total_count > max_items:
                lines.append(f"   • ...and {total_count - max_items} more items")
            
            return "\n".join(lines)
        
        else:
            # Generic formatting
            lines = []
            for item in preview_items:
                if isinstance(item, dict):
                    content = str(item.get("content", item.get("title", str(item))))
                else:
                    content = str(item)
                snippet = self._smart_truncate(content, 80)
                lines.append(f"   • {snippet}")
            
            if total_count > max_items:
                lines.append(f"   • ...and {total_count - max_items} more results")
            
            return "\n".join(lines)
    
    def _smart_truncate(self, text: str, max_length: int = 400) -> str:
        """Intelligently truncate while preserving meaning"""
        if len(text) <= max_length:
            return text
        
        # Find last complete sentence within limit
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclamation = truncated.rfind('!')
        
        cutoff = max(last_period, last_question, last_exclamation)
        if cutoff > max_length * 0.7:  # If we have 70%+ content
            return text[:cutoff + 1]
        else:
            # Find last word boundary
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.8:
                return text[:last_space] + "..."
            else:
                return text[:max_length] + "..."

class ConversationalProgressManager:
    """Manages conversational progress narrative with cumulative message building"""
    
    def __init__(self):
        self.current_phase = "starting"
        self.narrative_context = {}
        self.last_update_time = 0
        self.min_update_interval = 0.5  # Reduced for more responsive updates
        self.tool_previews = ToolResultPreview()
        self.message_sections = []  # Track cumulative sections
    
    def should_update_message(self, force: bool = False) -> bool:
        """Determine if message should be updated based on timing and content"""
        current_time = time.time()
        if force or (current_time - self.last_update_time) >= self.min_update_interval:
            self.last_update_time = current_time
            return True
        return False
    
    def add_progress_section(self, section: str):
        """Add a new section to the cumulative progress message"""
        # Format section in italics for Slack
        italic_section = f"*{section}*"
        self.message_sections.append(italic_section)
    
    def get_cumulative_message(self) -> str:
        """Get the full cumulative progress message"""
        if not self.message_sections:
            return ""
        
        # Join all sections with double line breaks for readability
        return "\n\n".join(self.message_sections)
    
    def create_conversational_message(self, narration: str, context: str = "", 
                                    findings: List[str] = None, next_step: str = "") -> str:
        """Create rich conversational progress message and add to cumulative sections"""
        message_parts = []
        
        # Main narration
        message_parts.append(f"{narration}")
        
        # Context or current action
        if context:
            message_parts.append(f"   {context}")
        
        # Findings preview
        if findings:
            message_parts.append("")  # Empty line for spacing
            for finding in findings:
                message_parts.append(finding)
        
        # Next step hint
        if next_step:
            message_parts.append("")
            message_parts.append(f"🎯 Next: {next_step}")
        
        # Create the section and add it
        section_content = "\n".join(message_parts)
        self.add_progress_section(section_content)
        
        return self.get_cumulative_message()
    
    def add_tool_results(self, tool_name: str, results: List[Dict[str, Any]]):
        """Add tool results for preview generation"""
        for result in results:
            self.tool_previews.add_tool_result(tool_name, result)

class ProgressTracker:
    """
    Enhanced Progress Tracker with conversational reasoning and rich tool result display.
    Manages real-time progress updates with sophisticated message editing for transparency.
    """
    
    def __init__(self, update_callback: Optional[Callable] = None):
        self.update_callback = update_callback
        self.current_message = ""
        self.last_update_time = 0
        self.event_history: List[Dict[str, Any]] = []
        self.reasoning_manager = ReasoningStageManager()  # Keep for compatibility
        self.conversational_manager = ConversationalProgressManager()
        self.is_in_reasoning_mode = False
        self.use_conversational_mode = True  # New feature flag
        
    async def emit_progress(self, event_type: ProgressEventType, action: str, details: str = "", 
                          reasoning_snippet: str = None, force_update: bool = False):
        """Enhanced progress emission with conversational support and italic formatting"""
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
        
        # Route to appropriate display logic
        if self.use_conversational_mode:
            await self._handle_conversational_progress(event_type, action, details, reasoning_snippet, force_update)
        else:
            # Legacy mode for backward compatibility
            await self._handle_legacy_progress(event_type, action, details, reasoning_snippet, force_update)
    
    async def _handle_conversational_progress(self, event_type: ProgressEventType, action: str, 
                                           details: str, reasoning_snippet: str, force_update: bool):
        """Handle progress display in conversational mode with italic formatting"""
        
        # Only update if enough time has passed or force update
        if not self.conversational_manager.should_update_message(force_update):
            return
        
        if event_type == ProgressEventType.NARRATING:
            # Pure narrative message - add as new section
            self.conversational_manager.add_progress_section(f"💭 {details}")
            cumulative_message = self.conversational_manager.get_cumulative_message()
            await self._update_slack_message(cumulative_message)
        
        elif event_type == ProgressEventType.DISCOVERY:
            # Discovery with excitement - add as new section
            self.conversational_manager.add_progress_section(f"✨ {details}")
            cumulative_message = self.conversational_manager.get_cumulative_message()
            await self._update_slack_message(cumulative_message)
        
        elif event_type == ProgressEventType.INSIGHT:
            # Insight with analysis - add as new section
            self.conversational_manager.add_progress_section(f"🎯 {details}")
            cumulative_message = self.conversational_manager.get_cumulative_message()
            await self._update_slack_message(cumulative_message)
        
        elif event_type == ProgressEventType.TRANSITION:
            # Transition to next phase - add as new section
            self.conversational_manager.add_progress_section(f"🔄 {details}")
            cumulative_message = self.conversational_manager.get_cumulative_message()
            await self._update_slack_message(cumulative_message)
        
        else:
            # Standard events with conversational framing - add as new section
            formatted_message = self._format_conversational_message(event_type, action, details)
            self.conversational_manager.add_progress_section(formatted_message)
            cumulative_message = self.conversational_manager.get_cumulative_message()
            await self._update_slack_message(cumulative_message)
    
    async def _handle_legacy_progress(self, event_type: ProgressEventType, action: str, 
                                    details: str, reasoning_snippet: str, force_update: bool):
        """Handle progress display in legacy mode with italic formatting"""
        # Handle reasoning-specific display logic
        if event_type == ProgressEventType.LIVE_REASONING:
            self.is_in_reasoning_mode = True
            if reasoning_snippet:
                self.reasoning_manager.add_reasoning_snippet(reasoning_snippet, action)
            
            # Use the enhanced message with reasoning context and italic formatting
            display_message = self.reasoning_manager.get_current_display_message(details)
            italic_message = f"*{display_message}*"
            
            # Only update if enough time has passed or force update
            if self.reasoning_manager.should_update_message(force_update):
                await self._update_slack_message(italic_message)
        
        elif event_type in [ProgressEventType.FLUID_THINKING, ProgressEventType.REASONING]:
            self.is_in_reasoning_mode = True
            italic_message = f"*{details}*"
            await self._update_slack_message(italic_message)
        
        else:
            # Standard progress events with italic formatting
            self.is_in_reasoning_mode = False
            formatted_message = self._format_progress_message(event_type, action, details)
            italic_message = f"*{formatted_message}*"
            await self._update_slack_message(italic_message)
    
    def _format_conversational_message(self, event_type: ProgressEventType, action: str, details: str) -> str:
        """Format progress message in conversational style (without italics - handled by caller)"""
        
        if event_type == ProgressEventType.SEARCHING:
            if "vector_search" in action:
                return f"💭 Let me check what the team has been discussing...\n   Searching through recent conversations..."
            elif "perplexity_search" in action:
                return f"🌐 Now let me get the latest news and updates...\n   Checking recent announcements and industry information..."
            elif "atlassian_search" in action:
                return f"📋 Let me look into the project details...\n   Searching through tickets and documentation..."
            else:
                return f"🔍 Searching for {details}..."
        
        elif event_type == ProgressEventType.PROCESSING:
            if "analyzing_results" in action:
                return f"⚙️ Interesting! Let me analyze what I found...\n   Processing the information to find key insights..."
            else:
                return f"⚙️ {details}"
        
        elif event_type == ProgressEventType.GENERATING:
            return f"✨ Putting together a comprehensive answer for you...\n   Combining insights from multiple sources..."
        
        elif event_type == ProgressEventType.ANALYZING:
            return f"🤔 I need to understand {details}...\n   This looks like a question about..."
        
        else:
            # Use enhanced emoji mapping
            emoji_map = {
                ProgressEventType.REASONING: "💭",
                ProgressEventType.SEARCHING: "🔍",
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
            return f"{emoji} {details}"
    
    def _format_progress_message(self, event_type: ProgressEventType, action: str, details: str) -> str:
        """Format progress message based on event type (legacy, without italics - handled by caller)"""
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
    
    async def emit_conversational_progress(self, narration: str, context: str = "", 
                                         tool_results: Dict[str, List[Dict]] = None, 
                                         next_step: str = ""):
        """Emit rich conversational progress with tool result previews and cumulative building"""
        findings = []
        
        # Generate tool result previews
        if tool_results:
            for tool_name, results in tool_results.items():
                if results:
                    self.conversational_manager.add_tool_results(tool_name, results)
                    preview = self.conversational_manager.tool_previews.get_result_preview(tool_name)
                    if preview:
                        tool_display_name = {
                            "vector_search": "Found team discussions:",
                            "perplexity_search": "Found recent sources:",
                            "atlassian_search": "Found project items:"
                        }.get(tool_name, f"Found {tool_name} results:")
                        
                        findings.append(f"   {tool_display_name}")
                        findings.append(preview)
        
        # Create rich message and add to cumulative sections
        message = self.conversational_manager.create_conversational_message(
            narration, context, findings, next_step
        )
        
        await self._update_slack_message(message)
    
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
            "in_reasoning_mode": self.is_in_reasoning_mode,
            "conversational_mode": self.use_conversational_mode,
            "tool_results_count": len(self.conversational_manager.tool_previews.results_by_tool)
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

# Legacy functions for backward compatibility
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

# New conversational functions
async def emit_narration(tracker: ProgressTracker, narration: str):
    """Emit pure narrative message"""
    await tracker.emit_progress(ProgressEventType.NARRATING, "narrating", narration)

async def emit_discovery(tracker: ProgressTracker, discovery: str):
    """Emit discovery with excitement"""
    await tracker.emit_progress(ProgressEventType.DISCOVERY, "discovering", discovery)

async def emit_insight(tracker: ProgressTracker, insight: str):
    """Emit insight with analysis"""
    await tracker.emit_progress(ProgressEventType.INSIGHT, "analyzing", insight)

async def emit_transition(tracker: ProgressTracker, transition: str):
    """Emit transition to next phase"""
    await tracker.emit_progress(ProgressEventType.TRANSITION, "transitioning", transition)

# Rich conversational functions
async def emit_search_with_results(tracker: ProgressTracker, search_type: str, query: str, results: List[Dict]):
    """Emit search progress with result preview"""
    tool_results = {search_type: results}
    
    if search_type == "vector_search":
        narration = "Let me check what the team has been discussing..."
        context = f"Searching for '{query}' in recent conversations"
        next_step = "analyzing what I found"
    elif search_type == "perplexity_search":
        narration = "Now let me get the latest news and updates..."
        context = f"Searching for recent information about '{query}'"
        next_step = "combining with team discussions"
    elif search_type == "atlassian_search":
        narration = "Let me look into the project details..."
        context = f"Searching for tickets and docs about '{query}'"
        next_step = "reviewing the findings"
    else:
        narration = f"Searching {search_type}..."
        context = f"Looking for information about '{query}'"
        next_step = "analyzing results"
    
    await tracker.emit_conversational_progress(narration, context, tool_results, next_step)

async def emit_analysis_insight(tracker: ProgressTracker, insight: str, findings: List[str] = None):
    """Emit analysis insight with supporting findings"""
    narration = "Interesting! Let me analyze what I found..."
    context = insight
    
    findings_formatted = []
    if findings:
        for finding in findings:
            findings_formatted.append(f"   ✓ {finding}")
    
    await tracker.emit_conversational_progress(narration, context, findings=findings_formatted)

async def emit_synthesis_progress(tracker: ProgressTracker, progress: str):
    """Emit synthesis progress with narrative"""
    narration = "Putting together a comprehensive answer for you..."
    context = progress
    next_step = "finalizing response"
    
    await tracker.emit_conversational_progress(narration, context, next_step=next_step)