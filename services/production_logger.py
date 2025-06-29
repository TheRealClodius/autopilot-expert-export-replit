"""
Production Logger Service

Comprehensive logging and execution transcript capture for production debugging.
Captures detailed execution traces that can be extracted via admin endpoints.
"""

import logging
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import traceback
from dataclasses import dataclass, asdict, field
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ExecutionStep:
    """Single execution step in a trace"""
    timestamp: str
    step_type: str  # orchestrator_start, mcp_call, api_call, error, etc.
    component: str  # orchestrator, atlassian_tool, slack_gateway, etc.
    action: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    error: Optional[str] = None

@dataclass
class SlackTrace:
    """Complete Slack message execution trace"""
    trace_id: str
    slack_message_id: str
    user_id: str
    channel_id: str
    query: str
    start_time: str
    end_time: Optional[str] = None
    total_duration_ms: Optional[float] = None
    steps: List[ExecutionStep] = field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    error_summary: Optional[str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []

class ProductionLogger:
    """
    Production-grade logging and execution tracing system.
    Captures detailed execution flows for production debugging.
    """
    
    def __init__(self):
        self.active_traces: Dict[str, SlackTrace] = {}
        self.completed_traces: List[SlackTrace] = []
        self.max_completed_traces = 50  # Keep last 50 traces
        
        # Setup production logging
        self._setup_production_logging()
        
        logger.info("Production logger initialized")
    
    def _setup_production_logging(self):
        """Setup enhanced production logging configuration"""
        # Don't reconfigure logging if already configured
        root_logger = logging.getLogger()
        if root_logger.handlers:
            return
            
        # Configure root logger for production
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
            ]
        )
    
    def start_slack_trace(self, message_data: Dict[str, Any]) -> str:
        """Start a new Slack message execution trace"""
        trace_id = str(uuid.uuid4())[:8]
        
        trace = SlackTrace(
            trace_id=trace_id,
            slack_message_id=message_data.get('ts', 'unknown'),
            user_id=message_data.get('user', 'unknown'),
            channel_id=message_data.get('channel', 'unknown'),
            query=message_data.get('text', 'unknown')[:200],  # Truncate long queries
            start_time=datetime.now(timezone.utc).isoformat()
        )
        
        self.active_traces[trace_id] = trace
        self._current_trace_id = trace_id
        
        self.log_step(trace_id, "slack_start", "slack_gateway", "message_received", {
            "message_type": message_data.get('type'),
            "channel": message_data.get('channel'),
            "user": message_data.get('user'),
            "query_preview": message_data.get('text', '')[:100]
        })
        
        logger.info(f"Started Slack trace for user query: {trace.query[:50]}...")
        return trace_id
    
    def log_step(self, trace_id: str, step_type: str, component: str, action: str, 
                 data: Dict[str, Any], duration_ms: Optional[float] = None, 
                 error: Optional[str] = None):
        """Log a single execution step"""
        if trace_id not in self.active_traces:
            logger.warning(f"Attempted to log step for unknown trace: {trace_id}")
            return
        
        step = ExecutionStep(
            timestamp=datetime.now(timezone.utc).isoformat(),
            step_type=step_type,
            component=component,
            action=action,
            data=data,
            duration_ms=duration_ms,
            error=error
        )
        
        self.active_traces[trace_id].steps.append(step)
        
        # Log to production logs
        log_msg = f"{component}.{action}"
        if duration_ms:
            log_msg += f" ({duration_ms:.1f}ms)"
        if error:
            log_msg += f" ERROR: {error[:100]}"
        
        # Set trace context for logging
        self._current_trace_id = trace_id
        
        if error:
            logger.error(log_msg, extra={'trace_id': trace_id})
        else:
            logger.info(log_msg, extra={'trace_id': trace_id})
    
    def log_orchestrator_reasoning(self, trace_id: str, reasoning_chunks: List[str]):
        """Log orchestrator reasoning process"""
        reasoning_summary = " ".join(reasoning_chunks)[:500]  # Truncate
        
        self.log_step(trace_id, "orchestrator_reasoning", "orchestrator", "ai_reasoning", {
            "reasoning_chunks": len(reasoning_chunks),
            "reasoning_preview": reasoning_summary,
            "full_reasoning": reasoning_chunks
        })
    
    def log_mcp_call(self, trace_id: str, mcp_tool: str, arguments: Dict[str, Any], 
                     result: Dict[str, Any], duration_ms: float):
        """Log MCP tool call with full details"""
        success = result.get("success", False)
        error = result.get("error") if not success else None
        
        self.log_step(trace_id, "mcp_call", "atlassian_tool", f"mcp_{mcp_tool}", {
            "mcp_tool": mcp_tool,
            "arguments": arguments,
            "success": success,
            "result_count": len(result.get("result", [])) if isinstance(result.get("result"), list) else 0,
            "result_preview": str(result)[:200]
        }, duration_ms, error)
    
    def log_api_call(self, trace_id: str, api_name: str, endpoint: str, 
                     status_code: int, duration_ms: float, error: Optional[str] = None):
        """Log external API call"""
        self.log_step(trace_id, "api_call", api_name, "http_request", {
            "endpoint": endpoint,
            "status_code": status_code,
            "success": 200 <= status_code < 300
        }, duration_ms, error)
    
    def complete_trace(self, trace_id: str, final_result: Optional[Dict[str, Any]] = None, 
                       error_summary: Optional[str] = None):
        """Complete a Slack trace"""
        if trace_id not in self.active_traces:
            logger.warning(f"Attempted to complete unknown trace: {trace_id}")
            return
        
        trace = self.active_traces[trace_id]
        trace.end_time = datetime.now(timezone.utc).isoformat()
        trace.final_result = final_result
        trace.error_summary = error_summary
        
        # Calculate total duration
        if trace.start_time:
            start_dt = datetime.fromisoformat(trace.start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(trace.end_time.replace('Z', '+00:00'))
            trace.total_duration_ms = (end_dt - start_dt).total_seconds() * 1000
        
        # Move to completed traces
        self.completed_traces.append(trace)
        del self.active_traces[trace_id]
        
        # Keep only recent traces
        if len(self.completed_traces) > self.max_completed_traces:
            self.completed_traces = self.completed_traces[-self.max_completed_traces:]
        
        logger.info(f"Completed trace {trace_id} in {trace.total_duration_ms:.1f}ms", 
                   extra={'trace_id': trace_id})
    
    def get_latest_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest execution traces"""
        traces = sorted(
            self.completed_traces, 
            key=lambda t: t.start_time, 
            reverse=True
        )[:limit]
        
        return [asdict(trace) for trace in traces]
    
    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get specific trace by ID"""
        # Check active traces
        if trace_id in self.active_traces:
            return asdict(self.active_traces[trace_id])
        
        # Check completed traces
        for trace in self.completed_traces:
            if trace.trace_id == trace_id:
                return asdict(trace)
        
        return None
    
    def get_execution_transcript(self, trace_id: str) -> str:
        """Generate human-readable execution transcript"""
        trace_data = self.get_trace_by_id(trace_id)
        if not trace_data:
            return f"Trace {trace_id} not found"
        
        transcript = []
        transcript.append(f"EXECUTION TRANSCRIPT - Trace ID: {trace_id}")
        transcript.append("=" * 60)
        transcript.append(f"Query: {trace_data['query']}")
        transcript.append(f"User: {trace_data['user_id']}")
        transcript.append(f"Channel: {trace_data['channel_id']}")
        transcript.append(f"Start: {trace_data['start_time']}")
        if trace_data['end_time']:
            transcript.append(f"Duration: {trace_data.get('total_duration_ms', 0):.1f}ms")
        transcript.append("")
        
        # Steps
        transcript.append("EXECUTION STEPS:")
        transcript.append("-" * 40)
        
        for i, step in enumerate(trace_data['steps'], 1):
            timestamp = step['timestamp'].split('T')[1][:12]  # Just time part
            duration = f"({step.get('duration_ms', 0):.1f}ms)" if step.get('duration_ms') else ""
            
            transcript.append(f"{i:2d}. [{timestamp}] {step['component']}.{step['action']} {duration}")
            
            if step.get('error'):
                transcript.append(f"    ERROR: {step['error']}")
            
            # Add key data points
            data = step.get('data', {})
            if 'mcp_tool' in data:
                transcript.append(f"    MCP: {data['mcp_tool']} -> Success: {data.get('success', False)}")
            if 'status_code' in data:
                transcript.append(f"    HTTP: {data['status_code']} -> {data.get('endpoint', '')}")
            if 'reasoning_chunks' in data:
                transcript.append(f"    AI: {data['reasoning_chunks']} reasoning steps")
        
        transcript.append("")
        
        # Final result
        if trace_data.get('error_summary'):
            transcript.append(f"FINAL ERROR: {trace_data['error_summary']}")
        elif trace_data.get('final_result'):
            result = trace_data['final_result']
            transcript.append(f"FINAL RESULT: {type(result).__name__} with {len(str(result))} chars")
        
        return "\n".join(transcript)
    
    def get_production_stats(self) -> Dict[str, Any]:
        """Get production execution statistics"""
        active_count = len(self.active_traces)
        completed_count = len(self.completed_traces)
        
        # Calculate success rates
        successful_traces = sum(1 for t in self.completed_traces if not t.error_summary)
        success_rate = (successful_traces / completed_count * 100) if completed_count > 0 else 0
        
        # Average duration
        durations = [t.total_duration_ms for t in self.completed_traces if t.total_duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "active_traces": active_count,
            "completed_traces": completed_count,
            "success_rate": f"{success_rate:.1f}%",
            "average_duration_ms": f"{avg_duration:.1f}",
            "recent_errors": [
                {"trace_id": t.trace_id, "error": t.error_summary, "query": t.query[:50]}
                for t in self.completed_traces[-10:] if t.error_summary
            ]
        }

# Global production logger instance
production_logger = ProductionLogger()