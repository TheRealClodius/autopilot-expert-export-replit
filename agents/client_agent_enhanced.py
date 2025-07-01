"""
Enhanced Client Agent - Leverages 5-step reasoning orchestrator's clean output format.
Sophisticated personality expression with contextual intelligence and elegant source integration.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List

from utils.gemini_client import GeminiClient
from services.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class ClientAgent:
    """
    Enhanced client-facing agent that fully leverages the 5-step reasoning orchestrator.
    Takes orchestrator's clean output format (synthesized_response, key_findings, source_links)
    and applies sophisticated personality, contextual intelligence, and elegant presentation.
    """
    
    def __init__(self):
        self.gemini_client = GeminiClient()
        
    async def generate_response(self, orchestrator_output: Dict[str, Any], user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate sophisticated response using orchestrator's clean output format.
        
        Args:
            orchestrator_output: Clean output from 5-step reasoning orchestrator:
                - synthesized_response: Comprehensive answer
                - key_findings: Important points list
                - source_links: Formatted source references
                - confidence_level: high|medium|low
                - suggested_followups: Optional follow-up questions
                - requires_human_input: Boolean flag
            user_context: User and conversation context:
                - query: Original user query
                - user: User profile (first_name, title, department)
                - channel_context: DM vs channel, channel name
                - conversation_history: Recent conversation context
            
        Returns:
            Dictionary containing enhanced response text and suggestions, or None on failure
        """
        try:
            start_time = time.time()
            logger.info("Enhanced Client Agent generating sophisticated response from orchestrator output...")
            
            # Validate orchestrator output format
            if not self._validate_orchestrator_output(orchestrator_output):
                logger.warning("Invalid orchestrator output format, falling back to legacy processing")
                return await self._fallback_to_legacy_processing(orchestrator_output, user_context)
            
            # Get trace manager for LangSmith integration 
            trace_id = user_context.get("trace_id")
            client_trace_id = None
            if trace_id:
                client_trace_id = await trace_manager.log_agent_operation(
                    agent_name="enhanced_client_agent",
                    operation="sophisticated_response_generation",
                    input_data=user_context.get("query", "")[:100]
                )
            
            # Generate sophisticated response with contextual intelligence
            enhanced_response = await self._generate_sophisticated_response(orchestrator_output, user_context)
            
            if not enhanced_response or self._contains_raw_json(enhanced_response):
                logger.warning("Enhanced client agent generated empty or JSON-contaminated response")
                enhanced_response = self._create_fallback_response(user_context)
            
            # Apply elegant source integration
            response_with_sources = self._integrate_sources_elegantly(enhanced_response, orchestrator_output)
            
            # Generate contextual and intelligent suggestions
            suggestions = await self._generate_intelligent_suggestions(orchestrator_output, user_context)
            
            total_time = time.time() - start_time
            logger.info(f"Enhanced Client Agent generated sophisticated response in {total_time:.2f}s")
            
            final_result = {
                "text": response_with_sources,
                "suggestions": suggestions,
                "confidence_level": orchestrator_output.get("confidence_level", "medium"),
                "requires_followup": orchestrator_output.get("requires_human_input", False)
            }
            
            # Complete client agent trace
            if client_trace_id:
                await trace_manager.complete_agent_operation(
                    trace_id=client_trace_id,
                    output_data=response_with_sources[:200],
                    success=True,
                    duration=total_time,
                    metadata={
                        "suggestions_count": len(suggestions),
                        "confidence_level": final_result["confidence_level"],
                        "sources_integrated": len(orchestrator_output.get("source_links", []))
                    }
                )
            
            return final_result
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR in Enhanced Client Agent: {e}")
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
                    pass
            return None
    
    def _validate_orchestrator_output(self, orchestrator_output: Dict[str, Any]) -> bool:
        """
        Validate that orchestrator output has the expected clean format from 5-step reasoning.
        """
        if not isinstance(orchestrator_output, dict):
            return False
        
        # Check for new format indicators
        has_synthesized_response = "synthesized_response" in orchestrator_output
        has_key_findings = "key_findings" in orchestrator_output
        has_confidence_level = "confidence_level" in orchestrator_output
        
        # If we have any of the new format fields, consider it valid
        return has_synthesized_response or has_key_findings or has_confidence_level
    
    async def _generate_sophisticated_response(self, orchestrator_output: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """
        Generate sophisticated response with contextual intelligence and dynamic personality.
        """
        # Build sophisticated context for personality-driven response
        context_prompt = self._build_sophisticated_context(orchestrator_output, user_context)
        
        # Get dynamic personality prompt based on context
        personality_prompt = self._get_dynamic_personality_prompt(user_context, orchestrator_output)
        
        # Use Gemini Flash for creative response generation with higher temperature
        response = await self.gemini_client.generate_response(
            personality_prompt,
            context_prompt,
            model=self.gemini_client.flash_model,
            max_tokens=1500,
            temperature=0.8  # High creativity for personality expression
        )
        
        return response if response else ""
    
    def _build_sophisticated_context(self, orchestrator_output: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """
        Build sophisticated context that leverages orchestrator's clean output format.
        """
        context_parts = []
        
        # User query and context
        query = user_context.get("query", "")
        context_parts.append(f"USER QUERY: {query}")
        
        # User profile for personalization
        user = user_context.get("user", {})
        user_info = []
        if user.get("first_name"):
            user_info.append(f"Name: {user['first_name']}")
        if user.get("title"):
            user_info.append(f"Title: {user['title']}")
        if user.get("department"):
            user_info.append(f"Department: {user['department']}")
        
        if user_info:
            context_parts.append(f"USER PROFILE: {', '.join(user_info)}")
        
        # Channel context for tone adaptation
        channel_context = user_context.get("channel_context", {})
        is_dm = channel_context.get("is_dm", False)
        channel_name = channel_context.get("channel_name", "")
        
        if is_dm:
            context_parts.append("CONTEXT: Private direct message conversation")
        elif channel_name:
            context_parts.append(f"CONTEXT: Public channel #{channel_name}")
        
        # Orchestrator's synthesized response (the core answer)
        synthesized_response = orchestrator_output.get("synthesized_response", "")
        if synthesized_response:
            context_parts.append(f"ORCHESTRATOR FINDINGS: {synthesized_response}")
        
        # Key findings for emphasis
        key_findings = orchestrator_output.get("key_findings", [])
        if key_findings:
            context_parts.append("KEY POINTS TO EMPHASIZE:")
            for i, finding in enumerate(key_findings[:5], 1):
                context_parts.append(f"{i}. {finding}")
        
        # Confidence level for tone adjustment
        confidence_level = orchestrator_output.get("confidence_level", "medium")
        context_parts.append(f"CONFIDENCE LEVEL: {confidence_level}")
        
        # Conversation history if available
        conversation_history = user_context.get("conversation_history", "")
        if conversation_history:
            context_parts.append(f"RECENT CONVERSATION: {conversation_history}")
        
        return "\n\n".join(context_parts)
    
    def _get_dynamic_personality_prompt(self, user_context: Dict[str, Any], orchestrator_output: Dict[str, Any]) -> str:
        """
        Generate dynamic personality prompt based on context and confidence level.
        """
        # Base personality from prompts.yaml
        base_personality = self._get_base_personality_prompt()
        
        # Context-specific adaptations
        adaptations = []
        
        # Confidence-based tone adaptation
        confidence_level = orchestrator_output.get("confidence_level", "medium")
        if confidence_level == "high":
            adaptations.append("You can be confident and definitive in your response. Present information with authority.")
        elif confidence_level == "low":
            adaptations.append("Be more cautious and speculative. Use phrases like 'it seems like', 'based on what I found', 'this suggests'.")
        else:
            adaptations.append("Present information with balanced confidence, acknowledging any limitations.")
        
        # Channel context adaptation
        channel_context = user_context.get("channel_context", {})
        if channel_context.get("is_dm", False):
            adaptations.append("This is a private conversation. You can be more personal and direct.")
        else:
            adaptations.append("This is a public channel. Be helpful to the broader audience while addressing the specific user.")
        
        # User role adaptation
        user = user_context.get("user", {})
        title = user.get("title", "").lower()
        if "engineer" in title or "developer" in title:
            adaptations.append("This user has technical background. You can use more technical terms and dive deeper into implementation details.")
        elif "manager" in title or "director" in title:
            adaptations.append("This user is in management. Focus on strategic implications, business value, and high-level overviews.")
        elif "designer" in title or "ux" in title or "ui" in title:
            adaptations.append("This user has design background. Emphasize user experience, design patterns, and visual/interaction considerations.")
        
        # Combine base personality with adaptations
        if adaptations:
            adapted_prompt = f"{base_personality}\n\n**CONTEXTUAL ADAPTATIONS FOR THIS RESPONSE:**\n" + "\n".join(f"- {adaptation}" for adaptation in adaptations)
        else:
            adapted_prompt = base_personality
        
        return adapted_prompt
    
    def _get_base_personality_prompt(self) -> str:
        """
        Get the base personality prompt from prompts.yaml.
        """
        from utils.prompt_loader import get_client_agent_prompt
        return get_client_agent_prompt()
    
    def _integrate_sources_elegantly(self, response: str, orchestrator_output: Dict[str, Any]) -> str:
        """
        Integrate source links elegantly into the response.
        """
        source_links = orchestrator_output.get("source_links", [])
        if not source_links:
            return response
        
        # Group sources by type for better presentation
        sources_by_type = {}
        for source in source_links:
            source_type = source.get("type", "web")
            if source_type not in sources_by_type:
                sources_by_type[source_type] = []
            sources_by_type[source_type].append(source)
        
        # Build elegant source presentation
        source_sections = []
        
        # Priority order for source types
        type_order = ["confluence", "jira", "slack", "web"]
        type_names = {
            "confluence": "📚 *Documentation*",
            "jira": "🎫 *Project Tickets*", 
            "slack": "💬 *Team Discussions*",
            "web": "🌐 *External Resources*"
        }
        
        for source_type in type_order:
            if source_type in sources_by_type:
                type_sources = sources_by_type[source_type]
                type_name = type_names.get(source_type, f"*{source_type.title()} Sources*")
                
                source_lines = [type_name]
                for source in type_sources[:3]:  # Limit to 3 per type
                    title = source.get("title", "Source")
                    url = source.get("url", "")
                    if url:
                        source_lines.append(f"• <{url}|{title}>")
                    else:
                        source_lines.append(f"• {title}")
                
                source_sections.append("\n".join(source_lines))
        
        # Add sources section to response
        if source_sections:
            response += "\n\n" + "\n\n".join(source_sections)
        
        return response
    
    async def _generate_intelligent_suggestions(self, orchestrator_output: Dict[str, Any], user_context: Dict[str, Any]) -> List[str]:
        """
        Generate intelligent follow-up suggestions that build on orchestrator's intelligence.
        """
        # Start with orchestrator's suggested follow-ups
        orchestrator_suggestions = orchestrator_output.get("suggested_followups", [])
        
        # Generate additional contextual suggestions using LLM
        context_prompt = f"""
        Based on this conversation context, generate 2-3 smart follow-up questions that would be valuable:
        
        Original Query: {user_context.get('query', '')}
        Key Findings: {', '.join(orchestrator_output.get('key_findings', []))}
        Confidence Level: {orchestrator_output.get('confidence_level', 'medium')}
        User Role: {user_context.get('user', {}).get('title', 'User')}
        
        Generate follow-up questions that:
        1. Build naturally on what was discovered
        2. Are appropriate for the user's role and expertise level
        3. Explore practical next steps or deeper insights
        4. Are concise and actionable
        
        Return only the questions, one per line, without numbering or bullet points.
        """
        
        try:
            llm_suggestions = await self.gemini_client.generate_response(
                "You are an expert at generating intelligent follow-up questions that build on previous findings.",
                context_prompt,
                model=self.gemini_client.flash_model,
                max_tokens=300,
                temperature=0.7
            )
            
            if llm_suggestions:
                generated_suggestions = [s.strip() for s in llm_suggestions.split("\n") if s.strip()]
            else:
                generated_suggestions = []
                
        except Exception as e:
            logger.warning(f"Failed to generate LLM suggestions: {e}")
            generated_suggestions = []
        
        # Combine and deduplicate suggestions
        all_suggestions = orchestrator_suggestions + generated_suggestions
        
        # Remove duplicates and limit to 4 suggestions
        unique_suggestions = []
        seen = set()
        for suggestion in all_suggestions:
            if suggestion and suggestion.lower() not in seen:
                unique_suggestions.append(suggestion)
                seen.add(suggestion.lower())
                if len(unique_suggestions) >= 4:
                    break
        
        # Fallback suggestions based on confidence level
        if not unique_suggestions:
            confidence_level = orchestrator_output.get("confidence_level", "medium")
            if confidence_level == "low":
                unique_suggestions = [
                    "Could you provide more specific details?",
                    "Would you like me to search for additional information?"
                ]
            else:
                unique_suggestions = [
                    "Would you like me to elaborate on any specific aspect?",
                    "Do you have any follow-up questions?"
                ]
        
        return unique_suggestions
    
    def _create_fallback_response(self, user_context: Dict[str, Any]) -> str:
        """
        Create contextual fallback response when main generation fails.
        """
        user_name = user_context.get("user", {}).get("first_name", "")
        if user_name:
            return f"Hey {user_name}, I'm having trouble crafting a response right now. Could you try asking again or rephrase your question?"
        else:
            return "I'm having trouble crafting a response right now. Could you try asking again or rephrasing your question?"
    
    async def _fallback_to_legacy_processing(self, state_stack: Dict[str, Any], user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fallback to legacy processing when orchestrator output doesn't match new format.
        """
        logger.info("Using legacy processing for backward compatibility")
        
        # Import and use the original client agent logic
        from agents.client_agent import ClientAgent as LegacyClientAgent
        legacy_client = LegacyClientAgent()
        
        # Convert user_context back to legacy state_stack format if needed
        if "orchestrator_findings" not in state_stack:
            # Build legacy format from user_context
            state_stack.update({
                "query": user_context.get("query", ""),
                "user": user_context.get("user", {}),
                "context": user_context.get("channel_context", {}),
                "conversation_memory": {"live_history": user_context.get("conversation_history", "")}
            })
        
        return await legacy_client.generate_response(state_stack)
    
    def _contains_raw_json(self, text: str) -> bool:
        """
        Check if response contains raw JSON fragments that should be filtered out.
        """
        json_patterns = ['"key_findings"', '"synthesized_response"', '"source_links"', '"confidence_level"']
        return any(pattern in text for pattern in json_patterns) or (text.strip().startswith('{') and text.strip().endswith('}'))