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
from utils.prompt_loader import get_orchestrator_prompt
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
    
    def __init__(self, memory_service: MemoryService, progress_tracker: Optional[ProgressTracker] = None, trace_manager=None):
        self.gemini_client = GeminiClient()
        self.vector_tool = VectorSearchTool()
        self.perplexity_tool = PerplexitySearchTool()
        self.outlook_tool = OutlookMeetingTool()
        self.trace_manager = trace_manager
        self.atlassian_tool = AtlassianTool(trace_manager=trace_manager)
        self.client_agent = ClientAgent()
        self.observer_agent = ObserverAgent()
        self.memory_service = memory_service
        self.progress_tracker = progress_tracker
        self.discovered_tools = []  # Will be populated with actual MCP tools
        
    async def discover_and_update_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from MCP server and update tool list"""
        try:
            tools = await self.atlassian_tool.discover_available_tools()
            self.discovered_tools = tools
            logger.info(f"Updated tool list with {len(tools)} total tools, {len(self.atlassian_tool.available_tools)} Atlassian tools")
            return tools
        except Exception as e:
            logger.warning(f"Failed to discover tools: {e}")
            return []
    
    async def _generate_dynamic_system_prompt(self) -> str:
        """Generate system prompt using YAML template with dynamic tool injection"""
        
        # Load base prompt from prompts.yaml
        base_prompt = get_orchestrator_prompt()
        
        # Generate dynamic Atlassian tools section
        atlassian_tools_section = ""
        
        if self.discovered_tools:
            atlassian_tools = [tool for tool in self.discovered_tools 
                             if any(keyword in tool.get('name', '').lower() 
                                  for keyword in ['jira', 'confluence', 'atlassian'])]
            
            if atlassian_tools:
                atlassian_tools_section = "\n  **Available Atlassian Tools from MCP server:**"
                for tool in atlassian_tools:
                    name = tool.get('name', 'unknown')
                    description = tool.get('description', 'No description available')
                    atlassian_tools_section += f"\n  - {name}: {description}"
                atlassian_tools_section += "\n  **For Atlassian MCP tools, use exact tool names returned by the server.**"
        
        # Inject the dynamic tools section into the placeholder
        full_prompt = base_prompt.replace("{{atlassian_tools_section}}", atlassian_tools_section)
        
        logger.info(f"Generated system prompt from YAML with {len(self.discovered_tools)} discovered tools")
        return full_prompt
        
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
            
            # Discover available tools from MCP server first
            await self.discover_and_update_tools()
            
            # Generate dynamic system prompt with actual available tools
            system_prompt = await self._generate_dynamic_system_prompt()
            
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
                            # Use generalized retry pattern for vector search
                            vector_action = {"type": "search", "query": query, "top_k": 5, "filters": {}}
                            result = await self._execute_tool_action("vector_search", vector_action, message)
                            
                            if result and not result.get("error"):
                                # Extract actual results from the wrapped response
                                actual_results = result.get("results", []) if isinstance(result, dict) else result
                                if actual_results:
                                    gathered_info["vector_results"].extend(actual_results if isinstance(actual_results, list) else [actual_results])
                            elif self.progress_tracker:
                                # Emit warning if no results found or HITL required
                                if result.get("hitl_required"):
                                    await emit_error(self.progress_tracker, "hitl_required", f"vector search requires human intervention")
                                else:
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
                        # Handle both modern MCP format and legacy format
                        action_type = action.get("mcp_tool") or action.get("type")
                        
                        if self.progress_tracker:
                            await emit_processing(self.progress_tracker, "atlassian_action", f"processing {action_type} request")
                        
                        try:
                            # Direct MCP execution with intelligent retry for connection issues
                            result = await asyncio.wait_for(
                                self._execute_mcp_action_with_retry(action),
                                timeout=60.0  # Direct MCP timeout
                            )
                            
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
                        
                        except asyncio.TimeoutError:
                            logger.warning(f"Atlassian {action_type} timed out after 90 seconds (deployment environment)")
                            gathered_info["atlassian_results"].append({
                                "action_type": action_type,
                                "error": "Request timed out in deployment environment. This may be due to slower network conditions.",
                                "success": False,
                                "timeout": True
                            })
                            if self.progress_tracker:
                                await emit_warning(self.progress_tracker, "atlassian_timeout", f"{action_type} timed out - continuing with other sources")
                                    
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
        Build simplified state stack for Client Agent with orchestrator-generated summaries.
        Shifts data processing responsibility to orchestrator, making client agent focus on presentation.
        
        Args:
            message: Original processed message
            gathered_information: Results from vector search and other tools
            execution_plan: Orchestrator's execution plan with insights
            
        Returns:
            Simplified state stack with pre-formatted summaries for client agent
        """
        try:
            # Get conversation history
            thread_identifier = message.thread_ts or message.message_ts
            conversation_key = f"conv:{message.channel_id}:{thread_identifier}"
            recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=10)
            
            # Generate orchestrator summaries for all search results (orchestrator does the heavy lifting)
            search_summary = await self._summarize_search_results(gathered_information.get("vector_results", []))
            web_summary = await self._summarize_web_results(gathered_information.get("perplexity_results", []))
            meeting_summary = await self._summarize_meeting_results(gathered_information.get("meeting_results", []))
            atlassian_summary = await self._summarize_atlassian_results(gathered_information.get("atlassian_results", []))
            
            # Create conversation summary from recent messages
            conversation_summary = await self._summarize_conversation_history(recent_messages)
            
            # Build simplified state stack for Client Agent (orchestrator does the heavy lifting)
            state_stack = {
                "query": message.text,
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
                    "thread_context": message.thread_context
                },
                "conversation_summary": conversation_summary,
                "orchestrator_findings": {
                    "analysis": execution_plan.get("analysis", ""),
                    "tools_used": execution_plan.get("tools_needed", []),
                    "search_summary": search_summary,
                    "web_summary": web_summary,
                    "meeting_summary": meeting_summary,
                    "atlassian_summary": atlassian_summary
                },
                "response_thread_ts": message.thread_ts or message.message_ts,
                "trace_id": self._get_current_trace_id()
            }
            
            logger.info(f"Built simplified state stack with orchestrator summaries")
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
    
    async def _execute_tool_action(self, tool_name: str, action: Dict[str, Any], message: ProcessedMessage) -> Dict[str, Any]:
        """
        Execute a tool action with simple error handling.
        Relies on tenacity-based network retries in individual tools.
        Logical errors are surfaced to the user for clear feedback.
        
        Args:
            tool_name: Name of the tool (atlassian, vector_search, perplexity, etc.)
            action: The action to execute  
            message: Original processed message for context
            
        Returns:
            Result from execution or clear error message for user
        """
        action_type = action.get("mcp_tool") or action.get("type", "unknown_action")
        
        try:
            if self.progress_tracker:
                await emit_reasoning(self.progress_tracker, "executing_action", f"executing {tool_name} {action_type}")
            
            # Execute the action using the appropriate tool
            result = await self._execute_single_tool_action(tool_name, action)
            
            # Check if action succeeded
            if result and not result.get("error"):
                return result
            else:
                # Tool execution failed - surface the error clearly to the user
                error_msg = result.get("error", "Unknown error") if result else "No result returned"
                
                # Provide user-friendly error message
                user_friendly_error = self._format_user_friendly_error(tool_name, action_type, error_msg)
                
                if self.progress_tracker:
                    await emit_warning(self.progress_tracker, "action_failed", f"{tool_name} search encountered an issue")
                
                return {"error": user_friendly_error, "user_facing": True}
                        
        except Exception as e:
            logger.error(f"{tool_name} action {action_type} failed: {str(e)}")
            user_friendly_error = self._format_user_friendly_error(tool_name, action_type, str(e))
            return {"error": user_friendly_error, "user_facing": True}
    
    async def _execute_mcp_action_direct(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Direct MCP execution bypassing complex retry logic.
        Uses the proven working pattern for all Atlassian MCP commands.
        """
        mcp_tool = action.get("mcp_tool")
        arguments = action.get("arguments", {})
        
        if not mcp_tool:
            return {"error": "No mcp_tool specified in action"}
        
        try:
            # Direct call to Atlassian tool using working pattern
            import time
            start_time = time.time()
            result = await self.atlassian_tool.execute_mcp_tool(mcp_tool, arguments)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log completed MCP operation to LangSmith
            if self.trace_manager:
                try:
                    await self.trace_manager.log_mcp_tool_operation(
                        mcp_tool,
                        arguments,
                        result if result else None,
                        duration_ms,
                        error=None if result and result.get("success") else result.get("error", "No result from MCP") if result else "No result from MCP"
                    )
                except Exception as e:
                    logger.warning(f"Failed to log completed MCP trace: {e}")
            
            # Log MCP call to production logger
            try:
                from services.production_logger import production_logger
                current_trace_id = getattr(self, '_current_trace_id', None)
                if current_trace_id:
                    production_logger.log_mcp_call(current_trace_id, mcp_tool, arguments, result, duration_ms)
            except Exception:
                pass  # Don't let logging errors break execution
            
            # Return result in expected format
            if result and result.get("success"):
                return {
                    "success": True,
                    "result": result.get("result", []),
                    "tool": mcp_tool,
                    "arguments": arguments
                }
            else:
                return {
                    "error": result.get("error", "MCP execution failed") if result else "No result from MCP",
                    "success": False
                }
                
        except Exception as e:
            logger.error(f"Direct MCP execution failed: {e}")
            
            # Log failed MCP operation to LangSmith
            if self.trace_manager:
                try:
                    await self.trace_manager.log_mcp_tool_operation(
                        mcp_tool,
                        arguments,
                        None,
                        0,
                        error=str(e)
                    )
                except Exception:
                    pass
                    
            return {"error": f"MCP execution error: {str(e)}", "success": False}
    
    async def _execute_mcp_action_with_retry(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP action with intelligent retry for connection/handshake issues.
        Handles deployment environment instability gracefully.
        """
        max_retries = 3
        base_delay = 1.0  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                result = await self._execute_mcp_action_direct(action)
                
                # Check if we got a connection-related error that should be retried
                if result and result.get("error"):
                    error_type = result.get("error")
                    
                    # Retry on connection timeouts and handshake failures
                    if (error_type in ["connection_timeout", "mcp_handshake_failed"] and 
                        result.get("retry_suggested") and 
                        attempt < max_retries - 1):
                        
                        # Calculate exponential backoff delay
                        delay = base_delay * (2 ** attempt)
                        
                        if self.progress_tracker:
                            await emit_retry(self.progress_tracker, "mcp_retry", 
                                           f"retrying MCP connection in {delay:.1f}s (attempt {attempt + 2}/{max_retries})")
                        
                        # Wait before retry
                        await asyncio.sleep(delay)
                        continue
                
                # Return result (success or non-retryable error)
                return result
                
            except Exception as e:
                logger.error(f"MCP retry attempt {attempt + 1} failed: {e}")
                
                # If this was the last attempt, return the error
                if attempt == max_retries - 1:
                    return {"error": f"MCP execution failed after {max_retries} attempts: {str(e)}", "success": False}
                
                # Otherwise, wait and retry
                delay = base_delay * (2 ** attempt)
                if self.progress_tracker:
                    await emit_retry(self.progress_tracker, "mcp_retry", 
                                   f"retrying after error in {delay:.1f}s (attempt {attempt + 2}/{max_retries})")
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        return {"error": "Maximum retries exceeded", "success": False}
    
    async def _execute_single_tool_action(self, tool_name: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool action without retry logic"""
        
        if tool_name == "atlassian":
            # Modern direct MCP tool execution (orchestrator generates this format)
            mcp_tool = action.get("mcp_tool")
            mcp_arguments = action.get("arguments", {})
            
            if mcp_tool and mcp_arguments:
                # Direct MCP call with correct format
                logger.info(f"Executing direct MCP call: {mcp_tool} with args: {mcp_arguments}")
                return await self.atlassian_tool.execute_mcp_tool(mcp_tool, mcp_arguments)
            else:
                # Legacy fallback for backward compatibility (use correct "limit" parameter)
                action_type = action.get("type")
                if action_type == "search_jira_issues":
                    return await self.atlassian_tool.execute_mcp_tool("jira_search", {
                        "jql": action.get("query", ""),
                        "limit": action.get("limit", action.get("max_results", 10))  # Fixed parameter name
                    })
                elif action_type == "get_jira_issue":
                    return await self.atlassian_tool.execute_mcp_tool("jira_get", {
                        "issue_key": action.get("issue_key", "")
                    })
                elif action_type == "search_confluence_pages":
                    return await self.atlassian_tool.execute_mcp_tool("confluence_search", {
                        "query": action.get("query", ""),
                        "space_key": action.get("space_key"),
                        "limit": action.get("limit", action.get("max_results", 10))  # Fixed parameter name
                    })
                elif action_type == "get_confluence_page":
                    return await self.atlassian_tool.execute_mcp_tool("confluence_get", {
                        "page_id": action.get("page_id", "")
                    })
                elif action_type == "create_jira_issue":
                    return await self.atlassian_tool.execute_mcp_tool("jira_create", {
                        "project_key": action.get("project_key", ""),
                        "issue_type": action.get("issue_type", "Task"),
                        "summary": action.get("summary", ""),
                        "description": action.get("description", ""),
                        "priority": action.get("priority", "Medium"),
                        "assignee": action.get("assignee")
                    })
                else:
                    return {"error": f"Unknown Atlassian action type: {action_type}"}
        
        elif tool_name == "vector_search":
            query = action.get("query", "")
            top_k = action.get("top_k", 5)
            
            # Execute vector search
            results = await self.vector_tool.search(
                query=query,
                top_k=top_k,
                filters=action.get("filters", {})
            )
            
            # Log vector search to LangSmith
            if self.trace_manager and results:
                try:
                    await self.trace_manager.log_vector_search(
                        query,
                        results,
                        search_type="semantic_similarity"
                    )
                except Exception as e:
                    logger.warning(f"Failed to log vector search trace: {e}")
            
            # Vector search returns a list, but we need to wrap it as a dict for consistency
            return {"results": results, "success": True} if results else {"results": [], "success": True}
        
        elif tool_name == "perplexity_search":
            return await self.perplexity_tool.search(
                query=action.get("query", ""),
                max_tokens=action.get("max_tokens", 1000),
                temperature=action.get("temperature", 0.2)
            )
        
        elif tool_name == "outlook_meeting":
            # Handle different Outlook meeting actions
            action_type = action.get("type", "unknown")
            if action_type == "check_availability":
                return await self.outlook_tool.check_availability(
                    email_addresses=action.get("emails", []),
                    start_time=action.get("start_time"),
                    end_time=action.get("end_time"),
                    timezone=action.get("timezone", "UTC")
                )
            elif action_type == "schedule_meeting":
                return await self.outlook_tool.schedule_meeting(
                    subject=action.get("subject", "Meeting"),
                    attendee_emails=action.get("attendees", []),
                    start_time=action.get("start_time"),
                    end_time=action.get("end_time"),
                    body=action.get("body", ""),
                    location=action.get("location", ""),
                    timezone=action.get("timezone", "UTC"),
                    is_online_meeting=action.get("is_online", True)
                )
            # Add other meeting actions...
            else:
                return {"error": f"Unknown Outlook meeting action: {action_type}"}
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _format_user_friendly_error(self, tool_name: str, action_type: str, error_msg: str) -> str:
        """
        Convert technical error messages into user-friendly format.
        
        Args:
            tool_name: Name of the tool that failed
            action_type: Type of action that failed
            error_msg: Technical error message
            
        Returns:
            User-friendly error message
        """
        # Convert common technical errors to user-friendly messages
        error_lower = error_msg.lower()
        
        if "syntax" in error_lower or "malformed" in error_lower:
            if tool_name == "atlassian":
                return "I couldn't process that search because the query format wasn't recognized. Could you try phrasing it differently?"
            elif tool_name == "vector_search":
                return "I had trouble understanding your search query. Could you try using different keywords?"
            else:
                return "I couldn't process your request because the query format wasn't recognized. Could you try rephrasing it?"
        
        elif "permission" in error_lower or "forbidden" in error_lower or "unauthorized" in error_lower:
            if tool_name == "atlassian":
                return "I don't have permission to access that information in Jira or Confluence. Please check with your administrator."
            else:
                return "I don't have permission to access that information. Please check with your administrator."
        
        elif "not found" in error_lower or "404" in error_msg:
            if tool_name == "atlassian":
                return "I couldn't find any matching results in Jira or Confluence. Try searching with different keywords."
            else:
                return "I couldn't find any matching results. Try searching with different keywords."
        
        elif "timeout" in error_lower or "connection" in error_lower:
            return "The search is taking longer than expected. Please try again in a moment."
        
        else:
            # Generic fallback that encourages user to try differently
            if tool_name == "atlassian":
                return "I encountered an issue searching Jira and Confluence. Could you try rephrasing your request?"
            elif tool_name == "vector_search":
                return "I had trouble searching our knowledge base. Could you try using different keywords?"
            else:
                return "I encountered an issue processing your request. Could you try rephrasing it?"
    
    async def _summarize_search_results(self, vector_results: List[Dict[str, Any]]) -> str:
        """
        Summarize vector search results into a clean, formatted summary for client agent.
        Orchestrator does the heavy lifting of data processing.
        """
        if not vector_results:
            return ""
        
        summary_parts = []
        summary_parts.append(f"Found {len(vector_results)} relevant documents:")
        
        for i, result in enumerate(vector_results[:3], 1):  # Top 3 results
            content = result.get("content", "")[:150]  # Truncate content
            source = result.get("source", "Unknown source")
            score = result.get("score", 0.0)
            summary_parts.append(f"{i}. {content}... (from {source}, relevance: {score:.2f})")
        
        return "\n".join(summary_parts)
    
    async def _summarize_web_results(self, perplexity_results: List[Dict[str, Any]]) -> str:
        """
        Summarize web search results into a clean, formatted summary for client agent.
        """
        if not perplexity_results:
            return ""
        
        summary_parts = []
        summary_parts.append(f"Found {len(perplexity_results)} web sources:")
        
        for i, result in enumerate(perplexity_results[:2], 1):  # Top 2 results
            content = result.get("content", "")[:150]  # Truncate content
            sources = result.get("sources", [])
            source_text = f" (sources: {len(sources)} citations)" if sources else ""
            summary_parts.append(f"{i}. {content}...{source_text}")
        
        return "\n".join(summary_parts)
    
    async def _summarize_meeting_results(self, meeting_results: List[Dict[str, Any]]) -> str:
        """
        Summarize meeting actions into a clean, formatted summary for client agent.
        """
        if not meeting_results:
            return ""
        
        summary_parts = []
        for result in meeting_results:
            action_type = result.get("action_type", "unknown")
            success = result.get("success", False)
            
            if success:
                if action_type == "schedule_meeting":
                    summary_parts.append("✓ Meeting scheduled successfully")
                elif action_type == "find_meeting_times":
                    suggestions = result.get("meeting_data", {}).get("meeting_time_suggestions", {}).get("suggestions", [])
                    summary_parts.append(f"✓ Found {len(suggestions)} available meeting times")
                elif action_type == "get_calendar":
                    events = result.get("meeting_data", {}).get("calendar_events", {}).get("events", [])
                    summary_parts.append(f"✓ Retrieved {len(events)} calendar events")
            else:
                summary_parts.append(f"✗ {action_type.replace('_', ' ').title()} failed")
        
        return "\n".join(summary_parts)
    
    async def _summarize_atlassian_results(self, atlassian_results: List[Dict[str, Any]]) -> str:
        """
        Summarize Atlassian actions into a clean, formatted summary with clickable links.
        """
        if not atlassian_results:
            return ""
        
        summary_parts = []
        for result in atlassian_results:
            action_type = result.get("action_type") or result.get("mcp_tool", "unknown")
            success = result.get("success", False)
            
            if success:
                result_data = result.get("result", [])
                
                if action_type in ["jira_search", "search_jira_issues"]:
                    if isinstance(result_data, list):
                        summary_parts.append(f"✓ Found {len(result_data)} Jira issues:")
                        for issue in result_data[:3]:  # Top 3 issues
                            key = issue.get("key", "")
                            summary = issue.get("summary", "")[:60]
                            if key:
                                url = f"https://uipath.atlassian.net/browse/{key}"
                                summary_parts.append(f"  • <{url}|{key}>: {summary}...")
                
                elif action_type in ["confluence_search", "search_confluence_pages"]:
                    if isinstance(result_data, list):
                        summary_parts.append(f"✓ Found {len(result_data)} Confluence pages:")
                        for page in result_data[:3]:  # Top 3 pages
                            title = page.get("title", "")[:60]
                            url = page.get("url", "")
                            if url:
                                summary_parts.append(f"  • <{url}|{title}>...")
                
                elif action_type in ["jira_create", "create_jira_issue"]:
                    if isinstance(result_data, dict):
                        key = result_data.get("key", "")
                        if key:
                            url = f"https://uipath.atlassian.net/browse/{key}"
                            summary_parts.append(f"✓ Created Jira issue: <{url}|{key}>")
            else:
                summary_parts.append(f"✗ {action_type.replace('_', ' ').title()} failed")
        
        return "\n".join(summary_parts)
    
    async def _summarize_conversation_history(self, recent_messages: List[Dict[str, Any]]) -> str:
        """
        Summarize recent conversation history into a clean, concise summary.
        """
        if not recent_messages or len(recent_messages) < 3:
            return ""
        
        # Extract just the last few exchanges for context
        user_messages = []
        bot_messages = []
        
        for msg in recent_messages[-6:]:  # Last 6 messages
            user_name = msg.get("user_name", "")
            text = msg.get("text", "")[:100]  # Truncate
            
            if user_name not in ["bot", "autopilot"] and text:
                user_messages.append(text)
            elif text:
                bot_messages.append(text)
        
        if not user_messages and not bot_messages:
            return ""
        
        summary = f"Recent conversation: {len(user_messages)} user messages, {len(bot_messages)} bot responses"
        if user_messages:
            summary += f". Last user said: \"{user_messages[-1]}...\""
        
        return summary
