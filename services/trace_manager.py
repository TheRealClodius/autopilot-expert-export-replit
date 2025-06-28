"""
LangSmith Trace Manager Service - Correct Non-LangChain Integration

Provides comprehensive tracing using proper LangSmith API patterns.
Based on official LangSmith documentation for non-LangChain integrations.
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
    Manages LangSmith tracing using proper non-LangChain integration patterns.
    
    Key principles from LangSmith docs:
    - Always provide run ID using uuid4()
    - Include both start_time and end_time for completed runs
    - Use proper run_type: "llm" for LLM calls, "chain" for workflows, "retriever" for searches
    - Create parent-child relationships using parent_run_id
    """
    
    def __init__(self):
        self.settings = Settings()
        self.client = None
        self.enabled = False
        
        # Track active conversation sessions
        self.active_sessions = {}
        self.current_session_id = None
        self.current_trace_id = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LangSmith client with proper connectivity testing"""
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
            
            # Test connectivity by checking project access
            try:
                project = self.client.read_project(project_name=self.settings.LANGSMITH_PROJECT)
                logger.info(f"LangSmith project access confirmed: {project.name}")
                self.enabled = True
                logger.info("LangSmith client fully operational")
                        
            except Exception as e:
                logger.warning(f"LangSmith project access failed: {e}")
                logger.warning("Tracing will operate in fallback mode")
                self.enabled = False
                self.client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith client: {e}")
            self.client = None
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled and working"""
        return self.enabled and self.client is not None
    
    async def start_conversation_session(self, user_id: str, message: str, 
                                       channel_id: str, message_ts: str) -> Optional[str]:
        """Start a new conversation session with proper LangSmith trace"""
        if not self.is_enabled():
            return None
            
        try:
            # Generate session ID and conversation trace ID
            session_id = f"conversation_{channel_id}_{int(time.time())}"
            conversation_trace_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # Create conversation trace in LangSmith
            self.client.create_run(
                id=conversation_trace_id,
                name=f"slack_conversation_{channel_id}",
                inputs={
                    "user_id": user_id,
                    "initial_message": message,
                    "channel_id": channel_id,
                    "message_ts": message_ts
                },
                run_type="chain",
                project_name=self.settings.LANGSMITH_PROJECT,
                start_time=current_time,
                tags=["conversation", "slack", "multi-agent"],
                extra={
                    "session_id": session_id,
                    "agent_system": "autopilot-expert-multi-agent"
                }
            )
            
            # Store session data
            self.active_sessions[session_id] = {
                'trace_id': conversation_trace_id,
                'start_time': current_time,
                'last_activity': current_time
            }
            
            self.current_session_id = session_id
            self.current_trace_id = conversation_trace_id
            
            logger.info(f"Started conversation session: {session_id} with trace: {conversation_trace_id}")
            
            # Log initial user message
            await self.log_user_message(user_id, message, message_ts)
            
            return session_id
                
        except Exception as e:
            logger.error(f"Failed to start conversation session: {e}")
            return None
    
    async def log_user_message(self, user_id: str, message: str, timestamp: str) -> Optional[str]:
        """Log a user message within the current conversation"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            message_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # Create user message run
            self.client.create_run(
                id=message_id,
                name="user_message",
                inputs={
                    "user_id": user_id,
                    "message": message,
                    "timestamp": timestamp
                },
                outputs={
                    "message_processed": True
                },
                run_type="chain",
                project_name=self.settings.LANGSMITH_PROJECT,
                start_time=current_time,
                end_time=current_time,
                parent_run_id=self.current_trace_id,
                tags=["user-input", "message"]
            )
            
            logger.debug(f"Logged user message with ID: {message_id}")
            return message_id
                
        except Exception as e:
            logger.error(f"Failed to log user message: {e}")
            return None
    
    async def log_llm_call(self, model: str, prompt: str, response: str, 
                          duration: float, tokens_used: int = None) -> Optional[str]:
        """Log an LLM API call with proper LangSmith format"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            llm_call_id = str(uuid.uuid4())
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=duration)
            
            # Create LLM run in LangSmith
            self.client.create_run(
                id=llm_call_id,
                name=f"llm_call_{model}",
                inputs={
                    "prompt": prompt,
                    "model": model
                },
                outputs={
                    "response": response,
                    "tokens_used": tokens_used
                },
                run_type="llm",  # Specific type for LLM calls
                project_name=self.settings.LANGSMITH_PROJECT,
                start_time=start_time,
                end_time=end_time,
                parent_run_id=self.current_trace_id,
                tags=["llm", "api-call", model.replace(".", "_")],
                extra={
                    "duration_seconds": duration,
                    "model": model,
                    "tokens": tokens_used
                }
            )
            
            logger.debug(f"Logged LLM call with ID: {llm_call_id}")
            return llm_call_id
                
        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}")
            return None
    
    async def log_orchestrator_analysis(self, query: str, execution_plan: str, 
                                      duration: float) -> Optional[str]:
        """Log orchestrator query analysis"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            analysis_id = str(uuid.uuid4())
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=duration)
            
            self.client.create_run(
                id=analysis_id,
                name="orchestrator_analysis",
                inputs={
                    "query": query,
                    "agent": "orchestrator"
                },
                outputs={
                    "execution_plan": execution_plan,
                    "duration_seconds": duration
                },
                run_type="chain",
                project_name=self.settings.LANGSMITH_PROJECT,
                start_time=start_time,
                end_time=end_time,
                parent_run_id=self.current_trace_id,
                tags=["orchestrator", "analysis", "planning"]
            )
            
            logger.debug(f"Logged orchestrator analysis: {analysis_id}")
            return analysis_id
                
        except Exception as e:
            logger.error(f"Failed to log orchestrator analysis: {e}")
            return None
    
    async def log_vector_search(self, query: str, results: List[Dict[str, Any]], 
                               duration_ms: float = None) -> Optional[str]:
        """Log vector search operation"""
        if not self.is_enabled() or not self.current_trace_id:
            return None
            
        try:
            search_id = str(uuid.uuid4())
            end_time = datetime.now()
            start_time = end_time - timedelta(milliseconds=duration_ms or 0)
            
            self.client.create_run(
                id=search_id,
                name="vector_search",
                inputs={
                    "query": query,
                    "search_type": "similarity"
                },
                outputs={
                    "results_count": len(results),
                    "results": results[:3],  # First 3 results to avoid huge payloads
                    "duration_ms": duration_ms
                },
                run_type="retriever",
                project_name=self.settings.LANGSMITH_PROJECT,
                start_time=start_time,
                end_time=end_time,
                parent_run_id=self.current_trace_id,
                tags=["vector-search", "retrieval", "pinecone"]
            )
            
            logger.debug(f"Logged vector search: {search_id}")
            return search_id
                
        except Exception as e:
            logger.error(f"Failed to log vector search: {e}")
            return None
    
    async def complete_conversation_session(self, session_id: str = None, 
                                          final_response: str = None) -> bool:
        """Complete the current conversation session"""
        if not self.is_enabled():
            return False
            
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.active_sessions:
            return False
            
        try:
            session_data = self.active_sessions[session_id]
            trace_id = session_data['trace_id']
            
            # Complete the conversation trace
            self.client.create_run(
                id=trace_id,
                name=f"slack_conversation_{session_id}",
                inputs={"session_id": session_id},
                outputs={
                    "final_response": final_response,
                    "session_completed": True,
                    "duration_seconds": (datetime.now() - session_data['start_time']).total_seconds()
                },
                run_type="chain",
                project_name=self.settings.LANGSMITH_PROJECT,
                start_time=session_data['start_time'],
                end_time=datetime.now(),
                tags=["conversation", "completed"]
            )
            
            # Clean up session
            del self.active_sessions[session_id]
            if self.current_session_id == session_id:
                self.current_session_id = None
                self.current_trace_id = None
            
            logger.info(f"Completed conversation session: {session_id}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to complete conversation session: {e}")
            return False


# Global instance
trace_manager = TraceManager()