"""
Orchestrator Agent - Main coordination agent that analyzes queries and creates execution plans.
Uses Gemini 2.5 Pro for query analysis and tool orchestration.
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.gemini_client import GeminiClient
from tools.vector_search import VectorSearchTool
from tools.perplexity_search import PerplexitySearchTool
from tools.outlook_meeting import OutlookMeetingTool
from tools.atlassian_tool import AtlassianTool
from agents.client_agent import ClientAgent
from agents.observer_agent import ObserverAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker, ProgressEventType, emit_thinking, emit_searching, emit_processing, emit_generating, emit_error, emit_warning, emit_retry, emit_reasoning, emit_considering, emit_analyzing, StreamingReasoningEmitter
from services.trace_manager import trace_manager
from models.schemas import ProcessedMessage

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Main orchestrating agent that analyzes queries and coordinates tool usage.
    Creates multi-step execution plans and manages the overall response flow.
    """
    
    def __init__(self, memory_service: MemoryService, progress_tracker: Optional[ProgressTracker] = None):
        self.gemini_client = GeminiClient()
        self.vector_tool = VectorSearchTool()
        self.perplexity_tool = PerplexitySearchTool()
        self.outlook_tool = OutlookMeetingTool()
        self.atlassian_tool = AtlassianTool()
        self.client_agent = ClientAgent()
        self.observer_agent = ObserverAgent()
        self.memory_service = memory_service
        self.progress_tracker = progress_tracker
        
    async def process_query(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        Process incoming query and generate response through multi-agent coordination.
        
        Args:
            message: Processed message from Slack Gateway
            
        Returns:
            Response data for sending back to Slack
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Orchestrator processing query: {message.text[:100]}...")
            
            # Emit initial reasoning progress instead of generic "analyzing"
            if self.progress_tracker:
                query_preview = message.text[:50] + "..." if len(message.text) > 50 else message.text
                first_progress_time = time.time()
                logger.info(f"⏱️  FIRST PROGRESS TRACE: About to emit reasoning progress at {first_progress_time:.3f}")
                await emit_considering(self.progress_tracker, "requirements", f"how to best approach: {query_preview}")
                post_progress_time = time.time()
                progress_emit_duration = post_progress_time - first_progress_time
                logger.info(f"⏱️  FIRST PROGRESS TRACE: Reasoning progress emitted at {post_progress_time:.3f} (emit took: {progress_emit_duration:.3f}s)")
            
            # Store raw message in short-term memory (10 message sliding window)
            # Use consistent thread identifier: for new mentions use message_ts, for thread replies use thread_ts
            thread_identifier = message.thread_ts or message.message_ts
            conversation_key = f"conv:{message.channel_id}:{thread_identifier}"
            await self.memory_service.store_raw_message(
                conversation_key,
                message.dict(),
                max_messages=10
            )
            
            # Also store current conversation context for compatibility
            await self.memory_service.store_conversation_context(
                conversation_key, 
                message.dict(), 
                ttl=86400  # 24 hours
            )
            
            plan_start = time.time()
            # Emit reasoning progress instead of generic "planning"
            if self.progress_tracker:
                await emit_reasoning(self.progress_tracker, "evaluating", "different approaches to solve this effectively")
            
            # Analyze query and create execution plan with tracing
            execution_plan = await self._analyze_query_and_plan(message)
            logger.info(f"Query analysis took {time.time() - plan_start:.2f}s")
            
            # Log orchestrator analysis in LangSmith
            await trace_manager.log_orchestrator_analysis(
                query=message.text,
                execution_plan=str(execution_plan),
                duration=time.time() - plan_start
            )
            
            if not execution_plan:
                # Let the orchestrator plan freely without constraints
                logger.warning("Query analysis returned None, letting orchestrator handle freely")
                # Don't force a minimal plan - let the system handle it naturally
                execution_plan = {
                    "analysis": f"Free-form analysis of query: '{message.text}'",
                    "tools_needed": ["vector_search"],  # Let it use available tools
                    "vector_queries": [message.text],  # Use the original query
                    "context": {
                        "intent": "open_query",
                        "response_approach": "Use full AI capabilities and available knowledge"
                    }
                }
            
            exec_start = time.time()
            # Execute the plan (specific search progress will be emitted during actual execution)
            gathered_information = await self._execute_plan(execution_plan, message)
            logger.info(f"Plan execution took {time.time() - exec_start:.2f}s")
            
            response_start = time.time()
            # Emit processing progress
            if self.progress_tracker:
                await emit_processing(self.progress_tracker, "analyzing_results", "search results")
            
            # Build comprehensive state stack for Client Agent
            state_stack = await self._build_state_stack(message, gathered_information, execution_plan)
            
            # Emit final generation progress
            if self.progress_tracker:
                await emit_generating(self.progress_tracker, "response_generation", "comprehensive response based on findings")
            
            # Generate final response through Client Agent with complete state
            response = await self.client_agent.generate_response(state_stack)
            logger.info(f"Response generation took {time.time() - response_start:.2f}s")
            
            if response:
                # Handle both string and dict responses from Client Agent
                if isinstance(response, dict):
                    response_text = response.get("text", "")
                    suggestions = response.get("suggestions", [])
                else:
                    response_text = response
                    suggestions = []
                
                # Trigger Observer Agent for learning (fire and forget - don't wait)
                import asyncio
                asyncio.create_task(self._trigger_observation(message, response_text, gathered_information))
                
                total_time = time.time() - start_time
                logger.info(f"Total processing time: {total_time:.2f}s")
                
                # Note: Response will be logged when conversation completes
                
                # Determine thread_ts for response
                # If user mentioned bot in channel (not in existing thread), start new thread
                # If user replied in existing thread, continue same thread
                response_thread_ts = message.thread_ts or message.message_ts
                
                result = {
                    "channel_id": message.channel_id,
                    "thread_ts": response_thread_ts,
                    "text": response_text,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add suggestions if they exist
                if suggestions:
                    result["suggestions"] = suggestions
                    logger.info(f"Including {len(suggestions)} suggestions in response")
                
                return result
            
            logger.warning("No response generated")
            return None
            
        except Exception as e:
            logger.error(f"Error in orchestrator processing: {e}")
            # Complete conversation turn with error
            await trace_manager.complete_conversation_turn(success=False, error=str(e))
            # Emit error progress if tracker is available
            if self.progress_tracker:
                await emit_error(self.progress_tracker, "processing_error", "internal system issue")
            return None
    
    async def _analyze_query_and_plan(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        Analyze the query using Gemini and create an execution plan.
        
        Args:
            message: Processed message to analyze
            
        Returns:
            Execution plan dictionary
        """
        try:
            # Get recent messages for better context (10 message sliding window)
            conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
            recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=10)
            
            # Also get legacy conversation history for compatibility
            conversation_history = await self.memory_service.get_conversation_context(conversation_key)
            
            # Prepare context for analysis with short-term memory
            context = {
                "query": message.text,
                "user": message.user_name,
                "channel": message.channel_name,
                "is_dm": message.is_dm,
                "thread_context": message.thread_context,
                "recent_messages": recent_messages,  # Last 10 raw messages
                "conversation_history": conversation_history
            }
            
            # Load prompt from centralized prompt loader
            from utils.prompt_loader import get_orchestrator_prompt
            system_prompt = get_orchestrator_prompt()
            
            user_prompt = f"""
Context: {json.dumps(context, indent=2)}

Create an execution plan to answer this query effectively.

Current Query: "{message.text}"
"""
            
            # Track LLM call timing for LangSmith
            llm_start = time.time()
            
            # Add timeout protection for API call with streaming reasoning capture
            try:
                # Set up real-time reasoning emission to Slack
                reasoning_emitter = StreamingReasoningEmitter(self.progress_tracker) if self.progress_tracker else None
                
                async def reasoning_callback(chunk_text: str, chunk_metadata: dict):
                    """Handle real-time reasoning chunks from Gemini streaming"""
                    logger.info(f"🧠 REASONING CHUNK: {chunk_text[:100]}...")
                    if reasoning_emitter:
                        await reasoning_emitter.emit_reasoning_chunk(chunk_text, chunk_metadata)
                
                # Use streaming to capture reasoning steps as they're generated
                streaming_response = await asyncio.wait_for(
                    self.gemini_client.generate_streaming_response(
                        system_prompt,
                        user_prompt,
                        model=self.gemini_client.pro_model,  # Orchestrator uses Pro model for complex planning
                        max_tokens=2000,
                        temperature=0.7,
                        reasoning_callback=reasoning_callback  # Pass callback for real-time reasoning
                    ),
                    timeout=20.0  # 20 second timeout for streaming
                )
                
                response = streaming_response.get("text") if streaming_response else None
                reasoning_steps = streaming_response.get("reasoning_steps", []) if streaming_response else []
                
                # Log reasoning steps if found
                if reasoning_steps:
                    logger.info(f"Captured {len(reasoning_steps)} reasoning steps from Gemini 2.5 Pro")
                    for i, step in enumerate(reasoning_steps[:3]):  # Log first 3 steps
                        logger.debug(f"Reasoning step {i+1}: {step.get('text', '')[:100]}...")
                else:
                    logger.debug("No explicit reasoning steps detected in response")
                
            except asyncio.TimeoutError:
                logger.error("Gemini API call timed out after 15 seconds")
                if self.progress_tracker:
                    await emit_warning(self.progress_tracker, "api_timeout", "analysis taking longer than expected")
                response = None
                reasoning_steps = []
            
            # Log LLM call to LangSmith with reasoning steps
            llm_duration = time.time() - llm_start
            if response:
                await trace_manager.log_llm_call(
                    model=self.gemini_client.pro_model,
                    prompt=f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}",
                    response=f"REASONING: {reasoning_steps}\n\nRESPONSE: {response}" if reasoning_steps else response,
                    duration=llm_duration
                )
            
            if response:
                try:
                    # Clean response to extract JSON from markdown code blocks
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        # Extract JSON from markdown code block
                        start_index = cleaned_response.find('{')
                        end_index = cleaned_response.rfind('}') + 1
                        if start_index != -1 and end_index > start_index:
                            cleaned_response = cleaned_response[start_index:end_index]
                    elif cleaned_response.startswith('```'):
                        # Remove code block markers
                        lines = cleaned_response.split('\n')
                        cleaned_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_response
                    
                    plan = json.loads(cleaned_response)
                    logger.info(f"Generated execution plan: {plan.get('analysis', 'No analysis')}")
                    return plan
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse execution plan JSON: {e}")
                    logger.error(f"Raw Gemini response: {response[:500]}...")
                    return None
            else:
                logger.error("Gemini API returned empty/None response")
                return None
            
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return None
    

    
    async def _execute_plan(self, plan: Dict[str, Any], message: ProcessedMessage) -> Dict[str, Any]:
        """
        Execute the generated plan by calling appropriate tools.
        
        Args:
            plan: Execution plan from query analysis
            message: Original processed message
            
        Returns:
            Dictionary containing gathered information from vector search
        """
        gathered_info = {"vector_results": [], "perplexity_results": [], "meeting_results": []}
        
        try:
            tools_needed = plan.get("tools_needed", [])
            
            # Execute Perplexity search if needed
            if "perplexity_search" in tools_needed:
                perplexity_queries = plan.get("perplexity_queries", [])
                if perplexity_queries:
                    logger.info(f"Executing {len(perplexity_queries)} Perplexity searches")
                    for i, query in enumerate(perplexity_queries):
                        # Emit specific search progress with clear context
                        if self.progress_tracker:
                            search_topic = query[:40] + "..." if len(query) > 40 else query
                            await emit_searching(self.progress_tracker, "perplexity_search", search_topic)
                        
                        try:
                            result = await self.perplexity_tool.search(
                                query=query,
                                max_tokens=1000,
                                temperature=0.2
                            )
                            if result and result.get("content"):
                                gathered_info["perplexity_results"].append({
                                    "query": query,
                                    "content": result["content"],
                                    "citations": result.get("citations", []),
                                    "search_time": result.get("search_time", 0),
                                    "model_used": result.get("model_used", "unknown")
                                })
                                # Emit success for found results
                                if self.progress_tracker:
                                    citations_count = len(result.get("citations", []))
                                    await emit_processing(self.progress_tracker, "analyzing_results", f"web findings ({citations_count} sources)")
                            elif self.progress_tracker:
                                # Emit warning if no results found
                                await emit_warning(self.progress_tracker, "limited_results", f"no web results for '{query[:20]}...'")
                        except Exception as search_error:
                            logger.error(f"Perplexity search error for query '{query}': {search_error}")
                            if self.progress_tracker:
                                await emit_error(self.progress_tracker, "search_error", f"issue with web search query")
                            # Continue with other queries even if one fails
            
            # Execute vector search if needed
            if "vector_search" in tools_needed:
                vector_queries = plan.get("vector_queries", [])
                if vector_queries:
                    logger.info(f"Executing {len(vector_queries)} vector searches")
                    for i, query in enumerate(vector_queries):
                        # Emit specific search progress with clear context
                        if self.progress_tracker:
                            search_topic = query[:40] + "..." if len(query) > 40 else query
                            await emit_searching(self.progress_tracker, "vector_search", search_topic)
                        
                        try:
                            results = await self.vector_tool.search(
                                query=query,
                                top_k=5,
                                filters={}
                            )
                            if results:
                                gathered_info["vector_results"].extend(results)
                            elif self.progress_tracker:
                                # Emit warning if no results found
                                await emit_warning(self.progress_tracker, "limited_results", f"no matches for '{query[:20]}...'")
                        except Exception as search_error:
                            logger.error(f"Vector search error for query '{query}': {search_error}")
                            if self.progress_tracker:
                                await emit_error(self.progress_tracker, "search_error", f"issue with search query")
                            # Continue with other queries even if one fails
            
            # Execute Outlook meeting actions if needed
            if "outlook_meeting" in tools_needed:
                meeting_actions = plan.get("meeting_actions", [])
                if meeting_actions:
                    logger.info(f"Executing {len(meeting_actions)} Outlook meeting actions")
                    gathered_info["meeting_results"] = []
                    
                    for action in meeting_actions:
                        action_type = action.get("type")
                        
                        if self.progress_tracker:
                            await emit_processing(self.progress_tracker, "meeting_action", f"processing {action_type} request")
                        
                        try:
                            if action_type == "check_availability":
                                result = await self.outlook_tool.check_availability(
                                    email_addresses=action.get("emails", []),
                                    start_time=action.get("start_time"),
                                    end_time=action.get("end_time"),
                                    timezone=action.get("timezone", "UTC")
                                )
                            elif action_type == "schedule_meeting":
                                result = await self.outlook_tool.schedule_meeting(
                                    subject=action.get("subject", "Meeting"),
                                    attendee_emails=action.get("attendees", []),
                                    start_time=action.get("start_time"),
                                    end_time=action.get("end_time"),
                                    body=action.get("body", ""),
                                    location=action.get("location", ""),
                                    timezone=action.get("timezone", "UTC"),
                                    is_online_meeting=action.get("is_online", True)
                                )
                            elif action_type == "find_meeting_times":
                                result = await self.outlook_tool.find_meeting_times(
                                    attendee_emails=action.get("attendees", []),
                                    duration_minutes=action.get("duration", 60),
                                    max_candidates=action.get("max_suggestions", 10),
                                    start_date=action.get("start_date"),
                                    end_date=action.get("end_date"),
                                    timezone=action.get("timezone", "UTC")
                                )
                            elif action_type == "get_calendar":
                                result = await self.outlook_tool.get_calendar_events(
                                    start_date=action.get("start_date"),
                                    end_date=action.get("end_date"),
                                    timezone=action.get("timezone", "UTC"),
                                    max_events=action.get("max_events", 20)
                                )
                            else:
                                logger.warning(f"Unknown meeting action type: {action_type}")
                                continue
                            
                            if result and "error" not in result:
                                gathered_info["meeting_results"].append({
                                    "action_type": action_type,
                                    "result": result,
                                    "success": True
                                })
                                if self.progress_tracker:
                                    await emit_processing(self.progress_tracker, "analyzing_results", f"meeting {action_type} completed")
                            else:
                                gathered_info["meeting_results"].append({
                                    "action_type": action_type,
                                    "error": result.get("error", "Unknown error") if result else "No result",
                                    "success": False
                                })
                                if self.progress_tracker:
                                    await emit_warning(self.progress_tracker, "meeting_error", f"{action_type} encountered an issue")
                                    
                        except Exception as meeting_error:
                            logger.error(f"Meeting action error for {action_type}: {meeting_error}")
                            gathered_info["meeting_results"].append({
                                "action_type": action_type,
                                "error": str(meeting_error),
                                "success": False
                            })
                            if self.progress_tracker:
                                await emit_error(self.progress_tracker, "meeting_error", f"issue with {action_type}")
                            # Continue with other actions even if one fails
            
            # Execute Atlassian tool if needed
            if "atlassian_search" in tools_needed:
                atlassian_actions = plan.get("atlassian_actions", [])
                if atlassian_actions:
                    logger.info(f"Executing {len(atlassian_actions)} Atlassian actions")
                    gathered_info["atlassian_results"] = []
                    
                    for action in atlassian_actions:
                        action_type = action.get("type")
                        
                        if self.progress_tracker:
                            await emit_processing(self.progress_tracker, "atlassian_action", f"processing {action_type} request")
                        
                        try:
                            if action_type == "search_jira_issues":
                                result = await self.atlassian_tool.search_jira_issues(
                                    query=action.get("query", ""),
                                    max_results=action.get("max_results", 10),
                                    fields=action.get("fields")
                                )
                            elif action_type == "get_jira_issue":
                                result = await self.atlassian_tool.get_jira_issue(
                                    issue_key=action.get("issue_key", "")
                                )
                            elif action_type == "search_confluence_pages":
                                result = await self.atlassian_tool.search_confluence_pages(
                                    query=action.get("query", ""),
                                    space_key=action.get("space_key"),
                                    max_results=action.get("max_results", 10)
                                )
                            elif action_type == "get_confluence_page":
                                result = await self.atlassian_tool.get_confluence_page(
                                    page_id=action.get("page_id", "")
                                )
                            elif action_type == "create_jira_issue":
                                result = await self.atlassian_tool.create_jira_issue(
                                    project_key=action.get("project_key", ""),
                                    issue_type=action.get("issue_type", "Task"),
                                    summary=action.get("summary", ""),
                                    description=action.get("description", ""),
                                    priority=action.get("priority", "Medium"),
                                    assignee=action.get("assignee")
                                )
                            else:
                                result = {"error": f"Unknown Atlassian action type: {action_type}"}
                            
                            # Store result
                            if result and not result.get("error"):
                                gathered_info["atlassian_results"].append({
                                    "action_type": action_type,
                                    "result": result,
                                    "success": True
                                })
                                if self.progress_tracker:
                                    await emit_processing(self.progress_tracker, "analyzing_results", f"Atlassian {action_type} completed")
                            else:
                                gathered_info["atlassian_results"].append({
                                    "action_type": action_type,
                                    "error": result.get("error", "Unknown error") if result else "No result",
                                    "success": False
                                })
                                if self.progress_tracker:
                                    await emit_warning(self.progress_tracker, "atlassian_error", f"{action_type} encountered an issue")
                                    
                        except Exception as atlassian_error:
                            logger.error(f"Atlassian action error for {action_type}: {atlassian_error}")
                            gathered_info["atlassian_results"].append({
                                "action_type": action_type,
                                "error": str(atlassian_error),
                                "success": False
                            })
                            if self.progress_tracker:
                                await emit_error(self.progress_tracker, "atlassian_error", f"issue with {action_type}")
                            # Continue with other actions even if one fails
            
            logger.info(f"Gathered {len(gathered_info['vector_results'])} vector results, {len(gathered_info['perplexity_results'])} web results, and {len(gathered_info.get('atlassian_results', []))} Atlassian results")
            return gathered_info
            
        except Exception as e:
            logger.error(f"Error executing plan: {e}")
            return gathered_info
    
    async def _build_state_stack(self, message: ProcessedMessage, gathered_information: Dict[str, Any], execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive state stack for Client Agent containing all context needed.
        
        Args:
            message: Original processed message
            gathered_information: Results from vector search and other tools
            execution_plan: Orchestrator's execution plan with insights
            
        Returns:
            Complete state stack for client agent
        """
        try:
            # Get conversation history
            thread_identifier = message.thread_ts or message.message_ts
            conversation_key = f"conv:{message.channel_id}:{thread_identifier}"
            recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=10)
            
            # Get conversation context for potential long-term summary
            conversation_context = await self.memory_service.get_conversation_context(conversation_key)
            
            # Organize recent messages into user queries and agent responses
            user_queries = []
            agent_responses = []
            
            for msg in recent_messages:
                if msg.get("user_name") != "bot" and msg.get("user_name") != "autopilot":
                    user_queries.append({
                        "text": msg.get("text", ""),
                        "user": msg.get("user_name", "Unknown"),
                        "timestamp": msg.get("message_ts", "")
                    })
                else:
                    agent_responses.append({
                        "text": msg.get("text", ""),
                        "timestamp": msg.get("message_ts", "")
                    })
            
            # Build streamlined state stack without redundant information
            state_stack = {
                "query": message.text,  # Client agent expects "query" key
                "user": {
                    "name": message.user_name,
                    "first_name": message.user_first_name,
                    "display_name": message.user_display_name,
                    "title": message.user_title,
                    "department": message.user_department
                },
                "context": {
                    "channel": message.channel_name,
                    "is_dm": message.is_dm,
                    "thread_ts": message.thread_ts
                },
                "conversation_history": {
                    "recent_exchanges": self._deduplicate_messages([
                        {"role": "user" if msg.get("user_name") != "bot" and msg.get("user_name") != "autopilot" else "assistant", 
                         "text": msg.get("text", "")[:200],  # Truncate long messages
                         "timestamp": msg.get("message_ts", "")}
                        for msg in recent_messages[-6:]  # Only last 6 messages for context
                    ]) if recent_messages else [],
                    "long_conversation_summary": conversation_context if len(recent_messages) >= 8 else None
                },
                "orchestrator_analysis": {
                    "intent": execution_plan.get("analysis", ""),
                    "tools_used": execution_plan.get("tools_needed", []),
                    "search_results": gathered_information.get("vector_results", [])[:3] if gathered_information.get("vector_results") else [],  # Limit to top 3 results
                    "web_results": gathered_information.get("perplexity_results", [])[:2] if gathered_information.get("perplexity_results") else [],  # Limit to top 2 web results
                    "meeting_results": gathered_information.get("meeting_results", []),  # Include all meeting results
                    "atlassian_results": gathered_information.get("atlassian_results", [])  # Include all Atlassian results
                },
                "response_thread_ts": message.thread_ts or message.message_ts,
                "trace_id": self._get_current_trace_id()
            }
            
            logger.info(f"Built state stack with {len(user_queries)} user queries, {len(agent_responses)} agent responses, {len(gathered_information.get('vector_results', []))} vector results")
            return state_stack
            
        except Exception as e:
            logger.error(f"Error building state stack: {e}")
            # Return minimal state stack on error
            return {
                "query": message.text,
                "user": {"name": message.user_name, "first_name": message.user_first_name},
                "context": {"channel": message.channel_name, "is_dm": message.is_dm},
                "conversation_history": {"recent_exchanges": []},
                "orchestrator_analysis": {
                    "intent": execution_plan.get("analysis", "Error occurred during analysis"),
                    "tools_used": [],
                    "search_results": [],
                    "web_results": [],
                    "atlassian_results": []
                },
                "response_thread_ts": message.thread_ts or message.message_ts,
                "trace_id": self._get_current_trace_id()
            }

    def _get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID from global trace manager"""
        try:
            from services.trace_manager import trace_manager
            current_id = trace_manager.current_trace_id
            logger.info(f"DEBUG: Orchestrator _get_current_trace_id returning: {current_id}")
            return current_id
        except Exception as e:
            logger.error(f"ERROR: Failed to get trace ID: {e}")
            return None
    
    def _deduplicate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate messages based on text content and timestamp.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Deduplicated list of messages
        """
        seen = set()
        deduplicated = []
        
        for msg in messages:
            # Create a unique key from text and timestamp
            key = (msg.get("text", ""), msg.get("timestamp", ""))
            if key not in seen and msg.get("text", "").strip():  # Only include non-empty messages
                seen.add(key)
                deduplicated.append(msg)
        
        return deduplicated
    
    async def _trigger_observation(self, message: ProcessedMessage, response: str, gathered_info: Dict[str, Any]):
        """
        Trigger Observer Agent to learn from the conversation (async).
        
        Args:
            message: Original message
            response: Generated response
            gathered_info: Information used to generate response
        """
        try:
            # Don't wait for observation to complete
            observation_data = {
                "message": message.dict(),
                "response": response,
                "gathered_info": gathered_info,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store for Observer Agent to process later
            await self.memory_service.store_temp_data(
                f"observation:{message.message_ts}",
                observation_data,
                ttl=3600  # 1 hour
            )
            
            # Trigger Observer Agent (fire and forget)
            await self.observer_agent.observe_conversation(observation_data)
            
        except Exception as e:
            logger.error(f"Error triggering observation: {e}")
    

