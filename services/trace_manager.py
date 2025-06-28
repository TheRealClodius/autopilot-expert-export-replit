"""
LangSmith Trace Manager Service - Fixed Version

Provides comprehensive tracing and observability for the multi-agent system
using LangSmith without requiring the full LangChain stack.

Fixed Issues:
- Proper conversation grouping (all messages in same conversation under one trace)
- Orchestrator traces now properly captured
- Robust error handling with fallback logging
"""

import asyncio
import logging
import traceback
import time
import uuid
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None

from config import Settings

logger = logging.getLogger(__name__)

class TraceManager:
    """
    Manages LangSmith tracing for multi-agent conversations and operations.
    Provides comprehensive observability without LangChain dependencies.
    """
    
    def __init__(self):
        self.settings = Settings()
        self.client = None
        self.enabled = False
        
        # Conversation session management for proper grouping
        self.active_sessions = {}  # session_id -> {trace_id, start_time, last_activity}
        self.current_session_id = None
        self.current_trace_id = None
        
        # Session cleanup (remove sessions older than 2 hours)
        self.session_timeout = timedelta(hours=2)
        
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize LangSmith client if available and configured"""
        try:
            if not LANGSMITH_AVAILABLE:
                logger.info("LangSmith not available - install langsmith package for tracing")
                return
                
            if not self.settings.LANGSMITH_API_KEY:
                logger.info("No LangSmith API key configured - tracing disabled")
                return
                
            self.client = Client(
                api_key=self.settings.LANGSMITH_API_KEY,
                api_url=self.settings.LANGSMITH_ENDPOINT
            )
            
            # Enable LangSmith client 
            self.enabled = True
            logger.info("LangSmith client initialized successfully")
            
            # Test basic connectivity (non-blocking)
            try:
                # Simple test to verify client works
                test_run = self.client.create_run(
                    name="connectivity_test",
                    run_type="chain",
                    inputs={"test": "connection"},
                    project_name=self.settings.LANGSMITH_PROJECT
                )
                
                if test_run:
                    logger.info("LangSmith connectivity test passed")
                    # Clean up test run
                    try:
                        self.client.update_run(
                            run_id=test_run.id,
                            outputs={"status": "connection_verified"},
                            end_time=datetime.now()
                        )
                    except:
                        pass  # Don't fail if cleanup fails
                else:
                    logger.warning("LangSmith connectivity test returned None but client is enabled")
                    
            except Exception as e:
                logger.warning(f"LangSmith connectivity test failed but client is enabled: {e}")
                # Keep enabled - connectivity issues shouldn't disable tracing
                
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith client: {e}")
            self.client = None
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled and working"""
        return self.enabled and self.client is not None
    
    def _get_session_id(self, channel_id: str, thread_ts: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Generate a consistent session ID for conversation grouping.
        
        Args:
            channel_id: Slack channel ID  
            thread_ts: Thread timestamp for threaded conversations
            user_id: User ID for DM conversations
            
        Returns:
            Consistent session identifier for grouping related messages
        """
        if thread_ts:
            # Threaded conversations: group by thread
            return f"thread_{channel_id}_{thread_ts}"
        elif channel_id.startswith('D') and user_id:
            # Direct messages: group by user
            return f"dm_{user_id}"
        else:
            # Channel conversations: group by time windows (30 minutes)
            time_window = int(time.time() // 1800)  # 30-minute windows
            return f"channel_{channel_id}_{time_window}"
    
    def _cleanup_old_sessions(self):
        """Remove old inactive sessions to prevent memory leaks"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            if current_time - session_data['last_activity'] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            if session_id == self.current_session_id:
                self.current_session_id = None
                self.current_trace_id = None
                
        if expired_sessions:
            logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def start_conversation_session(
        self,
        user_id: str,
        message: str,
        channel_id: str,
        message_ts: str,
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """
        Start or continue a conversation session for proper message grouping.
        
        Returns:
            Session ID if successful, None if tracing disabled
        """
        if not self.is_enabled():
            return None
        
        try:
            # Clean up old sessions
            self._cleanup_old_sessions()
            
            # Get session ID
            session_id = self._get_session_id(channel_id, thread_ts, user_id)
            current_time = datetime.now()
            
            # Check if session already exists
            if session_id in self.active_sessions:
                # Update existing session
                session_data = self.active_sessions[session_id]
                session_data['last_activity'] = current_time
                
                self.current_session_id = session_id
                self.current_trace_id = session_data['trace_id']
                
                logger.info(f"Continuing conversation session: {session_id}")
                return session_id
            
            # Create new conversation trace
            conversation_name = f"conversation_{session_id.replace('.', '_')}"
            
            inputs = {
                "user_id": user_id,
                "initial_message": message,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "session_type": "thread" if thread_ts else ("dm" if channel_id.startswith('D') else "channel")
            }
            
            metadata = {
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "session_id": session_id,
                "agent_system": "autopilot-expert-multi-agent"
            }
            
            # Create the trace
            trace = self.client.create_run(
                name=conversation_name,
                run_type="chain",
                inputs=inputs,
                project_name=self.settings.LANGSMITH_PROJECT,
                tags=["conversation", "multi-agent", "slack"],
                extra=metadata,
                start_time=current_time
            )
            
            if trace and hasattr(trace, 'id'):
                trace_id = str(trace.id)
                
                # Store session data
                self.active_sessions[session_id] = {
                    'trace_id': trace_id,
                    'trace_object': trace,
                    'start_time': current_time,
                    'last_activity': current_time
                }
                
                self.current_session_id = session_id
                self.current_trace_id = trace_id
                
                logger.info(f"Started new conversation session: {session_id} with trace: {trace_id}")
                
                # Log initial user message
                await self.log_user_message(user_id, message, message_ts)
                
                return session_id
            else:
                logger.error("Failed to create conversation trace - no ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start conversation session: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    async def log_user_message(self, user_id: str, message: str, timestamp: str) -> Optional[str]:
        """Log a user message within the current conversation"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            run = self.client.create_run(
                name="user_message",
                run_type="chain",
                parent_run_id=self.current_trace_id,
                inputs={
                    "user_id": user_id,
                    "message": message,
                    "timestamp": timestamp
                },
                project_name=self.settings.LANGSMITH_PROJECT,
                tags=["user-input", "message"],
                start_time=datetime.now()
            )
            
            if run:
                # Complete immediately
                self.client.update_run(
                    run_id=run.id,
                    outputs={"message_logged": True},
                    end_time=datetime.now()
                )
                return str(run.id)
                
        except Exception as e:
            logger.error(f"Failed to log user message: {e}")
            return None
    
    async def log_orchestrator_analysis(
        self,
        query: str,
        execution_plan: str,
        reasoning: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> Optional[str]:
        """Log orchestrator query analysis and planning"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            start_time = datetime.now()
            
            inputs = {
                "query": query,
                "analysis_type": "query_planning"
            }
            
            outputs = {
                "execution_plan": execution_plan,
                "reasoning": reasoning,
                "duration_ms": duration_ms
            }
            
            run = self.client.create_run(
                name="orchestrator_analysis",
                run_type="chain",
                parent_run_id=self.current_trace_id,
                inputs=inputs,
                outputs=outputs,
                project_name=self.settings.LANGSMITH_PROJECT,
                tags=["orchestrator", "analysis", "planning"],
                start_time=start_time,
                end_time=datetime.now()
            )
            
            if run:
                logger.debug(f"Logged orchestrator analysis: {run.id}")
                return str(run.id)
                
        except Exception as e:
            logger.error(f"Failed to log orchestrator analysis: {e}")
            return None
    
    async def log_vector_search(
        self,
        query: str,
        results: List[Dict[str, Any]],
        search_type: str = "similarity",
        duration_ms: Optional[float] = None
    ) -> Optional[str]:
        """Log vector search operation"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            start_time = datetime.now()
            
            inputs = {
                "query": query,
                "search_type": search_type
            }
            
            outputs = {
                "results_count": len(results),
                "results": results[:3],  # Log first 3 results to avoid huge payloads
                "duration_ms": duration_ms
            }
            
            run = self.client.create_run(
                name="vector_search",
                run_type="retriever",
                parent_run_id=self.current_trace_id,
                inputs=inputs,
                outputs=outputs,
                project_name=self.settings.LANGSMITH_PROJECT,
                tags=["vector-search", "retrieval", "pinecone"],
                start_time=start_time,
                end_time=datetime.now()
            )
            
            if run:
                logger.debug(f"Logged vector search: {run.id}")
                return str(run.id)
                
        except Exception as e:
            logger.error(f"Failed to log vector search: {e}")
            return None
    
    async def log_client_response(
        self,
        final_response: str,
        response_type: str = "slack_message",
        duration_ms: Optional[float] = None
    ) -> Optional[str]:
        """Log client agent final response"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            start_time = datetime.now()
            
            inputs = {
                "response_type": response_type
            }
            
            outputs = {
                "final_response": final_response,
                "duration_ms": duration_ms
            }
            
            run = self.client.create_run(
                name="client_response",
                run_type="chain",
                parent_run_id=self.current_trace_id,
                inputs=inputs,
                outputs=outputs,
                project_name=self.settings.LANGSMITH_PROJECT,
                tags=["client-agent", "response", "final"],
                start_time=start_time,
                end_time=datetime.now()
            )
            
            if run:
                logger.debug(f"Logged client response: {run.id}")
                return str(run.id)
                
        except Exception as e:
            logger.error(f"Failed to log client response: {e}")
            return None
    
    async def log_api_call(
        self,
        api_name: str,
        model_name: str,
        prompt: str,
        response: str,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> Optional[str]:
        """Log an API call (Gemini, etc.) within current conversation"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            start_time = datetime.now()
            
            inputs = {
                "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,  # Truncate long prompts
                "model": model_name,
                "api": api_name
            }
            
            if error:
                outputs = {"error": error}
            else:
                outputs = {
                    "response": response[:1000] + "..." if len(response) > 1000 else response,  # Truncate long responses
                    "tokens_used": tokens_used,
                    "duration_ms": duration_ms
                }
            
            run = self.client.create_run(
                name=f"{api_name}_api_call",
                run_type="llm",
                parent_run_id=self.current_trace_id,
                inputs=inputs,
                outputs=outputs,
                project_name=self.settings.LANGSMITH_PROJECT,
                tags=[api_name, model_name, "api-call"],
                start_time=start_time,
                end_time=datetime.now()
            )
            
            if run:
                logger.debug(f"Logged API call: {api_name} - {run.id}")
                return str(run.id)
                
        except Exception as e:
            logger.error(f"Failed to log API call {api_name}: {e}")
            return None
    
    async def complete_conversation_turn(self, success: bool = True, error: Optional[str] = None):
        """Mark the current conversation turn as complete"""
        if not self.is_enabled() or not self.current_trace_id:
            return
            
        try:
            if self.current_session_id in self.active_sessions:
                session_data = self.active_sessions[self.current_session_id]
                session_data['last_activity'] = datetime.now()
                
                # The conversation stays active for future messages
                # We don't end the trace here as it should continue for the full conversation
                
                logger.debug(f"Completed conversation turn for session: {self.current_session_id}")
                
        except Exception as e:
            logger.error(f"Failed to complete conversation turn: {e}")

# Global trace manager instance
trace_manager = TraceManager()