"""
Client Agent - Generates user-friendly responses with personality.
Refactored to use state stack from orchestrator instead of direct memory access.
"""

import logging
import time
from typing import Dict, Any, Optional, List

from utils.gemini_client import GeminiClient
from services.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class ClientAgent:
    """
    Client-facing agent responsible for generating user-friendly responses.
    Uses complete state stack from orchestrator for personality-driven formatting.
    """
    
    def __init__(self):
        self.gemini_client = GeminiClient()
        
    async def generate_response(self, state_stack: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a persona-based response using complete state stack from orchestrator.
        
        Task: Format the answer to the user query in your personality, taking into account 
        the orchestrator agent findings and message history in the state stack context.
        
        Args:
            state_stack: Complete context state containing:
                - query: Current user query
                - conversation_history: Recent message history
                - conversation_summary: Summary of older conversation (for 10+ messages)
                - orchestrator_insights: Insights from orchestrator analysis
                - gathered_information: Collated answers from orchestrator tools
            
        Returns:
            Dictionary containing response text and suggestions, or None on Gemini API failure
        """
        try:
            start_time = time.time()
            logger.info("Client Agent formatting response from orchestrator state stack...")
            
            # DEBUG: Check state stack structure
            logger.info(f"DEBUG: State stack keys: {list(state_stack.keys())}")
            
            # Get trace manager for LangSmith integration 
            # Use existing trace context from state stack or create new one
            from services.trace_manager import TraceManager
            trace_manager = TraceManager()
            
            # Check if we have an existing conversation trace to join
            existing_trace_id = state_stack.get("trace_id")
            logger.info(f"DEBUG: trace_id from state stack: {existing_trace_id}")
            if existing_trace_id:
                trace_manager.current_trace_id = existing_trace_id
                logger.info(f"DEBUG: Using existing trace ID: {existing_trace_id}")
            else:
                logger.info("DEBUG: No existing trace ID found, creating new context")
            
            logger.info("DEBUG: TraceManager initialized")
            
            # A. Get User Query from state stack
            user_query = state_stack.get("query", "")
            current_query = state_stack.get("current_query", "")
            logger.info(f"DEBUG: query='{user_query}', current_query='{current_query}'")
            
            if not user_query and not current_query:
                logger.error("No user query found in state stack")
                return None
            
            # Use whichever query exists
            final_query = user_query or current_query
            
            logger.info(f"DEBUG: About to create client agent trace for query: {user_query[:50]}...")
            # Start client agent trace span
            client_trace_id = await trace_manager.log_agent_operation(
                agent_name="client_agent",
                operation="response_generation",
                input_data=f"Query: {user_query[:100]}...",
                metadata={"model": "gemini-2.5-flash", "agent_type": "personality_formatting"}
            )
            logger.info(f"DEBUG: Client agent trace ID: {client_trace_id}")
            
            # B. Prepare complete state stack context for Gemini
            user_prompt = self._format_state_stack_context(state_stack)
            
            # C. Get client agent system prompt with main task
            system_prompt = self._get_personality_system_prompt()
            
            logger.info(f"Calling Gemini 2.5 Flash for query: {user_query[:50]}...")
            
            # Track API call for LangSmith
            api_start = time.time()
            
            # Generate response using Gemini Flash - this MUST respond
            response = await self.gemini_client.generate_response(
                system_prompt,
                user_prompt,
                model="gemini-2.5-flash",
                max_tokens=1500,  # Increased from 500 to allow full responses
                temperature=0.7
            )
            
            api_duration = (time.time() - api_start) * 1000
            
            # Log the Gemini API call to LangSmith (full prompts for debugging)
            await trace_manager.log_llm_call(
                model="gemini-2.5-flash",
                prompt=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}",
                response=response[:1000] + "..." if response and len(response) > 1000 else (response or ""),
                duration=api_duration / 1000  # Convert to seconds
            )
            
            # If Gemini doesn't respond, that's an ERROR, not a fallback case
            if not response:
                logger.error("CRITICAL ERROR: Gemini 2.5 Flash returned no response - API call formatting issue")
                return None
            
            # Response received successfully - validate and format
            logger.info("Successfully received response from Gemini 2.5 Flash")
            
            # CRITICAL FIX: Ensure response is natural language, not raw JSON
            response_text = response.strip()
            
            # Check if response contains raw JSON fragments (like "limit": 10)
            if self._contains_raw_json(response_text):
                logger.error(f"CRITICAL: Gemini returned raw JSON instead of natural language: {response_text[:200]}...")
                # Force a natural language fallback
                response_text = f"I found relevant information about your query. Let me provide you with the details from our documentation and search results."
                logger.info("Applied natural language fallback to replace raw JSON response")
            
            # Generate suggestions based on the context
            suggestions = await self._generate_suggestions(state_stack)
            
            final_result = {
                "text": response_text,
                "suggestions": suggestions
            }
            
            # Complete client agent trace span with successful result
            total_time = time.time() - start_time
            if 'client_trace_id' in locals():
                await trace_manager.complete_agent_operation(
                    trace_id=client_trace_id,
                    output_data=f"Response: {response[:200]}..." if len(response) > 200 else response,
                    success=True,
                    duration=total_time,
                    metadata={"suggestions_count": len(suggestions)}
                )
            
            return final_result
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR in Client Agent: {e}")
            # Complete client agent trace span with error
            if 'client_trace_id' in locals() and 'trace_manager' in locals():
                try:
                    await trace_manager.complete_agent_operation(
                        trace_id=client_trace_id,
                        output_data=f"Error: {str(e)}",
                        success=False,
                        duration=time.time() - start_time if 'start_time' in locals() else 0,
                        metadata={"error_type": type(e).__name__}
                    )
                except:
                    pass  # Don't let trace logging errors break the system
            return None
    
    def _get_personality_system_prompt(self) -> str:
        """
        Get the personality-based system prompt for the client agent.
        Contains the main task: format the answer to the user query based on personality 
        and state stack from orchestrator.
        
        Returns:
            System prompt with personality and main task instructions
        """
        # Load prompt from centralized prompt loader
        from utils.prompt_loader import get_client_agent_prompt
        return get_client_agent_prompt()
    
    def _format_state_stack_context(self, state_stack: Dict[str, Any]) -> str:
        """
        Format the state stack context for Gemini 2.5 Flash call.
        
        Structure as specified:
        A. User Query
        B. State stack from orchestrator containing:
           - Conversation Summary (for 10+ messages)
           - Raw History (recent messages) 
           - Collated Answers from orchestrator
           - Insights orchestrator thinks are relevant to client_agent
        
        Args:
            state_stack: Complete context state from orchestrator
            
        Returns:
            Formatted user prompt for Gemini 2.5 Flash
        """
        prompt_parts = []
        
        # A. User Query
        user_query = state_stack.get("query", "")
        prompt_parts.append(f"USER QUERY: {user_query}")
        prompt_parts.append("")
        
        # B. State Stack from Orchestrator
        prompt_parts.append("STATE STACK FROM ORCHESTRATOR:")
        prompt_parts.append("="*50)
        
        # B1. Conversation Summary (for 10+ message conversations)
        conversation_summary = state_stack.get("conversation_summary", "")
        if conversation_summary and conversation_summary.strip():
            prompt_parts.append("CONVERSATION SUMMARY:")
            prompt_parts.append(conversation_summary.strip())
            prompt_parts.append("")
        
        # B2. Raw History (recent messages)
        conversation_history_data = state_stack.get("conversation_history", {})
        recent_exchanges = conversation_history_data.get("recent_exchanges", []) if isinstance(conversation_history_data, dict) else []
        if recent_exchanges:
            prompt_parts.append("RECENT MESSAGE HISTORY:")
            for message in recent_exchanges:
                role = message.get("role", "unknown")
                text = message.get("text", "")
                timestamp = message.get("timestamp", "")
                if role and text:
                    prompt_parts.append(f"  {role.upper()}: {text}")
            prompt_parts.append("")
        
        # B3. Collated Answers from Orchestrator (Search Results & Meeting Actions)
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        search_results = orchestrator_analysis.get("search_results", [])
        web_results = orchestrator_analysis.get("web_results", [])
        meeting_results = orchestrator_analysis.get("meeting_results", [])
        atlassian_results = orchestrator_analysis.get("atlassian_results", [])
        
        if search_results or web_results or meeting_results or atlassian_results:
            prompt_parts.append("COLLATED ANSWERS FROM ORCHESTRATOR:")
            
            # Vector Search Results
            if search_results:
                prompt_parts.append("Vector Search Results:")
                for i, result in enumerate(search_results[:3], 1):  # Top 3 results
                    content = result.get("content", "")
                    source = result.get("source", "")
                    score = result.get("score", 0.0)
                    if content:
                        prompt_parts.append(f"  {i}. {content[:300]}...")
                        if source:
                            prompt_parts.append(f"     Source: {source}")
                        if score:
                            prompt_parts.append(f"     Relevance: {score:.2f}")
                prompt_parts.append("")
            
            # Web Search Results
            if web_results:
                prompt_parts.append("Real-Time Web Search Results:")
                for i, result in enumerate(web_results[:2], 1):  # Top 2 web results
                    content = result.get("content", "")
                    citations = result.get("citations", [])
                    query = result.get("query", "")
                    search_time = result.get("search_time", 0)
                    if content:
                        prompt_parts.append(f"  {i}. Query: {query}")
                        prompt_parts.append(f"     Content: {content[:400]}...")
                        if citations:
                            prompt_parts.append(f"     Sources: {', '.join(citations[:3])}")
                        prompt_parts.append(f"     Search Time: {search_time:.2f}s")
                prompt_parts.append("")
            
            # Meeting Results
            if meeting_results:
                prompt_parts.append("Outlook Meeting Actions:")
                for i, result in enumerate(meeting_results, 1):
                    action_type = result.get("action_type", "unknown")
                    success = result.get("success", False)
                    
                    if success:
                        meeting_data = result.get("result", {})
                        prompt_parts.append(f"  {i}. {action_type.replace('_', ' ').title()}: SUCCESS")
                        
                        if action_type == "check_availability":
                            availability = meeting_data.get("availability_check", {})
                            time_range = availability.get("time_range", "")
                            users = availability.get("users", {})
                            prompt_parts.append(f"     Time Range: {time_range}")
                            prompt_parts.append(f"     Checked: {len(users)} users")
                            
                        elif action_type == "schedule_meeting":
                            meeting_info = meeting_data.get("meeting_scheduled", {})
                            subject = meeting_info.get("subject", "")
                            start_time = meeting_info.get("start", "")
                            join_url = meeting_info.get("online_meeting", {}).get("join_url", "") if meeting_info.get("online_meeting") else ""
                            prompt_parts.append(f"     Subject: {subject}")
                            prompt_parts.append(f"     Start: {start_time}")
                            if join_url:
                                prompt_parts.append(f"     Join URL: {join_url}")
                        
                        elif action_type == "find_meeting_times":
                            suggestions = meeting_data.get("meeting_time_suggestions", {})
                            suggestions_list = suggestions.get("suggestions", [])
                            duration = suggestions.get("search_parameters", {}).get("duration_minutes", "")
                            prompt_parts.append(f"     Found: {len(suggestions_list)} time suggestions")
                            if duration:
                                prompt_parts.append(f"     Duration: {duration} minutes")
                                
                        elif action_type == "get_calendar":
                            calendar_data = meeting_data.get("calendar_events", {})
                            events = calendar_data.get("events", [])
                            date_range = calendar_data.get("date_range", "")
                            prompt_parts.append(f"     Events: {len(events)} found")
                            prompt_parts.append(f"     Range: {date_range}")
                    else:
                        error_msg = result.get("error", "Unknown error")
                        prompt_parts.append(f"  {i}. {action_type.replace('_', ' ').title()}: FAILED")
                        prompt_parts.append(f"     Error: {error_msg}")
                
                prompt_parts.append("")
            
            # Atlassian Results (MCP format)
            if atlassian_results:
                prompt_parts.append("Atlassian Actions:")
                for i, result in enumerate(atlassian_results, 1):
                    # Handle both old format (action_type) and new MCP format (mcp_tool)
                    action_type = result.get("action_type") or result.get("mcp_tool", "unknown")
                    success = result.get("success", False)
                    
                    if success:
                        # MCP results have nested structure: result.result.result (array of pages/issues)
                        result_wrapper = result.get("result", {})
                        if isinstance(result_wrapper, dict) and result_wrapper.get("success"):
                            atlassian_data = result_wrapper.get("result", [])
                        else:
                            atlassian_data = result_wrapper if isinstance(result_wrapper, list) else []
                        prompt_parts.append(f"  {i}. {action_type.replace('_', ' ').title()}: SUCCESS")
                        
                        # Handle MCP result format for different tools
                        if action_type in ["jira_search", "search_jira_issues"]:
                            # MCP jira_search returns array of issues directly
                            if isinstance(atlassian_data, list):
                                issues = atlassian_data
                                prompt_parts.append(f"     Found: {len(issues)} issues")
                                for issue in issues[:3]:  # Show top 3 issues
                                    key = issue.get("key", "")
                                    summary = issue.get("summary", "")[:60]
                                    status = issue.get("status", {}).get("name", "") if isinstance(issue.get("status"), dict) else issue.get("status", "")
                                    # Build Jira URL from base URL and key
                                    if key:
                                        url = f"https://uipath.atlassian.net/browse/{key}"
                                        prompt_parts.append(f"     - <{url}|{key}>: {summary}... ({status})")
                                    else:
                                        prompt_parts.append(f"     - {summary}... ({status})")
                        
                        elif action_type in ["jira_get", "get_jira_issue"]:
                            # MCP jira_get returns single issue object
                            if isinstance(atlassian_data, dict):
                                key = atlassian_data.get("key", "")
                                summary = atlassian_data.get("summary", "")
                                status = atlassian_data.get("status", {}).get("name", "") if isinstance(atlassian_data.get("status"), dict) else atlassian_data.get("status", "")
                                assignee = atlassian_data.get("assignee", {}).get("displayName", "Unassigned") if isinstance(atlassian_data.get("assignee"), dict) else atlassian_data.get("assignee", "Unassigned")
                                if key:
                                    url = f"https://uipath.atlassian.net/browse/{key}"
                                    prompt_parts.append(f"     Issue: <{url}|{key}>")
                                else:
                                    prompt_parts.append(f"     Issue: {summary}")
                                prompt_parts.append(f"     Summary: {summary}")
                                prompt_parts.append(f"     Status: {status}")
                                prompt_parts.append(f"     Assignee: {assignee}")
                        
                        elif action_type in ["confluence_search", "search_confluence_pages"]:
                            # MCP confluence_search returns array of pages directly
                            if isinstance(atlassian_data, list):
                                pages = atlassian_data
                                prompt_parts.append(f"     Found: {len(pages)} pages")
                                for page in pages[:3]:  # Show top 3 pages
                                    title = page.get("title", "")[:60]
                                    space_info = page.get("space", {})
                                    space_name = space_info.get("name", "") if isinstance(space_info, dict) else ""
                                    url = page.get("url", "")
                                    if url:
                                        prompt_parts.append(f"     - <{url}|{title}>... (Space: {space_name})")
                                    else:
                                        prompt_parts.append(f"     - {title}... (Space: {space_name})")
                        
                        elif action_type in ["confluence_get", "get_confluence_page"]:
                            # MCP confluence_get returns single page object
                            if isinstance(atlassian_data, dict):
                                title = atlassian_data.get("title", "")
                                space_info = atlassian_data.get("space", {})
                                space_name = space_info.get("name", "") if isinstance(space_info, dict) else ""
                                url = atlassian_data.get("url", "")
                                if url:
                                    prompt_parts.append(f"     Page: <{url}|{title}>")
                                else:
                                    prompt_parts.append(f"     Page: {title}")
                                prompt_parts.append(f"     Space: {space_name}")
                        
                        elif action_type in ["jira_create", "create_jira_issue"]:
                            # MCP jira_create returns created issue object
                            if isinstance(atlassian_data, dict):
                                key = atlassian_data.get("key", "")
                                summary = atlassian_data.get("summary", "")
                                project = atlassian_data.get("project", {}).get("name", "") if isinstance(atlassian_data.get("project"), dict) else ""
                                if key:
                                    url = f"https://uipath.atlassian.net/browse/{key}"
                                    prompt_parts.append(f"     Created: <{url}|{key}>")
                                else:
                                    prompt_parts.append(f"     Created: {summary}")
                                prompt_parts.append(f"     Summary: {summary}")
                                prompt_parts.append(f"     Project: {project}")
                    else:
                        error_msg = result.get("error", "Unknown error")
                        prompt_parts.append(f"  {i}. {action_type.replace('_', ' ').title()}: FAILED")
                        prompt_parts.append(f"     Error: {error_msg}")
                
                prompt_parts.append("")
        
        # B4. Orchestrator Analysis & Insights
        if orchestrator_analysis:
            prompt_parts.append("ORCHESTRATOR ANALYSIS & INSIGHTS:")
            
            # Include the orchestrator's intent analysis
            intent_analysis = orchestrator_analysis.get("intent", "")
            if intent_analysis and intent_analysis.strip():
                prompt_parts.append(f"Intent Analysis: {intent_analysis.strip()}")
            
            # Include tools used information
            tools_used = orchestrator_analysis.get("tools_used", [])
            if tools_used:
                prompt_parts.append(f"Tools Used: {', '.join(tools_used)}")
            else:
                prompt_parts.append("Tools Used: none")
            
            # Include results summary if available
            results_summary = []
            if search_results:
                results_summary.append(f"{len(search_results)} knowledge base items")
            if web_results:
                results_summary.append(f"{len(web_results)} real-time web results")
            if meeting_results:
                results_summary.append(f"{len(meeting_results)} meeting actions")
            if atlassian_results:
                results_summary.append(f"{len(atlassian_results)} Atlassian actions")
            
            if results_summary:
                prompt_parts.append(f"Results Found: {', '.join(results_summary)}")
            else:
                prompt_parts.append("Results Found: none")
            
            prompt_parts.append("")
        else:
            prompt_parts.append("ORCHESTRATOR ANALYSIS & INSIGHTS:")
            prompt_parts.append("No orchestrator analysis available")
            prompt_parts.append("")
        
        # Final instruction for the client agent
        prompt_parts.append("TASK:")
        prompt_parts.append("Format the answer to the user query in your personality, taking into account the orchestrator findings and message history provided above.")
        
        formatted_prompt = "\n".join(prompt_parts)
        
        # Log the complete formatted prompt for trace visibility
        logger.info(f"CLIENT AGENT PROMPT PREVIEW:\n{formatted_prompt[:500]}...")
        
        return formatted_prompt
    
    def _post_process_response(self, response: str, state_stack: Dict[str, Any]) -> str:
        """
        Post-process the generated response for better formatting.
        
        Args:
            response: Raw response from Gemini
            state_stack: State stack for context
            
        Returns:
            Formatted response
        """
        try:
            # Basic cleanup
            clean_response = response.strip()
            
            # Ensure response doesn't exceed reasonable length for Slack
            if len(clean_response) > 4000:  # Increased limit to allow fuller responses
                clean_response = clean_response[:3950] + "...\n\n*[Response truncated for readability]*"
            
            return clean_response
            
        except Exception as e:
            logger.error(f"Error post-processing response: {e}")
            return response
    
    async def _generate_suggestions(self, state_stack: Dict[str, Any]) -> List[str]:
        """
        Generate contextual suggestions based on state stack.
        
        Args:
            state_stack: Complete state stack
            
        Returns:
            List of suggestion strings
        """
        try:
            user_query = state_stack.get("query", "")
            
            # Simple contextual suggestions based on query content
            suggestions = []
            
            query_lower = user_query.lower()
            if "autopilot" in query_lower:
                suggestions.extend([
                    "Tell me about Autopilot features",
                    "How do I get started with Autopilot?",
                    "Show me Autopilot examples"
                ])
            elif "construct" in query_lower:
                suggestions.extend([
                    "Explain Construct automation",
                    "How does Construct work?",
                    "Construct best practices"
                ])
            elif "help" in query_lower or "how" in query_lower:
                suggestions.extend([
                    "What can you help me with?",
                    "Show me available features",
                    "Explain key concepts"
                ])
            else:
                # Default suggestions
                suggestions.extend([
                    "Tell me about Autopilot",
                    "How can I automate tasks?",
                    "What's new in the platform?"
                ])
            
            # Return first 3 suggestions
            return suggestions[:3]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            # Return default suggestions on error
            return [
                "Tell me about Autopilot",
                "How can I automate tasks?",
                "What features are available?"
            ]