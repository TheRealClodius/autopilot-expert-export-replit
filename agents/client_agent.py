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
            
            # A. Get User Query from state stack
            user_query = state_stack.get("query", "")
            if not user_query:
                logger.error("No user query found in state stack")
                return None
            
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
            
            # Log the Gemini API call to LangSmith
            await trace_manager.log_api_call(
                api_name="gemini",
                model_name="gemini-2.5-flash",
                prompt=f"{system_prompt[:200]}...\n\n{user_prompt[:300]}...",
                response=response[:500] + "..." if response and len(response) > 500 else (response or ""),
                duration_ms=api_duration,
                error=None if response else "No response received"
            )
            
            # If Gemini doesn't respond, that's an ERROR, not a fallback case
            if not response:
                logger.error("CRITICAL ERROR: Gemini 2.5 Flash returned no response - API call formatting issue")
                return None
            
            # Response received successfully - format and return
            logger.info("Successfully received response from Gemini 2.5 Flash")
            
            # Generate suggestions based on the context
            suggestions = await self._generate_suggestions(state_stack)
            
            final_result = {
                "text": response.strip(),
                "suggestions": suggestions
            }
            
            # Log the client response generation to LangSmith
            total_duration = (time.time() - start_time) * 1000
            await trace_manager.log_client_response(
                final_response=response.strip(),
                duration_ms=total_duration
            )
            
            return final_result
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR in Client Agent: {e}")
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
        conversation_history = state_stack.get("conversation_history", [])
        if conversation_history:
            prompt_parts.append("RECENT MESSAGE HISTORY:")
            for message in conversation_history:
                role = message.get("role", "unknown")
                text = message.get("text", "")
                timestamp = message.get("timestamp", "")
                if role and text:
                    prompt_parts.append(f"  {role.upper()}: {text}")
            prompt_parts.append("")
        
        # B3. Collated Answers from Orchestrator
        gathered_info = state_stack.get("gathered_information", {})
        if gathered_info:
            prompt_parts.append("COLLATED ANSWERS FROM ORCHESTRATOR:")
            
            # Vector search results
            vector_results = gathered_info.get("vector_search_results", [])
            if vector_results:
                prompt_parts.append("Vector Search Results:")
                for i, result in enumerate(vector_results[:3], 1):  # Top 3 results
                    content = result.get("content", "")
                    if content:
                        prompt_parts.append(f"  {i}. {content[:200]}...")
            
            # Other relevant context
            relevant_context = gathered_info.get("relevant_context", "")
            if relevant_context:
                prompt_parts.append(f"Additional Context: {relevant_context}")
            
            prompt_parts.append("")
        
        # B4. Orchestrator Insights
        orchestrator_insights = state_stack.get("orchestrator_insights", "")
        if orchestrator_insights and orchestrator_insights.strip():
            prompt_parts.append("ORCHESTRATOR INSIGHTS:")
            prompt_parts.append(orchestrator_insights.strip())
            prompt_parts.append("")
        
        # Final instruction for the client agent
        prompt_parts.append("TASK:")
        prompt_parts.append("Format the answer to the user query in your personality, taking into account the orchestrator findings and message history provided above.")
        
        return "\n".join(prompt_parts)
    
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