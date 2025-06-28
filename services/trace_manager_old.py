"""
LangSmith Trace Manager Service

Provides comprehensive tracing and observability for the multi-agent system
using LangSmith without requiring the full LangChain stack.
"""

import asyncio
import logging
import traceback
import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from contextlib import asynccontextmanager

from langsmith import Client
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
        # Track active conversation sessions and their traces
        self.conversation_sessions = {}  # session_id -> trace_id
        self.session_traces = {}  # trace_id -> trace object
        self.current_session_id = None
        self.current_trace_id = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize LangSmith client if API key is available"""
        try:
            if self.settings.LANGSMITH_API_KEY:
                self.client = Client(
                    api_key=self.settings.LANGSMITH_API_KEY,
                    api_url=self.settings.LANGSMITH_ENDPOINT
                )
                logger.info("LangSmith client initialized successfully")
                logger.info("LangSmith client ready - will test connectivity on first trace")
                    
            else:
                logger.info("No LangSmith API key provided, tracing disabled")
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith client: {e}")
            self.client = None
    
    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled and working"""
        return self.client is not None
    
    def _get_conversation_session_id(self, channel_id: str, thread_ts: Optional[str] = None, user_id: str = None) -> str:
        """
        Generate a consistent conversation session ID for grouping related messages.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp if this is a thread conversation
            user_id: User ID for DM conversations
            
        Returns:
            Conversation session identifier
        """
        # For threaded conversations, use the thread timestamp
        if thread_ts:
            return f"thread_{channel_id}_{thread_ts}"
        # For DM conversations, use user_id
        elif channel_id.startswith('D') and user_id:
            return f"dm_{user_id}"
        # For channel conversations, create session based on recent activity window
        else:
            # Use a time window to group channel messages (30 minutes)
            import time
            time_window = int(time.time() // 1800)  # 30-minute windows
            return f"channel_{channel_id}_{time_window}"

    async def start_conversation_trace(
        self,
        user_id: str,
        message: str,
        channel_id: str,
        message_ts: str,
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """
        Start or continue a conversation trace for a Slack message.
        Groups related messages under the same conversation session.
        
        Args:
            user_id: Slack user ID who sent the message
            message: The user's message content
            channel_id: Slack channel ID
            message_ts: Message timestamp
            thread_ts: Thread timestamp if this is a thread reply
            
        Returns:
            Trace ID if successful, None if tracing disabled
        """
        if not self.is_enabled():
            return None
            
        try:
            # Get conversation session ID for grouping
            session_id = self._get_conversation_session_id(channel_id, thread_ts, user_id)
            
            # Check if we already have an active trace for this conversation
            if session_id in self.conversation_sessions:
                # Continue existing conversation trace
                existing_trace_id = self.conversation_sessions[session_id]
                self.current_trace = type('TraceObj', (), {'id': existing_trace_id})()
                logger.info(f"Continuing conversation trace: {existing_trace_id} for session: {session_id}")
                
                # Create a new message turn within the existing conversation
                await self.log_agent_step(
                    agent_name="user",
                    action="new_message",
                    inputs={
                        "message": message,
                        "user_id": user_id,
                        "timestamp": message_ts
                    },
                    metadata={
                        "message_type": "user_input",
                        "channel_id": channel_id,
                        "thread_ts": thread_ts
                    }
                )
                
                return existing_trace_id
            
            # Create new conversation trace
            metadata = {
                "user_id": user_id,
                "channel_id": channel_id,
                "message_ts": message_ts,
                "thread_ts": thread_ts,
                "session_id": session_id,
                "agent_system": "autopilot-expert-multi-agent",
                "timestamp": datetime.now().isoformat()
            }
            
            # Create a conversation-level trace name
            conversation_name = f"conversation_{session_id.replace('.', '_')}"
            
            trace_data = {
                "name": conversation_name,
                "run_type": "chain",
                "inputs": {
                    "initial_message": message,
                    "user_id": user_id,
                    "channel_context": channel_id,
                    "session_type": "thread" if thread_ts else ("dm" if channel_id.startswith('D') else "channel")
                },
                "tags": ["slack", "multi-agent", "conversation-session"],
                "extra": metadata,
                "start_time": datetime.now()
            }
            
            logger.debug(f"Creating new conversation trace: {conversation_name}")
            
            if not self.client:
                logger.error("LangSmith client is None")
                return None
                
            # Create the conversation trace with minimal required parameters
            try:
                self.current_trace = self.client.create_run(
                    name=trace_data["name"],
                    run_type=trace_data["run_type"],
                    inputs=trace_data["inputs"],
                    project_name=self.settings.LANGSMITH_PROJECT
                )
                
                if self.current_trace and hasattr(self.current_trace, 'id'):
                    trace_id = str(self.current_trace.id)
                    # Store the session for future messages
                    self.conversation_sessions[session_id] = trace_id
                    logger.info(f"Started new conversation trace: {trace_id} for session: {session_id}")
                    
                    # Log the initial user message as the first step
                    await self.log_agent_step(
                        agent_name="user",
                        action="conversation_start",
                        inputs={
                            "message": message,
                            "user_id": user_id,
                            "timestamp": message_ts
                        },
                        metadata={
                            "message_type": "conversation_start",
                            "channel_id": channel_id,
                            "thread_ts": thread_ts
                        }
                    )
                    
                    return trace_id
                else:
                    logger.error(f"create_run returned invalid object: {type(self.current_trace)}")
                    return None
                    
            except Exception as api_error:
                logger.error(f"LangSmith API error: {api_error}")
                import traceback
                logger.error(f"Full error traceback: {traceback.format_exc()}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to start conversation trace: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    async def log_agent_step(
        self,
        agent_name: str,
        action: str,
        inputs: Dict[str, Any],
        outputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error: Optional[Exception] = None
    ) -> Optional[str]:
        """
        Log an individual agent step within the current trace.
        
        Args:
            agent_name: Name of the agent (orchestrator, client, observer, etc.)
            action: Specific action being performed
            inputs: Input data for this step
            outputs: Output data from this step
            metadata: Additional metadata
            start_time: When the step started
            end_time: When the step completed
            error: Any error that occurred
            
        Returns:
            Run ID if successful, None if tracing disabled
        """
        if not self.is_enabled() or not self.current_trace:
            return None
            
        try:
            # Prepare run data
            run_data = {
                "name": f"{agent_name}_{action}",
                "project_name": self.settings.LANGSMITH_PROJECT,
                "parent_run_id": self.current_trace.id,
                "inputs": inputs,
                "run_type": "chain",  # LangSmith run type
                "tags": [agent_name, action, "agent-step"],
                "metadata": {
                    "agent": agent_name,
                    "action": action,
                    "step_timestamp": datetime.now().isoformat(),
                    **(metadata or {})
                }
            }
            
            # Add timing if provided
            if start_time:
                run_data["start_time"] = start_time
            if end_time:
                run_data["end_time"] = end_time
                
            # Create the run
            run = self.client.create_run(**run_data)
            
            # Update with outputs or error
            if outputs is not None:
                self.client.update_run(
                    run_id=run.id,
                    outputs=outputs,
                    end_time=end_time or datetime.now()
                )
            elif error is not None:
                self.client.update_run(
                    run_id=run.id,
                    error=str(error),
                    end_time=end_time or datetime.now()
                )
                
            logger.debug(f"Logged agent step: {agent_name}.{action} - {run.id}")
            return str(run.id)
            
        except Exception as e:
            logger.error(f"Failed to log agent step {agent_name}.{action}: {e}")
            return None
    
    async def log_api_call(
        self,
        api_name: str,
        model_name: str,
        prompt: str,
        response: str,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> Optional[str]:
        """
        Log an API call (like Gemini) within the current trace.
        
        Args:
            api_name: Name of the API (e.g., "gemini", "pinecone")
            model_name: Model used (e.g., "gemini-2.5-pro")
            prompt: Input prompt
            response: API response
            tokens_used: Number of tokens consumed
            duration_ms: Request duration in milliseconds
            error: Any error that occurred
            
        Returns:
            Run ID if successful, None if tracing disabled
        """
        if not self.is_enabled() or not self.current_trace:
            return None
            
        try:
            # Prepare API call data
            inputs = {
                "prompt": prompt,
                "model": model_name,
                "api": api_name
            }
            
            outputs = {
                "response": response,
                "tokens_used": tokens_used,
                "duration_ms": duration_ms
            } if not error else {}
            
            metadata = {
                "api_provider": api_name,
                "model": model_name,
                "tokens": tokens_used,
                "duration_ms": duration_ms
            }
            
            run_data = {
                "name": f"{api_name}_api_call",
                "project_name": self.settings.LANGSMITH_PROJECT,
                "parent_run_id": self.current_trace.id,
                "inputs": inputs,
                "outputs": outputs,
                "run_type": "llm",  # LangSmith LLM run type
                "tags": [api_name, model_name, "api-call"],
                "metadata": metadata
            }
            
            if error:
                run_data["error"] = str(error)
                
            run = self.client.create_run(**run_data)
            logger.debug(f"Logged API call: {api_name}.{model_name} - {run.id}")
            return str(run.id)
            
        except Exception as e:
            logger.error(f"Failed to log API call {api_name}: {e}")
            return None
    
    async def log_vector_search(
        self,
        query: str,
        results: List[Dict[str, Any]],
        search_duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log a vector search operation within the current trace.
        
        Args:
            query: Search query text
            results: Search results from Pinecone
            search_duration_ms: Search duration in milliseconds
            metadata: Additional search metadata
            
        Returns:
            Run ID if successful, None if tracing disabled
        """
        if not self.is_enabled() or not self.current_trace:
            return None
            
        try:
            inputs = {
                "query": query,
                "search_type": "vector_similarity"
            }
            
            outputs = {
                "results_count": len(results),
                "results": results[:3],  # Log first 3 results to avoid data overload
                "duration_ms": search_duration_ms
            }
            
            run_metadata = {
                "search_engine": "pinecone",
                "results_count": len(results),
                "duration_ms": search_duration_ms,
                **(metadata or {})
            }
            
            run_data = {
                "name": "vector_search",
                "project_name": self.settings.LANGSMITH_PROJECT,
                "parent_run_id": self.current_trace.id,
                "inputs": inputs,
                "outputs": outputs,
                "run_type": "retriever",  # LangSmith retriever run type
                "tags": ["vector-search", "pinecone", "knowledge-retrieval"],
                "metadata": run_metadata
            }
            
            run = self.client.create_run(**run_data)
            logger.debug(f"Logged vector search: {len(results)} results - {run.id}")
            return str(run.id)
            
        except Exception as e:
            logger.error(f"Failed to log vector search: {e}")
            return None
    
    async def complete_conversation_trace(
        self,
        final_response: str,
        total_duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[Exception] = None
    ) -> None:
        """
        Complete the current conversation message turn (not the entire conversation).
        Conversations remain active for future message turns.
        
        Args:
            final_response: The final response sent to the user for this turn
            total_duration_ms: Total processing time for this message turn
            success: Whether this message turn was successful
            error: Any error that occurred during this turn
        """
        if not self.is_enabled() or not self.current_trace:
            return
            
        try:
            # Log the agent's final response as a step in the conversation
            await self.log_agent_step(
                agent_name="assistant",
                action="response_complete",
                inputs={"processing_time_ms": total_duration_ms},
                outputs={
                    "final_response": final_response,
                    "success": success,
                    "turn_duration_ms": total_duration_ms
                },
                metadata={
                    "turn_type": "assistant_response",
                    "success": success,
                    "error": str(error) if error else None
                }
            )
            
            logger.info(f"Completed conversation turn in trace: {self.current_trace.id}")
            
            # Don't end the conversation trace - keep it active for future turns
            # Only reset current_run, not current_trace or session
            self.current_run = None
            
        except Exception as e:
            logger.error(f"Failed to complete conversation turn: {e}")

    def cleanup_expired_sessions(self, max_age_hours: int = 2) -> None:
        """
        Clean up conversation sessions older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours before session cleanup
        """
        try:
            import time
            current_time = time.time()
            expired_sessions = []
            
            # For now, implement simple time-based cleanup
            # In production, you might want more sophisticated session tracking
            for session_id in list(self.conversation_sessions.keys()):
                # Extract time component from session_id for time-based sessions
                if "channel_" in session_id:
                    try:
                        # Extract time window from channel session IDs
                        time_window = int(session_id.split('_')[-1])
                        session_time = time_window * 1800  # Convert back to timestamp
                        if current_time - session_time > (max_age_hours * 3600):
                            expired_sessions.append(session_id)
                    except (ValueError, IndexError):
                        # If we can't parse the time, keep the session
                        continue
                        
            # Remove expired sessions
            for session_id in expired_sessions:
                del self.conversation_sessions[session_id]
                logger.debug(f"Cleaned up expired conversation session: {session_id}")
                
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired conversation sessions")
                
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
    
    @asynccontextmanager
    async def trace_agent_operation(
        self,
        agent_name: str,
        operation: str,
        inputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing agent operations with automatic timing and error handling.
        
        Usage:
            async with trace_manager.trace_agent_operation("orchestrator", "analyze_query", inputs):
                result = await some_operation()
                yield result
        """
        if not self.is_enabled():
            yield None
            return
            
        start_time = datetime.now()
        run_id = None
        error = None
        outputs = {}
        
        try:
            # Start the operation trace
            run_id = await self.log_agent_step(
                agent_name=agent_name,
                action=operation,
                inputs=inputs,
                metadata=metadata,
                start_time=start_time
            )
            
            yield run_id
            
        except Exception as e:
            error = e
            logger.error(f"Error in traced operation {agent_name}.{operation}: {e}")
            raise
        finally:
            # Complete the operation trace
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            if run_id:
                try:
                    self.client.update_run(
                        run_id=run_id,
                        outputs=outputs,
                        end_time=end_time,
                        error=str(error) if error else None
                    )
                except Exception as update_error:
                    logger.error(f"Failed to update traced operation: {update_error}")


# Global trace manager instance
trace_manager = TraceManager()