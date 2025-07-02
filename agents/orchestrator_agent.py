"""
Orchestrator Agent - Main coordination agent that analyzes queries and creates execution plans.
Uses Gemini 2.5 Pro for query analysis and tool orchestration.
Follows 5-step reasoning framework with recursive observation and replanning.
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.gemini_client import GeminiClient
from utils.prompt_loader import get_orchestrator_prompt, get_orchestrator_evaluation_prompt
from tools.vector_search import VectorSearchTool
from tools.perplexity_search import PerplexitySearchTool
from tools.outlook_meeting import OutlookMeetingTool
# AtlassianTool replaced by AtlassianToolbelt
from agents.atlassian_guru import AtlassianToolbelt
from agents.client_agent import ClientAgent
from services.core.memory_service import MemoryService
from services.data.token_manager import TokenManager
from services.data.entity_store import EntityStore
from services.processing.progress_tracker import ProgressTracker, ProgressEventType, emit_thinking, emit_searching, emit_processing, emit_generating, emit_error, emit_warning, emit_retry, emit_reasoning, emit_considering, emit_analyzing, StreamingReasoningEmitter
from services.core.trace_manager import trace_manager
from models.schemas import ProcessedMessage

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Main orchestrating agent with both:
    - Legacy methods (preserved for safety/compatibility)
    - New 5-step reasoning framework (for enhanced intelligence)
    
    New Framework:
    1. Analyze user intent
    2. Select tools strategically  
    3. Execute and observe critically
    4. Replan dynamically if needed
    5. Synthesize final clean output
    """

    def __init__(self,
                 memory_service: MemoryService,
                 progress_tracker: Optional[ProgressTracker] = None,
                 trace_manager=None):
        self.gemini_client = GeminiClient()
        self.vector_tool = VectorSearchTool()
        self.perplexity_tool = PerplexitySearchTool()
        self.outlook_tool = OutlookMeetingTool()
        self.trace_manager = trace_manager
        self.atlassian_guru = AtlassianToolbelt()
        self.client_agent = ClientAgent()
        self.memory_service = memory_service
        self.token_manager = TokenManager(model_name="gpt-4")
        self.entity_store = EntityStore(memory_service)
        self.progress_tracker = progress_tracker
        self.discovered_tools = []
        
        # NEW: Execution state tracking for 5-step reasoning
        self.current_execution_steps = []
        self.replanning_count = 0
        self.max_replanning_iterations = 3
        
        # LEGACY: Trace ID attribute for external compatibility
        self._current_trace_id = None

    async def discover_and_update_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from MCP server and update tool list"""
        try:
            capabilities = await self.atlassian_guru.get_capabilities()
            self.discovered_tools = capabilities.get("available_tools", [])
            logger.info(f"Updated tool list with {len(self.discovered_tools)} total tools from AtlassianToolbelt")
            return self.discovered_tools
        except Exception as e:
            logger.warning(f"Failed to discover tools: {e}")
            return []

    async def process_query(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        UPDATED: Main entry point now uses 5-step reasoning framework with recursive observation.
        
        Returns legacy format for compatibility:
        {
            "channel_id": "...",
            "thread_ts": "...", 
            "text": "response text",
            "timestamp": "...",
            "suggestions": [...],
            "confidence_level": "high|medium|low"
        }
        """
        start_time = time.time()
        
        # Reset execution state for new query
        self.current_execution_steps = []
        self.replanning_count = 0
        
        try:
            logger.info(f"Orchestrator starting 5-step reasoning for: {message.text[:100]}...")

            # Emit initial reasoning progress
            if self.progress_tracker:
                query_preview = message.text[:50] + "..." if len(message.text) > 50 else message.text
                await emit_considering(self.progress_tracker, "requirements", f"how to approach: {query_preview}")

            # Store conversation context
            await self._store_conversation_context(message)

            # NEW: STEP 1-2: Analyze user intent with FLUID REASONING and create strategic tool selection plan.
            if self.progress_tracker:
                await emit_reasoning(self.progress_tracker, "fluid_reasoning", "thinking through your request naturally...")
            
            initial_plan = await self._step1_2_analyze_and_plan_new(message)
            if not initial_plan:
                return await self._create_fallback_response_new("I'm having trouble understanding your request. Could you rephrase it?", message)

            # NEW: STEP 3-4-5: Execute with recursive observation and replanning
            final_clean_output = await self._step3_4_5_execute_observe_synthesize_new(initial_plan, message)
            
            if final_clean_output:
                # Background tasks (fire and forget) - REMOVED observer_agent integration
                asyncio.create_task(self._queue_entity_extraction(message, final_clean_output.get("synthesized_response", "")))
                
                total_time = time.time() - start_time
                logger.info(f"Orchestrator completed 5-step process in {total_time:.2f}s with {len(self.current_execution_steps)} steps")
                
                # Use enhanced client agent with clean output format
                final_response = await self._use_enhanced_client_agent_new(final_clean_output, message)
                if final_response:
                    return final_response
                
                # Fallback to legacy format conversion for compatibility
                return await self._convert_clean_output_to_legacy_format(final_clean_output, message)
            
            # If we reach here, the synthesis step failed completely - create a more helpful response
            return await self._create_fallback_response_new("I'm experiencing high demand right now, but I can still help you. Could you try rephrasing your question or ask me something else?", message)

        except Exception as e:
            logger.error(f"Error in orchestrator 5-step process: {e}")
            await trace_manager.complete_conversation_turn(success=False, error=str(e))
            if self.progress_tracker:
                await emit_error(self.progress_tracker, "processing_error", "internal system issue")
            return await self._create_fallback_response_new("I'm having trouble analyzing your request right now. Could you try rephrasing your question or ask me something else?", message)

    # ============================================================================
    # NEW: 5-STEP REASONING FRAMEWORK METHODS
    # ============================================================================

    async def _step1_2_analyze_and_plan_new(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        NEW: STEP 1-2: Analyze user intent with FLUID REASONING and create strategic tool selection plan.
        Enhanced with real-time reasoning display via message editing.
        """
        try:
            # Build context for analysis
            conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
            hybrid_history = await self._construct_hybrid_history(conversation_key, message.text)
            relevant_entities = await self._search_relevant_entities(message.text, conversation_key)

            # Discover available tools
            try:
                await asyncio.wait_for(self.discover_and_update_tools(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Tool discovery timed out, proceeding with default tools")

            # Build analysis context
            context = {
                "query": message.text,
                "user_info": {
                    "name": message.user_name,
                    "first_name": message.user_first_name,
                    "title": message.user_title,
                    "department": message.user_department
                },
                "channel": {"name": message.channel_name, "is_dm": message.is_dm},
                "conversation_memory": hybrid_history,
                "relevant_entities": relevant_entities
            }

            # NEW: FLUID REASONING PHASE with message-editing display
            if self.progress_tracker:
                await emit_reasoning(self.progress_tracker, "fluid_reasoning", "thinking through your request naturally...")

            reasoning_response = await self._fluid_reasoning_with_display_new(context, message)
            
            if reasoning_response and reasoning_response.get("plan"):
                # Initialize execution steps from plan
                plan = reasoning_response["plan"]
                self._initialize_execution_steps_new(plan)
                plan["fluid_reasoning"] = reasoning_response.get("reasoning", "")
                return plan

            return None

        except Exception as e:
            logger.error(f"Error in fluid reasoning and planning: {e}")
            return None

    async def _fluid_reasoning_with_display_new(self, context: Dict[str, Any], message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        NEW: Conduct fluid reasoning with real-time message editing to show thinking process.
        """
        try:
            # Phase 1: Free-form reasoning with streaming display
            if self.progress_tracker:
                await emit_reasoning(self.progress_tracker, "stream_of_consciousness", "💭 Thinking through your request...")

            reasoning_stages = [
                "💭 Understanding what you're really asking...",
                "🎯 Considering the best approach...", 
                "🔍 Thinking about which tools would be most effective...",
                "⚡ Planning the optimal strategy...",
                "📋 Structuring my execution plan..."
            ]

            # Get system prompt for fluid reasoning
            fluid_prompt = self._get_fluid_reasoning_prompt_new()
            user_prompt = f"Context: {json.dumps(context, indent=2)}\n\nQuery: \"{message.text}\"\n\nThink through this naturally and comprehensively."

            # Create reasoning callback for message editing
            reasoning_callback = self._create_reasoning_callback_new(reasoning_stages)

            # Generate streaming response with real-time display
            llm_start = time.time()
            try:
                reasoning_result = await asyncio.wait_for(
                    self.gemini_client.generate_streaming_response(
                        system_prompt=fluid_prompt,
                        user_prompt=user_prompt,
                        reasoning_callback=reasoning_callback,
                        model=self.gemini_client.pro_model,
                        max_tokens=20000,
                        temperature=0.3  # Lower temperature for focused reasoning
                    ),
                    timeout=15.0  # Reduced from 25.0 to prevent frequent timeouts
                )
            except asyncio.TimeoutError:
                logger.error("Fluid reasoning timed out")
                # Instead of returning None, create a basic plan to continue processing
                logger.info("Creating fallback plan after timeout")
                return {
                    "reasoning": "Reasoning timed out, using fallback approach",
                    "reasoning_steps": [],
                    "plan": self._create_fallback_plan_new(context)
                }

            # Log LLM call
            await trace_manager.log_llm_call(
                model=self.gemini_client.pro_model,
                prompt=f"FLUID REASONING: {user_prompt[:200]}...",
                response=reasoning_result.get("text", "")[:500],
                duration=time.time() - llm_start
            )

            # Phase 2: Extract structured plan from reasoning
            if self.progress_tracker:
                await emit_processing(self.progress_tracker, "plan_extraction", "🎯 Extracting execution plan from reasoning...")

            structured_plan = await self._extract_plan_from_reasoning_new(reasoning_result.get("text", ""), context)

            return {
                "reasoning": reasoning_result.get("text", ""),
                "reasoning_steps": reasoning_result.get("reasoning_steps", []),
                "plan": structured_plan
            }

        except Exception as e:
            logger.error(f"Error in fluid reasoning with display: {e}")
            
            # Check if this is a quota exhaustion error
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                logger.warning("Gemini Pro quota exhausted, creating fallback plan")
                # Create a fallback plan that allows processing to continue
                return {
                    "reasoning": "I'm experiencing high demand right now, but I can still help you. Let me check what information I can find.",
                    "reasoning_steps": ["Analyzing your request", "Checking available resources", "Preparing response"],
                    "plan": self._create_fallback_plan_new(context)
                }
            
            # For other errors, also create a fallback rather than stopping
            logger.warning("Creating fallback plan after error")
            return {
                "reasoning": "I encountered an issue during analysis, but let me try a different approach to help you.",
                "reasoning_steps": ["Analyzing request", "Using alternative approach"],
                "plan": self._create_fallback_plan_new(context)
            }

    def _create_reasoning_callback_new(self, reasoning_stages: List[str]) -> callable:
        """
        NEW: Create callback for updating Slack message with reasoning progress.
        Shows clean conversational progress instead of raw LLM reasoning.
        """
        stage_index = 0
        accumulated_reasoning = ""
        last_update_time = 0
        
        async def reasoning_callback(chunk_text: str, chunk_metadata: dict):
            nonlocal stage_index, accumulated_reasoning, last_update_time
            
            try:
                accumulated_reasoning += chunk_text
                current_time = time.time()
                
                # Throttle updates to prevent spam (minimum 2 seconds between updates)
                if current_time - last_update_time < 2.0:
                    return
                
                if self.progress_tracker:
                    # Advance stage based on content keywords
                    stage_keywords = ["approach", "strategy", "plan", "execute", "synthesis", "observe"]
                    for keyword in stage_keywords:
                        if keyword in chunk_text.lower() and stage_index < len(reasoning_stages) - 1:
                            stage_index = min(stage_index + 1, len(reasoning_stages) - 1)
                            break
                    
                    # Use clean stage message only (no raw reasoning snippets)
                    stage_message = reasoning_stages[stage_index] if stage_index < len(reasoning_stages) else "💡 Finalizing approach..."
                    
                    # Send clean progress message without raw reasoning content
                    await emit_reasoning(self.progress_tracker, "live_reasoning", stage_message)
                    last_update_time = current_time
                    
            except Exception as callback_error:
                # Don't let callback errors interrupt reasoning
                logger.debug(f"Reasoning callback error: {callback_error}")
        
        return reasoning_callback

    def _get_fluid_reasoning_prompt_new(self) -> str:
        """
        NEW: Get enhanced prompt for fluid reasoning phase.
        """
        return """You are an advanced AI orchestrator with fluid intelligence. Think naturally and comprehensively about how to approach this query.

ENGAGE IN FREE-FORM REASONING first. Think out loud about:

- What is the user really asking for? What context clues help you understand their true intent?
- What would be the most insightful and comprehensive approach?
- How can you orchestrate tools for maximum effect?
- What different angles should you explore?
- Should you use tools in parallel for richer insights?
- What tool combinations would create synergy?

Consider these tools:
- vector_search: Internal Slack conversations and team discussions
- perplexity_search: Current web information and real-time data  
- atlassian_search: Jira issues, Confluence pages, UiPath/Autopilot projects
- outlook_meeting: Calendar and meeting management

Think through your approach naturally, then at the end provide a structured JSON plan with:
- reasoning_summary
- complexity_level (simple|moderate|complex|research)  
- tools_needed
- execution_strategy
- specific queries/actions for each tool

Let your intelligence flow freely before structuring your response."""

    async def _extract_plan_from_reasoning_new(self, reasoning_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        NEW: Extract structured execution plan from fluid reasoning text.
        """
        try:
            if self.progress_tracker:
                await emit_processing(self.progress_tracker, "plan_structuring", "🔧 Converting reasoning into execution plan...")

            extraction_prompt = f"""
            Based on this reasoning about the user's query, extract a structured execution plan.

            Original Query: "{context['query']}"
            
            Reasoning: {reasoning_text}
            
            Extract and return ONLY a JSON plan with this structure:
            {{
                "reasoning_summary": "Brief summary of the thinking process",
                "complexity_level": "simple|moderate|complex|research",
                "analysis": "Key insights about user intent and approach",
                "tools_needed": ["list of tools to use"],
                "execution_strategy": "sequential|parallel|hybrid",
                "vector_queries": ["search terms"] (if vector_search needed),
                "perplexity_queries": ["web searches"] (if perplexity_search needed),
                "atlassian_actions": [{{"task": "description"}}] (if atlassian_search needed),
                "observation_plan": "What to assess in results",
                "synthesis_approach": "How to combine findings"
            }}
            """

            extraction_response = await asyncio.wait_for(
                self.gemini_client.generate_structured_response(
                    "You are an expert at extracting structured plans from reasoning text.",
                    extraction_prompt,
                    response_format="json",
                    model=self.gemini_client.flash_model,  # Use Flash for quick extraction
                    temperature=0.3  # Lower temperature for focused decision extraction
                ),
                timeout=8.0  # Reduced from 10.0 for faster response
            )

            if extraction_response:
                try:
                    plan = json.loads(extraction_response)
                    logger.info(f"Extracted execution plan from fluid reasoning: {plan.get('reasoning_summary', 'No summary')}")
                    return plan
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted plan JSON: {e}")
                    return self._create_fallback_plan_new(context)
            
            return self._create_fallback_plan_new(context)

        except Exception as e:
            logger.error(f"Error extracting plan from reasoning: {e}")
            return self._create_fallback_plan_new(context)

    def _create_fallback_plan_new(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        NEW: Create a fallback plan when plan extraction fails.
        """
        query = context.get("query", "")
        
        # Simple heuristic-based planning as fallback
        tools_needed = []
        
        # Check for keywords to determine tools
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ["team", "discussion", "said", "conversation", "chat"]):
            tools_needed.append("vector_search")
        
        if any(keyword in query_lower for keyword in ["current", "latest", "recent", "news", "update"]):
            tools_needed.append("perplexity_search")
        
        if any(keyword in query_lower for keyword in ["uipath", "autopilot", "jira", "confluence", "project"]):
            tools_needed.append("atlassian_search")
        
        if any(keyword in query_lower for keyword in ["meeting", "schedule", "calendar", "availability"]):
            tools_needed.append("outlook_meeting")
        
        # Default to vector search if no specific indicators
        if not tools_needed:
            tools_needed = ["vector_search"]

        return {
            "reasoning_summary": "Fallback plan based on keyword analysis",
            "complexity_level": "moderate",
            "analysis": f"Analyzing query for keywords, selected tools: {', '.join(tools_needed)}",
            "tools_needed": tools_needed,
            "execution_strategy": "sequential",
            "vector_queries": [query] if "vector_search" in tools_needed else [],
            "perplexity_queries": [query] if "perplexity_search" in tools_needed else [],
            "atlassian_actions": [{"task": f"Search for information about: {query}"}] if "atlassian_search" in tools_needed else [],
            "observation_plan": "Check if results directly answer the user's question",
            "synthesis_approach": "Combine all findings into a comprehensive response"
        }

    async def _step3_4_5_execute_observe_synthesize_new(self, plan: Dict[str, Any], message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        NEW: STEP 3-4-5: Execute tools, observe results critically, replan if needed, then synthesize.
        Uses recursive observation pattern.
        """
        all_results = []
        
        try:
            # STEP 3: Execute planned tools
            if self.progress_tracker:
                await emit_processing(self.progress_tracker, "executing_plan", "planned search strategy")
            
            execution_results = await self._execute_planned_tools_new(plan, message)
            all_results.extend(execution_results)
            
            # STEP 4: Observe and decide if replanning is needed (RECURSIVE CALL)
            needs_more = await self._step4_observe_and_replan_new(all_results, plan, message)
            
            if needs_more and self.replanning_count < self.max_replanning_iterations:
                # Recursive call for additional tool execution
                additional_results = await self._step3_4_5_execute_observe_synthesize_new(needs_more, message)
                if additional_results and additional_results.get("raw_results"):
                    # Merge additional results into our synthesis
                    all_results.extend(additional_results.get("raw_results", []))
            
            # STEP 5: Synthesize final clean output
            if self.progress_tracker:
                await emit_generating(self.progress_tracker, "response_generation", "comprehensive response")
            
            final_output = await self._step5_synthesize_output_new(all_results, plan, message)
            
            # Add raw results for potential recursive calls
            if final_output:
                final_output["raw_results"] = all_results
            
            return final_output

        except Exception as e:
            logger.error(f"Error in execute-observe-synthesize cycle: {e}")
            return None

    async def _step4_observe_and_replan_new(self, results: List[Dict], original_plan: Dict, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        NEW: STEP 4: Critically observe results and decide if replanning is needed.
        This is where the recursive observation happens.
        """
        try:
            self.replanning_count += 1
            
            # Quick quality check first
            if not results or all(not r.get("success", True) for r in results):
                logger.info("All tool results failed, attempting replanning")
                return await self._create_replan_from_failures_new(results, original_plan, message)
            
            # Ask LLM to observe results and decide next steps
            observation_response = await self._llm_observe_results_new(results, original_plan, message)
            
            if observation_response and observation_response.get("needs_more_tools"):
                logger.info(f"LLM observation suggests more tools needed: {observation_response.get('reasoning', 'No reason given')}")
                # Update execution steps
                self._update_execution_steps_from_observation_new(observation_response)
                return observation_response.get("new_plan")
            
            logger.info("LLM observation indicates results are sufficient for synthesis")
            return None  # No more tools needed, proceed to synthesis

        except Exception as e:
            logger.error(f"Error in observation and replanning: {e}")
            return None

    async def _step5_synthesize_output_new(self, all_results: List[Dict], plan: Dict, message: ProcessedMessage) -> Dict[str, Any]:
        """
        NEW: STEP 5: Synthesize all results into clean output format for client agent with conversational progress.
        """
        from services.processing.progress_tracker import emit_synthesis_progress, emit_narration, emit_discovery
        
        try:
            # Mark synthesis step as in progress with conversational message
            self._add_execution_step_new("synthesize_results", "Synthesizing all findings into final response", "in_progress")
            
            if self.progress_tracker:
                await emit_synthesis_progress(self.progress_tracker, 
                                            "Analyzing all the information I found to give you the best answer...")
            
            # Extract and categorize results by tool type
            vector_results = [r for r in all_results if r.get("tool_type") == "vector_search"]
            web_results = [r for r in all_results if r.get("tool_type") == "perplexity_search"]
            atlassian_results = [r for r in all_results if r.get("tool_type") == "atlassian_search"]
            meeting_results = [r for r in all_results if r.get("tool_type") == "outlook_meeting"]
            
            # Conversational progress about what we're synthesizing
            if self.progress_tracker:
                synthesis_sources = []
                if vector_results: synthesis_sources.append(f"{len(vector_results)} team discussions")
                if web_results: synthesis_sources.append(f"{len(web_results)} web sources")
                if atlassian_results: synthesis_sources.append(f"{len(atlassian_results)} project resources")
                if meeting_results: synthesis_sources.append(f"{len(meeting_results)} meeting actions")
                
                if synthesis_sources:
                    await emit_narration(self.progress_tracker, 
                                       f"Combining insights from {', '.join(synthesis_sources)}...")
            
            # Build comprehensive context for synthesis
            synthesis_context = {
                "original_query": message.text,
                "user_context": {
                    "first_name": message.user_first_name,
                    "title": message.user_title,
                    "department": message.user_department
                },
                "execution_plan": plan.get("analysis", ""),
                "execution_steps": self.current_execution_steps,
                "results_summary": {
                    "vector_search": len(vector_results),
                    "web_search": len(web_results), 
                    "atlassian_search": len(atlassian_results),
                    "meeting_actions": len(meeting_results)
                },
                "detailed_results": {
                    "vector_findings": self._summarize_vector_results_new(vector_results),
                    "web_findings": self._summarize_web_results_new(web_results),
                    "project_findings": self._summarize_atlassian_results_new(atlassian_results),
                    "meeting_outcomes": self._summarize_meeting_results_new(meeting_results)
                }
            }
            
            # Use LLM to synthesize clean final response with progress
            if self.progress_tracker:
                await emit_narration(self.progress_tracker, 
                                   "Creating a comprehensive response that directly answers your question...")
            
            synthesized_response = await self._llm_synthesize_final_response_new(synthesis_context)
            
            # Extract key findings
            key_findings = self._extract_key_findings_new(all_results, plan)
            
            # Generate source links
            source_links = self._generate_source_links_new(all_results)
            
            # Assess confidence level
            confidence_level = self._assess_confidence_level_new(all_results, plan)
            
            # Generate follow-up suggestions
            suggested_followups = self._generate_followup_suggestions_new(synthesis_context)
            
            # Mark synthesis as completed with conversational message
            self._update_execution_step_new("synthesize_results", "completed", {"response_length": len(synthesized_response)})
            
            if self.progress_tracker:
                response_quality = "comprehensive" if len(synthesized_response) > 500 else "focused"
                await emit_discovery(self.progress_tracker, 
                                   f"Perfect! I've prepared a {response_quality} answer with {len(key_findings)} key insights and {len(source_links)} sources.")
            
            clean_output = {
                "synthesized_response": synthesized_response,
                "key_findings": key_findings,
                "source_links": source_links,
                "confidence_level": confidence_level,
                "suggested_followups": suggested_followups,
                "requires_human_input": False,
                "execution_summary": {
                    "steps_completed": len([s for s in self.current_execution_steps if s["status"] == "completed"]),
                    "total_steps": len(self.current_execution_steps),
                    "replanning_iterations": self.replanning_count
                }
            }
            
            logger.info(f"Synthesized clean output: {len(synthesized_response)} chars, {len(key_findings)} findings, confidence: {confidence_level}")
            return clean_output

        except asyncio.TimeoutError:
            logger.warning("LLM synthesis timed out, using basic summary")
            return {
                "synthesized_response": "I found information from multiple sources but the detailed synthesis took too long. Let me give you the key points I discovered.",
                "key_findings": [],
                "source_links": [],
                "confidence_level": "low",
                "suggested_followups": [],
                "requires_human_input": False,
                "execution_summary": {
                    "steps_completed": 0,
                    "total_steps": 0,
                    "replanning_iterations": 0
                }
            }
        except Exception as e:
            logger.error(f"Error in LLM synthesis: {e}")
            return {
                "synthesized_response": "I gathered information from multiple sources but encountered an issue creating a comprehensive response.",
                "key_findings": [],
                "source_links": [],
                "confidence_level": "low",
                "suggested_followups": [],
                "requires_human_input": False,
                "execution_summary": {
                    "steps_completed": 0,
                    "total_steps": 0,
                    "replanning_iterations": 0
                }
            }

    # ============================================================================
    # NEW: SUPPORTING METHODS FOR 5-STEP FRAMEWORK
    # ============================================================================

    async def _use_enhanced_client_agent_new(self, clean_output: Dict[str, Any], message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """NEW: Use enhanced client agent with clean output format from 5-step reasoning"""
        try:
            logger.info("Using enhanced client agent with clean orchestrator output...")
            
            # Build user context for enhanced client agent
            user_context = {
                "query": message.text,
                "user": {
                    "first_name": message.user_first_name or "",
                    "title": message.user_title or "",
                    "department": message.user_department or ""
                },
                "channel_context": {
                    "is_dm": message.is_dm,
                    "channel_name": message.channel_name,
                    "thread_ts": message.thread_ts
                },
                "conversation_history": "",  # Could be enhanced later
                "trace_id": None  # Could be enhanced with proper trace ID
            }
            
            # Initialize enhanced client agent
            enhanced_client = ClientAgent()
            
            # Generate sophisticated response using new interface
            enhanced_result = await enhanced_client.generate_response(clean_output, user_context)
            
            if enhanced_result:
                # Convert enhanced response to legacy format for Slack Gateway compatibility
                return {
                    "channel_id": message.channel_id,
                    "thread_ts": message.thread_ts or message.message_ts,
                    "text": enhanced_result.get("text", ""),
                    "timestamp": datetime.now().isoformat(),
                    "suggestions": enhanced_result.get("suggestions", []),
                    "confidence_level": enhanced_result.get("confidence_level", "medium"),
                    "source_links": clean_output.get("source_links", []),
                    "execution_summary": clean_output.get("execution_summary", {}),
                    "enhanced_mode": True  # Flag to indicate enhanced processing
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error using enhanced client agent: {e}")
            return None

    async def _convert_clean_output_to_legacy_format(self, clean_output: Dict[str, Any], message: ProcessedMessage) -> Dict[str, Any]:
        """NEW: Convert new clean output format to legacy format for compatibility"""
        
        # Enhanced: Also generate enhanced client agent response
        enhanced_response = asyncio.create_task(self._generate_enhanced_client_response(clean_output, message))
        
        # Legacy format for backward compatibility
        legacy_response = {
            "channel_id": message.channel_id,
            "thread_ts": message.thread_ts or message.message_ts,
            "text": clean_output.get("synthesized_response", ""),
            "timestamp": datetime.now().isoformat(),
            "suggestions": clean_output.get("suggested_followups", []),
            "confidence_level": clean_output.get("confidence_level", "medium"),
            "source_links": clean_output.get("source_links", []),
            "execution_summary": clean_output.get("execution_summary", {})
        }
        
        # Try to use enhanced client agent response if available
        try:
            enhanced_result = await asyncio.wait_for(enhanced_response, timeout=5.0)
            if enhanced_result and enhanced_result.get("text"):
                legacy_response["text"] = enhanced_result["text"]
                legacy_response["suggestions"] = enhanced_result.get("suggestions", legacy_response["suggestions"])
                legacy_response["enhanced_by_client_agent"] = True
                logger.info("Successfully enhanced response using enhanced client agent")
        except Exception as e:
            logger.warning(f"Enhanced client agent failed, using orchestrator synthesis: {e}")
            legacy_response["enhanced_by_client_agent"] = False
        
        return legacy_response
    
    async def _generate_enhanced_client_response(self, clean_output: Dict[str, Any], message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """NEW: Generate enhanced response using the enhanced client agent"""
        try:
            # Prepare message context for enhanced client agent
            message_context = {
                "user": {
                    "id": message.user_id,
                    "name": message.user_name,
                    "first_name": message.user_first_name,
                    "display_name": message.user_display_name,
                    "title": message.user_title,
                    "department": message.user_department
                },
                "context": {
                    "channel_id": message.channel_id,
                    "channel_name": message.channel_name,
                    "is_dm": message.is_dm,
                    "thread_ts": message.thread_ts,
                    "message_ts": message.message_ts
                },
                "query": message.text
            }
            
            # Call enhanced client agent with clean orchestrator output
            enhanced_response = await self.client_agent.generate_response(clean_output, message_context)
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error generating enhanced client response: {e}")
            return None

    async def _store_conversation_context(self, message: ProcessedMessage):
        """Store conversation context in memory systems"""
        try:
            thread_identifier = message.thread_ts or message.message_ts
            conversation_key = f"conv:{message.channel_id}:{thread_identifier}"
            
            # Store in sliding window memory
            await self.memory_service.store_raw_message(conversation_key, message.dict(), max_messages=10)
            
            # Store conversation context
            await self.memory_service.store_conversation_context(conversation_key, message.dict(), ttl=86400)
            
        except Exception as e:
            logger.error(f"Error storing conversation context: {e}")

    async def _get_reasoning_system_prompt_new(self) -> str:
        """NEW: Get the 5-step reasoning system prompt from prompts.yaml"""
        return get_orchestrator_prompt()

    def _parse_planning_response_new(self, response: str) -> Optional[Dict[str, Any]]:
        """NEW: Parse LLM planning response into execution plan"""
        try:
            # Clean response to extract JSON from markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                start_index = cleaned_response.find('{')
                end_index = cleaned_response.rfind('}') + 1
                if start_index != -1 and end_index > start_index:
                    cleaned_response = cleaned_response[start_index:end_index]
            elif cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_response

            plan = json.loads(cleaned_response)
            logger.info(f"Parsed execution plan: {plan.get('analysis', 'No analysis')[:100]}...")
            return plan
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse planning response JSON: {e}")
            logger.error(f"Raw response: {response[:500]}...")
            return None

    def _initialize_execution_steps_new(self, plan: Dict[str, Any]):
        """NEW: Initialize execution steps from the planning phase"""
        self.current_execution_steps = []
        
        # Add planned tool executions as steps
        tools_needed = plan.get("tools_needed", [])
        for i, tool in enumerate(tools_needed, 1):
            self._add_execution_step_new(
                f"execute_{tool}",
                f"Execute {tool} with planned queries",
                "pending"
            )
        
        # Add synthesis step
        self._add_execution_step_new("synthesize_results", "Synthesize all findings into final response", "pending")

    def _add_execution_step_new(self, action_id: str, description: str, status: str, result: Dict = None):
        """NEW: Add a new execution step"""
        step = {
            "step": len(self.current_execution_steps) + 1,
            "action_id": action_id,
            "action": description,
            "status": status,  # pending, in_progress, completed, failed
            "timestamp": datetime.now().isoformat(),
            "result": result or {}
        }
        self.current_execution_steps.append(step)
        logger.debug(f"Added execution step {step['step']}: {description} ({status})")

    def _update_execution_step_new(self, action_id: str, status: str, result: Dict = None):
        """NEW: Update an existing execution step"""
        for step in self.current_execution_steps:
            if step["action_id"] == action_id:
                step["status"] = status
                step["timestamp"] = datetime.now().isoformat()
                if result:
                    step["result"].update(result)
                logger.debug(f"Updated execution step {step['step']}: {step['action']} → {status}")
                break

    def _update_execution_steps_from_observation_new(self, observation: Dict[str, Any]):
        """NEW: Update execution steps based on observation response"""
        try:
            new_actions = observation.get("new_actions", [])
            for action in new_actions:
                self._add_execution_step_new(
                    action.get("action_id", f"replan_{len(self.current_execution_steps)}"),
                    action.get("description", "Additional action from replanning"),
                    "pending"
                )
        except Exception as e:
            logger.error(f"Error updating execution steps from observation: {e}")

    async def _create_fallback_response_new(self, message: str, processed_message: ProcessedMessage) -> Dict[str, Any]:
        """NEW: Create a fallback response in the legacy output format"""
        return {
            "channel_id": processed_message.channel_id,
            "thread_ts": processed_message.thread_ts or processed_message.message_ts,
            "text": message,
            "timestamp": datetime.now().isoformat(),
            "suggestions": ["Could you rephrase your question?", "What specific aspect would you like to know more about?"],
            "confidence_level": "low",
            "source_links": [],
            "requires_human_input": True
        }

    async def _execute_planned_tools_new(self, plan: Dict[str, Any], message: ProcessedMessage) -> List[Dict[str, Any]]:
        """NEW: Execute all planned tools with conversational progress and result previews"""
        from services.processing.progress_tracker import emit_search_with_results, emit_analysis_insight, emit_discovery, emit_narration
        
        results = []
        tools_needed = plan.get("tools_needed", [])
        
        # Execute vector search with rich progress
        if "vector_search" in tools_needed:
            vector_queries = plan.get("vector_queries", [])
            for query in vector_queries:
                self._update_execution_step_new(f"execute_vector_search", "in_progress")
                
                try:
                    # Conversational progress message
                    if self.progress_tracker:
                        await emit_narration(self.progress_tracker, 
                                           f"Let me check what the team has been discussing about '{query}'...")
                    
                    search_results = await self.vector_tool.search(query=query, top_k=5)
                    
                    # Convert results for preview display
                    preview_results = []
                    for result in search_results:
                        preview_results.append({
                            "content": result.get("content", ""),
                            "user_name": result.get("user_name", "Team member"),
                            "timestamp": result.get("timestamp", ""),
                            "score": result.get("score", 0)
                        })
                    
                    # Show results with conversational progress
                    if self.progress_tracker and preview_results:
                        await emit_search_with_results(self.progress_tracker, "vector_search", query, preview_results)
                        
                        # Add insight about findings
                        if len(preview_results) > 0:
                            await emit_discovery(self.progress_tracker, 
                                               f"Found {len(preview_results)} relevant team discussions!")
                    
                    results.append({
                        "tool_type": "vector_search",
                        "query": query,
                        "results": search_results,
                        "success": len(search_results) > 0
                    })
                    self._update_execution_step_new(f"execute_vector_search", "completed", {"results_count": len(search_results)})
                    
                except Exception as e:
                    logger.error(f"Vector search error: {e}")
                    if self.progress_tracker:
                        await emit_narration(self.progress_tracker, 
                                           f"Had trouble accessing team discussions - trying alternative sources...")
                    results.append({"tool_type": "vector_search", "query": query, "error": str(e), "success": False})
                    self._update_execution_step_new(f"execute_vector_search", "failed", {"error": str(e)})

        # Execute perplexity search with rich progress
        if "perplexity_search" in tools_needed:
            perplexity_queries = plan.get("perplexity_queries", [])
            for query in perplexity_queries:
                self._update_execution_step_new(f"execute_perplexity_search", "in_progress")
                
                try:
                    # Conversational progress message
                    if self.progress_tracker:
                        await emit_narration(self.progress_tracker, 
                                           f"Now let me get the latest information from the web about '{query}'...")
                    
                    search_result = await self.perplexity_tool.search(query=query, max_tokens=2000)
                    
                    # Convert result for preview display
                    preview_results = []
                    if search_result and search_result.get("content"):
                        # Create preview from perplexity result
                        citations = search_result.get("citations", [])
                        for citation in citations[:3]:  # Top 3 sources
                            preview_results.append({
                                "title": citation.get("title", "Web Source"),
                                "source": citation.get("source", ""),
                                "url": citation.get("url", ""),
                                "snippet": citation.get("snippet", "")[:100] + "..." if citation.get("snippet") else ""
                            })
                    
                    # Show results with conversational progress
                    if self.progress_tracker and preview_results:
                        await emit_search_with_results(self.progress_tracker, "perplexity_search", query, preview_results)
                        
                        # Add insight about web findings
                        if search_result and search_result.get("content"):
                            content_length = len(search_result["content"])
                            await emit_discovery(self.progress_tracker, 
                                               f"Found current information ({content_length} chars) from {len(preview_results)} sources!")
                    
                    results.append({
                        "tool_type": "perplexity_search",
                        "query": query,
                        "result": search_result,
                        "success": bool(search_result and search_result.get("content"))
                    })
                    self._update_execution_step_new(f"execute_perplexity_search", "completed", {"has_content": bool(search_result and search_result.get("content"))})
                    
                except Exception as e:
                    logger.error(f"Perplexity search error: {e}")
                    if self.progress_tracker:
                        await emit_narration(self.progress_tracker, 
                                           f"Web search encountered an issue - focusing on internal knowledge...")
                    results.append({"tool_type": "perplexity_search", "query": query, "error": str(e), "success": False})
                    self._update_execution_step_new(f"execute_perplexity_search", "failed", {"error": str(e)})

        # Execute Atlassian search with rich progress
        if "atlassian_search" in tools_needed:
            atlassian_actions = plan.get("atlassian_actions", [])
            for action in atlassian_actions:
                self._update_execution_step_new(f"execute_atlassian_search", "in_progress")
                
                try:
                    task = action.get("task", "General Atlassian search")
                    
                    # Conversational progress message
                    if self.progress_tracker:
                        await emit_narration(self.progress_tracker, 
                                           f"Let me check our project documentation and tickets...")
                    
                    result = await self.atlassian_guru.execute_task(task)
                    
                    # Convert result for preview display
                    preview_results = []
                    if result and result.get("status") == "success" and result.get("data"):
                        data = result["data"]
                        if isinstance(data, list):
                            for item in data[:3]:  # Top 3 items
                                if isinstance(item, dict):
                                    preview_results.append({
                                        "title": item.get("title", "Project Item"),
                                        "type": item.get("type", "document"),
                                        "url": item.get("url", ""),
                                        "summary": item.get("summary", "")[:80] + "..." if item.get("summary") else ""
                                    })
                    
                    # Show results with conversational progress
                    if self.progress_tracker and preview_results:
                        await emit_search_with_results(self.progress_tracker, "atlassian_search", task, preview_results)
                        
                        # Add insight about project findings
                        if result and result.get("status") == "success":
                            await emit_discovery(self.progress_tracker, 
                                               f"Found {len(preview_results)} relevant project resources!")
                    
                    results.append({
                        "tool_type": "atlassian_search",
                        "task": task,
                        "result": result,
                        "success": result and result.get("status") == "success"
                    })
                    self._update_execution_step_new(f"execute_atlassian_search", "completed", {"status": result.get("status") if result else "no_result"})
                    
                except Exception as e:
                    logger.error(f"Atlassian search error: {e}")
                    if self.progress_tracker:
                        await emit_narration(self.progress_tracker, 
                                           f"Project search encountered an issue - using available information...")
                    results.append({"tool_type": "atlassian_search", "task": action.get("task", ""), "error": str(e), "success": False})
                    self._update_execution_step_new(f"execute_atlassian_search", "failed", {"error": str(e)})

        # Summary of all findings
        if self.progress_tracker and results:
            successful_results = [r for r in results if r.get("success", False)]
            total_tools = len(results)
            successful_tools = len(successful_results)
            
            if successful_tools > 0:
                await emit_analysis_insight(self.progress_tracker, 
                                          f"Great! I gathered information from {successful_tools}/{total_tools} sources. Let me analyze what I found...",
                                          [f"✓ {r['tool_type'].replace('_', ' ').title()}: {'Success' if r.get('success') else 'Failed'}" for r in results])
            else:
                await emit_narration(self.progress_tracker, 
                                   "I encountered some challenges gathering information, but let me work with what I can access...")

        return results

    async def _llm_observe_results_new(self, results: List[Dict], original_plan: Dict, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """NEW: Use LLM to observe results and decide if more tools are needed"""
        try:
            # Build observation context
            observation_context = {
                "original_query": message.text,
                "original_plan": original_plan.get("analysis", ""),
                "results_summary": {
                    "total_results": len(results),
                    "successful_tools": len([r for r in results if r.get("success", True)]),
                    "failed_tools": len([r for r in results if not r.get("success", True)]),
                    "tools_executed": list(set(r.get("tool_type", "unknown") for r in results))
                },
                "execution_steps_completed": len([s for s in self.current_execution_steps if s["status"] == "completed"])
            }

            # Simple observation prompt
            observation_prompt = f"""
            Original query: "{message.text}"
            
            Results obtained: {len(results)} tool executions
            Successful: {observation_context['results_summary']['successful_tools']}
            Failed: {observation_context['results_summary']['failed_tools']}
            
            Based on these results, do we have enough information to answer the user's question comprehensively?
            
            Respond with JSON:
            {{
                "needs_more_tools": true/false,
                "reasoning": "Brief explanation of decision",
                "new_plan": {{"tools_needed": ["tool"], "queries": ["new query"]}} or null
            }}
            """

            response = await asyncio.wait_for(
                self.gemini_client.generate_response(
                    get_orchestrator_evaluation_prompt(),
                    observation_prompt,
                    model=self.gemini_client.flash_model,  # Use Flash for quick observation
                    max_tokens=5000,
                    temperature=0.3
                ),
                timeout=10.0
            )

            if response:
                try:
                    # Parse observation response
                    observation = json.loads(response.strip())
                    return observation
                except json.JSONDecodeError:
                    logger.warning("Failed to parse observation response as JSON")
                    return None

            return None

        except Exception as e:
            logger.error(f"Error in LLM observation: {e}")
            return None

    async def _create_replan_from_failures_new(self, failed_results: List[Dict], original_plan: Dict, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """NEW: Create a replan when all tools failed"""
        # Simple fallback: try different tools or different queries
        original_tools = original_plan.get("tools_needed", [])
        
        # If vector search failed, try perplexity
        if "vector_search" in original_tools and "perplexity_search" not in original_tools:
            return {
                "tools_needed": ["perplexity_search"],
                "perplexity_queries": [message.text],
                "analysis": "Falling back to web search after internal search failed"
            }
        
        # If perplexity failed, try atlassian
        if "perplexity_search" in original_tools and "atlassian_search" not in original_tools:
            return {
                "tools_needed": ["atlassian_search"],
                "atlassian_actions": [{"task": f"Search for information about: {message.text}"}],
                "analysis": "Falling back to project search after web search failed"
            }
        
        return None

    async def _llm_synthesize_final_response_new(self, synthesis_context: Dict[str, Any]) -> str:
        """NEW: Use LLM to synthesize all results into a comprehensive response"""
        try:
            synthesis_prompt = f"""
            Synthesize the following information into a comprehensive, helpful response:
            
            Original Query: "{synthesis_context['original_query']}"
            User: {synthesis_context['user_context']['first_name']} ({synthesis_context['user_context']['title']})
            
            Search Results Summary:
            - Vector search results: {synthesis_context['results_summary']['vector_search']} findings
            - Web search results: {synthesis_context['results_summary']['web_search']} findings  
            - Project information: {synthesis_context['results_summary']['atlassian_search']} findings
            
            Detailed Findings:
            {synthesis_context['detailed_results']['vector_findings']}
            {synthesis_context['detailed_results']['web_findings']}
            {synthesis_context['detailed_results']['project_findings']}
            
            Create a comprehensive, helpful response that directly answers the user's question using the information found.
            Be specific, actionable, and cite relevant sources naturally.
            """

            # Try Pro model first, fallback to Flash on quota exhaustion
            try:
                response = await asyncio.wait_for(
                    self.gemini_client.generate_response(
                        "You are an expert at synthesizing information from multiple sources into clear, helpful responses.",
                        synthesis_prompt,
                        model=self.gemini_client.pro_model,  # Use Flash for synthesis
                        max_tokens=5000,
                        temperature=0.3,  # Lower temperature for focused synthesis
                        include_reasoning=True  # Enable thinking mode
                    ),
                    timeout=12.0  # Reduced from 15.0 for faster response
                )
                
                if response:
                    return response
                
            except Exception as pro_error:
                # Check if it's a quota exhaustion error
                if "429" in str(pro_error) or "RESOURCE_EXHAUSTED" in str(pro_error) or "quota" in str(pro_error).lower():
                    logger.warning("Gemini Pro quota exhausted during synthesis, falling back to Flash model")
                    try:
                        # Fallback to Flash model for synthesis
                        response = await asyncio.wait_for(
                            self.gemini_client.generate_response(
                                "You are an expert at synthesizing information from multiple sources into clear, helpful responses.",
                                synthesis_prompt,
                                model=self.gemini_client.flash_model,  # Fallback to Flash
                                max_tokens=5000,
                                temperature=0.3,  # Lower temperature for focused synthesis
                                include_reasoning=True  # Enable thinking mode
                            ),
                            timeout=12.0
                        )
                        
                        if response:
                            return response
                    except Exception as flash_error:
                        logger.error(f"Flash model also failed during synthesis: {flash_error}")
                else:
                    logger.error(f"Non-quota error in Pro synthesis: {pro_error}")
            
            # If both models fail or no response, create a basic synthesis
            basic_response = self._create_basic_synthesis_response(synthesis_context)
            return basic_response if basic_response else "I found relevant information but had trouble synthesizing it clearly."

        except asyncio.TimeoutError:
            logger.warning("LLM synthesis timed out, using basic summary")
            return "I found information from multiple sources but the detailed synthesis took too long. Let me give you the key points I discovered."
        except Exception as e:
            logger.error(f"Error in LLM synthesis: {e}")
            return "I gathered information from multiple sources but encountered an issue creating a comprehensive response."

    def _create_basic_synthesis_response(self, synthesis_context: Dict[str, Any]) -> str:
        """Create a basic synthesis response when LLM synthesis fails"""
        try:
            query = synthesis_context.get('original_query', '')
            results_summary = synthesis_context.get('results_summary', {})
            
            # Create basic response structure
            response_parts = [f"Based on your question about '{query}', here's what I found:"]
            
            # Summarize what was searched
            sources_found = []
            if results_summary.get('vector_search', 0) > 0:
                sources_found.append(f"{results_summary['vector_search']} team discussions")
            if results_summary.get('web_search', 0) > 0:
                sources_found.append(f"{results_summary['web_search']} web sources")
            if results_summary.get('atlassian_search', 0) > 0:
                sources_found.append(f"{results_summary['atlassian_search']} project resources")
            
            if sources_found:
                response_parts.append(f"I searched through {', '.join(sources_found)} and found relevant information.")
            else:
                response_parts.append("I searched through multiple sources for relevant information.")
            
            # Add a helpful closing
            response_parts.append("I'm experiencing high demand right now, but the information I found should help answer your question. Feel free to ask for more specific details about any aspect.")
            
            return " ".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error creating basic synthesis response: {e}")
            return "I found relevant information but am experiencing high demand. Please try rephrasing your question and I'll help you right away."

    def _summarize_vector_results_new(self, vector_results: List[Dict]) -> str:
        """NEW: Summarize vector search results"""
        if not vector_results:
            return ""
        
        summary_parts = []
        for result in vector_results:
            if result.get("success") and result.get("results"):
                results = result["results"]
                summary_parts.append(f"Found {len(results)} relevant documents for '{result['query']}'")
                for i, doc in enumerate(results[:2], 1):  # Top 2 docs
                    content = doc.get("content", "")[:100] + "..."
                    summary_parts.append(f"  {i}. {content}")
        
        return "\n".join(summary_parts)

    def _summarize_web_results_new(self, web_results: List[Dict]) -> str:
        """NEW: Summarize perplexity web search results"""
        if not web_results:
            return ""
        
        summary_parts = []
        for result in web_results:
            if result.get("success") and result.get("result"):
                web_result = result["result"]
                content = web_result.get("content", "")[:150] + "..."
                citations = len(web_result.get("citations", []))
                summary_parts.append(f"Web search for '{result['query']}': {content} ({citations} sources)")
        
        return "\n".join(summary_parts)

    def _summarize_atlassian_results_new(self, atlassian_results: List[Dict]) -> str:
        """NEW: Summarize Atlassian search results"""
        if not atlassian_results:
            return ""
        
        summary_parts = []
        for result in atlassian_results:
            if result.get("success") and result.get("result"):
                atlassian_result = result["result"]
                message = atlassian_result.get("message", "")[:100] + "..."
                summary_parts.append(f"Project search: {message}")
        
        return "\n".join(summary_parts)

    def _summarize_meeting_results_new(self, meeting_results: List[Dict]) -> str:
        """NEW: Summarize meeting action results"""
        if not meeting_results:
            return ""
        
        summary_parts = []
        for result in meeting_results:
            action_type = result.get("action_type", "unknown")
            success = result.get("success", False)
            status = "✓" if success else "✗"
            summary_parts.append(f"{status} {action_type}")
        
        return "\n".join(summary_parts)

    def _extract_key_findings_new(self, all_results: List[Dict], plan: Dict) -> List[str]:
        """NEW: Extract key findings from all results"""
        findings = []
        
        for result in all_results:
            if result.get("success"):
                tool_type = result.get("tool_type", "")
                if tool_type == "vector_search" and result.get("results"):
                    findings.append(f"Found {len(result['results'])} relevant documents in knowledge base")
                elif tool_type == "perplexity_search" and result.get("result", {}).get("content"):
                    findings.append("Located current web information on the topic")
                elif tool_type == "atlassian_search" and result.get("result", {}).get("status") == "success":
                    findings.append("Retrieved relevant project and documentation information")
        
        return findings[:5]  # Limit to top 5 findings

    def _generate_source_links_new(self, all_results: List[Dict]) -> List[Dict[str, str]]:
        """NEW: Generate source links from results"""
        links = []
        
        for result in all_results:
            if result.get("success"):
                tool_type = result.get("tool_type", "")
                
                if tool_type == "perplexity_search" and result.get("result", {}).get("citations"):
                    citations = result["result"]["citations"]
                    for citation in citations[:3]:  # Top 3 citations
                        if citation.get("url"):
                            links.append({
                                "title": citation.get("title", "Web Source"),
                                "url": citation["url"],
                                "type": "web"
                            })
                
                elif tool_type == "atlassian_search" and result.get("result", {}).get("data"):
                    # Extract Atlassian links if available in result data
                    data = result["result"]["data"]
                    if isinstance(data, list):
                        for item in data[:2]:  # Top 2 items
                            if isinstance(item, dict) and item.get("url"):
                                links.append({
                                    "title": item.get("title", "Project Resource"),
                                    "url": item["url"],
                                    "type": "confluence" if "confluence" in item["url"] else "jira"
                                })
        
        return links[:5]  # Limit to 5 source links

    def _assess_confidence_level_new(self, all_results: List[Dict], plan: Dict) -> str:
        """NEW: Assess confidence level based on results quality"""
        if not all_results:
            return "low"
        
        successful_results = [r for r in all_results if r.get("success", True)]
        success_rate = len(successful_results) / len(all_results) if all_results else 0
        
        # Check for substantial content
        has_substantial_content = False
        for result in successful_results:
            if result.get("tool_type") == "vector_search" and len(result.get("results", [])) >= 2:
                has_substantial_content = True
            elif result.get("tool_type") == "perplexity_search" and result.get("result", {}).get("content"):
                has_substantial_content = True
            elif result.get("tool_type") == "atlassian_search" and result.get("result", {}).get("status") == "success":
                has_substantial_content = True
        
        if success_rate >= 0.8 and has_substantial_content:
            return "high"
        elif success_rate >= 0.5 or has_substantial_content:
            return "medium"
        else:
            return "low"

    def _generate_followup_suggestions_new(self, synthesis_context: Dict[str, Any]) -> List[str]:
        """NEW: Generate contextual follow-up suggestions"""
        suggestions = []
        
        # Based on tools used
        results_summary = synthesis_context.get("results_summary", {})
        
        if results_summary.get("vector_search", 0) > 0:
            suggestions.append("Search for related topics in our knowledge base")
        
        if results_summary.get("web_search", 0) > 0:
            suggestions.append("Get the latest updates on this topic")
        
        if results_summary.get("atlassian_search", 0) > 0:
            suggestions.append("Check related project documentation")
        
        # Generic helpful suggestions
        suggestions.extend([
            "Ask for more specific details",
            "Explore implementation steps"
        ])
        
        return suggestions[:4]  # Limit to 4 suggestions

    # Existing methods from original file (preserved)
    async def _construct_hybrid_history(self, conversation_key: str, current_query: str) -> Dict[str, Any]:
        """
        Construct hybrid memory system with rolling long-term summary and precise token-managed live history.
        """
        MAX_LIVE_MESSAGES = 10
        MAX_LIVE_TOKENS = 2000
        PRESERVE_RECENT = 2

        try:
            recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=MAX_LIVE_MESSAGES)
            summary_key = f"{conversation_key}:long_term_summary"
            long_term_summary = await self.memory_service.get_conversation_context(summary_key) or {"summary": "", "message_count": 0}

            if recent_messages:
                messages_to_keep, messages_to_summarize, token_stats = self.token_manager.build_token_managed_history(
                    recent_messages, MAX_LIVE_TOKENS, PRESERVE_RECENT)

                if messages_to_summarize and len(messages_to_summarize) >= 2:
                    raw_messages_to_summarize = [msg.original_message for msg in messages_to_summarize]
                    await self._queue_abstractive_summarization(conversation_key, summary_key, raw_messages_to_summarize, long_term_summary.get("summary", ""))
                    
                    for msg in messages_to_summarize:
                        if long_term_summary["summary"]:
                            long_term_summary["summary"] += f"\n{msg.speaker}: {msg.text[:100]}..."
                        else:
                            long_term_summary["summary"] = f"{msg.speaker}: {msg.text[:100]}..."
                    long_term_summary["message_count"] += len(messages_to_summarize)

                live_history_text = self.token_manager.format_messages_for_context(messages_to_keep)
                precise_token_count = token_stats["total_tokens"]
                old_char_estimate = sum(len(f"{msg.speaker}: {msg.text}") // 4 for msg in messages_to_keep)
                efficiency_stats = self.token_manager.get_token_efficiency_stats(old_char_estimate, precise_token_count)

                return {
                    "summarized_history": long_term_summary["summary"],
                    "summarized_message_count": long_term_summary["message_count"],
                    "live_history": live_history_text,
                    "live_message_count": token_stats["kept_messages"],
                    "precise_tokens": precise_token_count,
                    "estimated_tokens": precise_token_count,
                    "token_efficiency": efficiency_stats,
                    "summarized_message_candidates": len(messages_to_summarize)
                }
            else:
                query_tokens = self.token_manager.count_tokens(f"User: {current_query}")
                return {
                    "summarized_history": long_term_summary["summary"],
                    "summarized_message_count": long_term_summary["message_count"],
                    "live_history": f"User: {current_query}",
                    "live_message_count": 1,
                    "precise_tokens": query_tokens,
                    "estimated_tokens": query_tokens,
                    "token_efficiency": {"accuracy_percentage": 100, "is_more_efficient": True},
                    "summarized_message_candidates": 0
                }

        except Exception as e:
            logger.error(f"Error constructing hybrid history: {e}")
            fallback_tokens = self.token_manager.count_tokens(f"User: {current_query}")
            return {
                "summarized_history": "", "summarized_message_count": 0,
                "live_history": f"User: {current_query}", "live_message_count": 1,
                "precise_tokens": fallback_tokens, "estimated_tokens": fallback_tokens,
                "token_efficiency": {"accuracy_percentage": 100, "fallback": True},
                "summarized_message_candidates": 0
            }

    async def _search_relevant_entities(self, query_text: str, conversation_key: str) -> Dict[str, Any]:
        """Search for entities relevant to the current query"""
        try:
            query_keywords = self._extract_query_keywords(query_text)
            if not query_keywords:
                return {"entities": [], "search_performed": False}

            matching_entities = await self.entity_store.search_entities(
                query_keywords=query_keywords, conversation_key=conversation_key, limit=10)

            formatted_entities = []
            entity_summary = {}
            for entity in matching_entities:
                formatted_entity = {
                    "key": entity.key, "type": entity.type, "value": entity.value,
                    "context": entity.context, "relevance_score": entity.relevance_score,
                    "mentioned_at": entity.mentioned_at
                }
                formatted_entities.append(formatted_entity)
                entity_summary[entity.type] = entity_summary.get(entity.type, 0) + 1

            return {
                "entities": formatted_entities, "entity_summary": entity_summary,
                "search_keywords": query_keywords, "search_performed": True,
                "total_found": len(formatted_entities)
            }
        except Exception as e:
            logger.error(f"Error searching relevant entities: {e}")
            return {"entities": [], "search_performed": False, "error": str(e)}

    def _extract_query_keywords(self, query_text: str) -> List[str]:
        """Extract relevant keywords from query text for entity search"""
        import re
        keywords = []
        text_lower = query_text.lower()
        
        # Extract JIRA patterns, project names, quotes, important words
        jira_matches = re.findall(r'\b([A-Z]+-\d+)\b', query_text, re.IGNORECASE)
        keywords.extend(jira_matches)
        
        project_matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\b', query_text)
        keywords.extend([match for match in project_matches if len(match) > 2])
        
        entity_keywords = ["ticket", "issue", "project", "deadline", "document", "template", "report", "meeting", "user", "owner", "assigned", "status"]
        for keyword in entity_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        quoted_matches = re.findall(r'"([^"]+)"', query_text)
        keywords.extend(quoted_matches)
        
        words = re.findall(r'\b[A-Za-z]{3,}\b', query_text)
        important_words = [word for word in words if word.lower() not in {'the', 'and', 'for', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'can', 'what', 'when', 'where', 'why', 'how', 'who', 'which', 'this', 'that', 'with'}]
        keywords.extend(important_words[:5])
        
        keywords = list(set([k.strip() for k in keywords if k.strip()]))
        return keywords[:10]

    async def _queue_entity_extraction(self, message: ProcessedMessage, bot_response: str):
        """Queue background entity extraction from the conversation exchange"""
        try:
            from workers.entity_extractor import extract_entities_from_conversation
            conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
            extraction_task = extract_entities_from_conversation.delay(
                conversation_key=conversation_key, user_query=message.text, bot_response=bot_response,
                user_name=message.user_name, additional_context={
                    "channel_name": message.channel_name, "is_dm": message.is_dm,
                    "user_title": message.user_title, "user_department": message.user_department,
                    "timestamp": datetime.now().isoformat()
                })
            logger.info(f"Entity extraction task queued: {extraction_task.id} for conversation: {conversation_key}")
        except Exception as e:
            logger.error(f"Failed to queue entity extraction: {e}")

    async def _queue_abstractive_summarization(self, conversation_key: str, summary_key: str, messages_to_archive: List[Dict[str, Any]], existing_summary: str):
        """Queue abstractive summarization task for background processing"""
        try:
            from workers.conversation_summarizer import summarize_conversation_chunk
            logger.info(f"Queuing abstractive summarization for {conversation_key} with {len(messages_to_archive)} messages")
            summarization_result = summarize_conversation_chunk.delay(
                conversation_key=conversation_key, messages_to_summarize=messages_to_archive, existing_summary=existing_summary)
            logger.info(f"Abstractive summarization task queued: {summarization_result.id}")
        except Exception as e:
            logger.error(f"Failed to queue abstractive summarization: {e}")

    # ============================================================================
    # LEGACY METHODS (preserved for safety/compatibility)
    # ============================================================================

    async def _analyze_query_and_plan(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        LEGACY: Original query analysis method - preserved for external compatibility.
        Now uses new 5-step framework internally but returns legacy format.
        """
        try:
            logger.info("LEGACY: Using _analyze_query_and_plan compatibility method")
            
            # Use new method internally
            new_plan = await self._step1_2_analyze_and_plan_new(message)
            
            if new_plan:
                # Convert new format to legacy format for compatibility
                legacy_plan = {
                    "analysis": new_plan.get("analysis", "Query analysis completed"),
                    "intent": new_plan.get("analysis", "")[:100] + "...",  # Truncated analysis as intent
                    "tools_needed": new_plan.get("tools_needed", []),
                    "vector_queries": new_plan.get("vector_queries", []),
                    "perplexity_queries": new_plan.get("perplexity_queries", []),
                    "atlassian_actions": new_plan.get("atlassian_actions", []),
                    "meeting_actions": new_plan.get("meeting_actions", []),
                    "context": {
                        "execution_approach": "5-step reasoning framework",
                        "framework_version": "new",
                        "original_plan_keys": list(new_plan.keys())
                    }
                }
                logger.info("LEGACY: Successfully converted new plan to legacy format")
                return legacy_plan
            else:
                logger.warning("LEGACY: New planning method returned None")
                return None
                
        except Exception as e:
            logger.error(f"LEGACY: Error in _analyze_query_and_plan compatibility method: {e}")
            return None

    async def _execute_plan(self, execution_plan: Dict[str, Any], message: ProcessedMessage) -> Dict[str, Any]:
        """
        LEGACY: Original plan execution method - preserved for external compatibility.
        Now uses new execution methods internally but returns legacy format.
        """
        try:
            logger.info("LEGACY: Using _execute_plan compatibility method")
            
            # Use new execution method internally
            tool_results = await self._execute_planned_tools_new(execution_plan, message)
            
            # Convert new results format to legacy format
            legacy_results = {
                "vector_results": [],
                "perplexity_results": [],
                "atlassian_results": [],
                "meeting_results": [],
                "execution_summary": {
                    "total_tools_executed": len(tool_results),
                    "successful_tools": len([r for r in tool_results if r.get("success", True)]),
                    "failed_tools": len([r for r in tool_results if not r.get("success", True)]),
                    "framework_version": "new"
                }
            }
            
            # Categorize results by tool type for legacy compatibility
            for result in tool_results:
                tool_type = result.get("tool_type", "unknown")
                
                if tool_type == "vector_search":
                    legacy_results["vector_results"].append({
                        "query": result.get("query", ""),
                        "results": result.get("results", []),
                        "success": result.get("success", False),
                        "error": result.get("error", None)
                    })
                    
                elif tool_type == "perplexity_search":
                    legacy_results["perplexity_results"].append({
                        "query": result.get("query", ""),
                        "result": result.get("result", {}),
                        "success": result.get("success", False),
                        "error": result.get("error", None)
                    })
                    
                elif tool_type == "atlassian_search":
                    legacy_results["atlassian_results"].append({
                        "task": result.get("task", ""),
                        "result": result.get("result", {}),
                        "success": result.get("success", False),
                        "error": result.get("error", None)
                    })
                    
                elif tool_type == "outlook_meeting":
                    legacy_results["meeting_results"].append({
                        "action_type": result.get("action_type", "unknown"),
                        "result": result.get("result", {}),
                        "success": result.get("success", False),
                        "error": result.get("error", None)
                    })
            
            logger.info(f"LEGACY: Successfully converted {len(tool_results)} tool results to legacy format")
            return legacy_results
            
        except Exception as e:
            logger.error(f"LEGACY: Error in _execute_plan compatibility method: {e}")
            return {
                "vector_results": [],
                "perplexity_results": [],
                "atlassian_results": [],
                "meeting_results": [],
                "execution_summary": {"error": str(e), "framework_version": "new"}
            }

    async def _build_state_stack(self, message: ProcessedMessage, gathered_info: Dict[str, Any], execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        LEGACY: Original state stack builder - preserved for external compatibility.
        Creates a comprehensive state stack for the client agent using both legacy and new data.
        """
        try:
            logger.info("LEGACY: Using _build_state_stack compatibility method")
            
            # Build conversation context using existing method
            conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
            hybrid_history = await self._construct_hybrid_history(conversation_key, message.text)
            relevant_entities = await self._search_relevant_entities(message.text, conversation_key)
            
            # Build legacy state stack format
            state_stack = {
                "query": message.text,
                "user": {
                    "id": message.user_id,
                    "name": message.user_name,
                    "first_name": message.user_first_name,
                    "display_name": message.user_display_name,
                    "title": message.user_title,
                    "department": message.user_department
                },
                "context": {
                    "channel_id": message.channel_id,
                    "channel_name": message.channel_name,
                    "is_dm": message.is_dm,
                    "thread_ts": message.thread_ts,
                    "message_ts": message.message_ts
                },
                "conversation_memory": hybrid_history,
                "relevant_entities": relevant_entities,
                "orchestrator_analysis": {
                    "execution_plan": execution_plan.get("analysis", ""),
                    "intent_analysis": execution_plan.get("intent", ""),
                    "tools_planned": execution_plan.get("tools_needed", []),
                    "search_results": [],  # Will be populated below
                    "reasoning": execution_plan.get("context", {})
                },
                "orchestrator_findings": {
                    "search_summary": self._create_legacy_search_summary(gathered_info),
                    "key_insights": self._extract_legacy_key_insights(gathered_info),
                    "source_references": self._extract_legacy_source_references(gathered_info),
                    "confidence_assessment": self._assess_legacy_confidence(gathered_info),
                    "execution_metadata": {
                        "tools_executed": gathered_info.get("execution_summary", {}).get("total_tools_executed", 0),
                        "successful_tools": gathered_info.get("execution_summary", {}).get("successful_tools", 0),
                        "framework_version": "legacy_compatibility"
                    }
                }
            }
            
            # Add search results to orchestrator analysis for client agent formatting
            all_results = []
            all_results.extend(gathered_info.get("vector_results", []))
            all_results.extend(gathered_info.get("perplexity_results", []))
            all_results.extend(gathered_info.get("atlassian_results", []))
            
            state_stack["orchestrator_analysis"]["search_results"] = all_results
            
            logger.info("LEGACY: Successfully built comprehensive state stack")
            return state_stack
            
        except Exception as e:
            logger.error(f"LEGACY: Error in _build_state_stack compatibility method: {e}")
            # Return minimal fallback state stack
            return {
                "query": message.text,
                "user": {"first_name": message.user_first_name or "User"},
                "context": {"channel_name": message.channel_name or "unknown"},
                "conversation_memory": {"live_history": f"User: {message.text}"},
                "orchestrator_findings": {"search_summary": "Error building state stack", "error": str(e)}
            }

    def _create_legacy_search_summary(self, gathered_info: Dict[str, Any]) -> str:
        """LEGACY: Create search summary in legacy format"""
        summary_parts = []
        
        vector_results = gathered_info.get("vector_results", [])
        if vector_results:
            total_docs = sum(len(r.get("results", [])) for r in vector_results)
            summary_parts.append(f"Found {total_docs} documents in knowledge base")
        
        perplexity_results = gathered_info.get("perplexity_results", [])
        if perplexity_results:
            successful_searches = len([r for r in perplexity_results if r.get("success")])
            summary_parts.append(f"Completed {successful_searches} web searches")
        
        atlassian_results = gathered_info.get("atlassian_results", [])
        if atlassian_results:
            successful_searches = len([r for r in atlassian_results if r.get("success")])
            summary_parts.append(f"Retrieved {successful_searches} project resources")
        
        return "; ".join(summary_parts) if summary_parts else "No search results available"

    def _extract_legacy_key_insights(self, gathered_info: Dict[str, Any]) -> List[str]:
        """LEGACY: Extract key insights in legacy format"""
        insights = []
        
        # Extract insights from vector results
        for result in gathered_info.get("vector_results", []):
            if result.get("success") and result.get("results"):
                insights.append(f"Knowledge base contains {len(result['results'])} relevant documents")
        
        # Extract insights from web results
        for result in gathered_info.get("perplexity_results", []):
            if result.get("success") and result.get("result", {}).get("content"):
                insights.append("Current web information available on this topic")
        
        # Extract insights from project results
        for result in gathered_info.get("atlassian_results", []):
            if result.get("success"):
                insights.append("Project documentation and resources found")
        
        return insights[:5]  # Limit to 5 insights

    def _extract_legacy_source_references(self, gathered_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """LEGACY: Extract source references in legacy format"""
        sources = []
        
        # Extract from perplexity results (web sources)
        for result in gathered_info.get("perplexity_results", []):
            if result.get("success") and result.get("result", {}).get("citations"):
                for citation in result["result"]["citations"][:3]:
                    if citation.get("url"):
                        sources.append({
                            "title": citation.get("title", "Web Source"),
                            "url": citation["url"],
                            "type": "web"
                        })
        
        # Extract from Atlassian results (project sources)
        for result in gathered_info.get("atlassian_results", []):
            if result.get("success") and result.get("result", {}).get("data"):
                # This would need to be adapted based on actual Atlassian result structure
                sources.append({
                    "title": "Project Resource",
                    "url": "#project-source",
                    "type": "project"
                })
        
        return sources[:5]  # Limit to 5 sources

    def _assess_legacy_confidence(self, gathered_info: Dict[str, Any]) -> str:
        """LEGACY: Assess confidence in legacy format"""
        execution_summary = gathered_info.get("execution_summary", {})
        total_tools = execution_summary.get("total_tools_executed", 0)
        successful_tools = execution_summary.get("successful_tools", 0)
        
        if total_tools == 0:
            return "low"
        
        success_rate = successful_tools / total_tools
        if success_rate >= 0.8:
            return "high"
        elif success_rate >= 0.5:
            return "medium"
        else:
            return "low"
