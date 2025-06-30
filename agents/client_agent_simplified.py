"""
Simplified Client Agent - Focuses purely on creative presentation and Slack formatting.
Orchestrator does all data processing; client agent applies personality and formats for Slack.
"""

import logging
import time
from typing import Dict, Any, Optional, List

from utils.gemini_client import GeminiClient
from services.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class ClientAgent:
    """
    Simplified client-facing agent responsible for creative presentation.
    Takes pre-formatted summaries from orchestrator and applies personality + Slack formatting.
    """
    
    def __init__(self):
        self.gemini_client = GeminiClient()
        
    async def generate_response(self, state_stack: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a persona-based response using clean summaries from orchestrator.
        
        Args:
            state_stack: Simplified context state containing:
                - query: Current user query
                - user: User profile information
                - context: Channel/DM context
                - conversation_summary: Brief conversation context
                - orchestrator_findings: Pre-formatted summaries from orchestrator
            
        Returns:
            Dictionary containing response text and suggestions, or None on failure
        """
        try:
            start_time = time.time()
            logger.info("Client Agent generating creative response from orchestrator summaries...")
            
            # Get trace manager for LangSmith integration 
            trace_id = state_stack.get("trace_id")
            if trace_id:
                client_trace_id = await trace_manager.start_agent_operation(
                    parent_trace_id=trace_id,
                    agent_name="client_agent",
                    operation="response_generation",
                    input_data={"query": state_stack.get("query", "")[:100]}
                )
            else:
                client_trace_id = None
            
            # Generate creative response using clean orchestrator summaries
            response_text = await self._generate_creative_response(state_stack)
            
            if not response_text or self._contains_raw_json(response_text):
                logger.warning("Client agent generated empty or JSON-contaminated response")
                response_text = "I'm having trouble crafting a response right now. Could you try asking again?"
            
            # Post-process for better Slack formatting
            formatted_response = self._post_process_response(response_text, state_stack)
            
            # Generate contextual suggestions
            suggestions = await self._generate_suggestions(state_stack)
            
            total_time = time.time() - start_time
            logger.info(f"Client Agent generated response in {total_time:.2f}s")
            
            final_result = {
                "text": formatted_response,
                "suggestions": suggestions
            }
            
            # Complete client agent trace
            if client_trace_id:
                await trace_manager.complete_agent_operation(
                    trace_id=client_trace_id,
                    output_data=formatted_response[:200],
                    success=True,
                    duration=total_time,
                    metadata={"suggestions_count": len(suggestions)}
                )
            
            return final_result
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR in Client Agent: {e}")
            # Complete client agent trace with error
            if 'client_trace_id' in locals() and client_trace_id:
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
    
    async def _generate_creative_response(self, state_stack: Dict[str, Any]) -> str:
        """
        Generate creative response using clean orchestrator summaries.
        Focus on personality, tone, and Slack formatting.
        """
        system_prompt = self._get_personality_system_prompt()
        user_prompt = self._format_clean_context(state_stack)
        
        # Use Gemini Flash for fast creative response generation
        response = await self.gemini_client.generate_response(
            system_prompt,
            user_prompt,
            model=self.gemini_client.flash_model,  # Client uses Flash for speed
            max_tokens=1500,
            temperature=0.8  # Higher temperature for more creative responses
        )
        
        return response.get("text", "") if response else ""
    
    def _get_personality_system_prompt(self) -> str:
        """
        Get the personality-based system prompt for the client agent.
        """
        from utils.prompt_loader import get_client_agent_prompt
        return get_client_agent_prompt()
    
    def _format_clean_context(self, state_stack: Dict[str, Any]) -> str:
        """
        Format clean context from orchestrator summaries for creative response generation.
        Much simpler than the old 250+ line function - orchestrator did the heavy lifting.
        """
        context_parts = []
        
        # User query
        query = state_stack.get("query", "")
        context_parts.append(f"USER QUERY: {query}")
        context_parts.append("")
        
        # User information for personalization
        user = state_stack.get("user", {})
        first_name = user.get("first_name", "")
        title = user.get("title", "")
        if first_name:
            context_parts.append(f"USER: {first_name}" + (f" ({title})" if title else ""))
            context_parts.append("")
        
        # Channel context
        context = state_stack.get("context", {})
        is_dm = context.get("is_dm", False)
        channel = context.get("channel", "")
        if is_dm:
            context_parts.append("CONTEXT: Direct message conversation")
        elif channel:
            context_parts.append(f"CONTEXT: Channel #{channel}")
        context_parts.append("")
        
        # Conversation summary (if available)
        conversation_summary = state_stack.get("conversation_summary", "")
        if conversation_summary:
            context_parts.append("CONVERSATION CONTEXT:")
            context_parts.append(conversation_summary)
            context_parts.append("")
        
        # Orchestrator findings (pre-formatted summaries)
        findings = state_stack.get("orchestrator_findings", {})
        
        analysis = findings.get("analysis", "")
        if analysis:
            context_parts.append("QUERY ANALYSIS:")
            context_parts.append(analysis)
            context_parts.append("")
        
        # Pre-formatted search summaries from orchestrator
        search_summary = findings.get("search_summary", "")
        if search_summary:
            context_parts.append("KNOWLEDGE BASE FINDINGS:")
            context_parts.append(search_summary)
            context_parts.append("")
        
        web_summary = findings.get("web_summary", "")
        if web_summary:
            context_parts.append("WEB RESEARCH FINDINGS:")
            context_parts.append(web_summary)
            context_parts.append("")
        
        atlassian_summary = findings.get("atlassian_summary", "")
        if atlassian_summary:
            context_parts.append("PROJECT INFORMATION:")
            context_parts.append(atlassian_summary)
            context_parts.append("")
        
        meeting_summary = findings.get("meeting_summary", "")
        if meeting_summary:
            context_parts.append("MEETING ACTIONS:")
            context_parts.append(meeting_summary)
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _post_process_response(self, response: str, state_stack: Dict[str, Any]) -> str:
        """
        Post-process the generated response for better Slack formatting.
        """
        # Clean up any potential formatting issues
        response = response.strip()
        
        # Ensure proper Slack formatting (use *text* for bold, _text_ for italic)
        # Gemini sometimes uses **text** which doesn't work in Slack
        response = response.replace("**", "*")
        
        # Remove any residual JSON fragments
        if "{" in response and "}" in response:
            lines = response.split("\n")
            clean_lines = []
            for line in lines:
                if not (line.strip().startswith("{") or line.strip().startswith("}")):
                    clean_lines.append(line)
            response = "\n".join(clean_lines)
        
        return response
    
    async def _generate_suggestions(self, state_stack: Dict[str, Any]) -> List[str]:
        """
        Generate contextual suggestions based on orchestrator findings.
        """
        try:
            findings = state_stack.get("orchestrator_findings", {})
            tools_used = findings.get("tools_used", [])
            
            suggestions = []
            
            # Smart suggestions based on what tools were used
            if "atlassian_search" in tools_used:
                suggestions.extend([
                    "Search for related Jira issues",
                    "Find more Confluence documentation",
                    "Create a new Jira ticket"
                ])
            
            if "vector_search" in tools_used:
                suggestions.extend([
                    "Ask about related topics",
                    "Get more technical details",
                    "Search with different keywords"
                ])
            
            if "perplexity_search" in tools_used:
                suggestions.extend([
                    "Get latest industry updates",
                    "Search for recent news",
                    "Find current best practices"
                ])
            
            # Limit to 3-4 suggestions
            return suggestions[:4] if suggestions else [
                "Tell me more about this topic",
                "How does this relate to our project?",
                "What are the next steps?"
            ]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return ["Ask me anything else!", "How can I help you further?"]
    
    def _contains_raw_json(self, text: str) -> bool:
        """
        Check if response contains raw JSON fragments instead of natural language.
        """
        if not text:
            return True
        
        # Count JSON-like patterns
        json_indicators = ["{", "}", '":', "[]", "null", "true", "false"]
        json_count = sum(1 for indicator in json_indicators if indicator in text)
        
        # If more than 30% of the content looks like JSON, it's probably contaminated
        return json_count > len(text.split()) * 0.3