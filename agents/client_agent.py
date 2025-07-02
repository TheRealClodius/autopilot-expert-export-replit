"""
Enhanced Client Agent - Sophisticated personality with full orchestrator intelligence integration.
Takes orchestrator's clean synthesized output and applies dynamic personality, contextual adaptations, and elegant presentation.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List

from utils.gemini_client import GeminiClient
from utils.prompt_loader import get_client_agent_prompt
from services.core.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class ClientAgent:
    """
    Enhanced client-facing agent with sophisticated personality and contextual adaptations.
    Takes clean synthesized output from orchestrator and applies:
    - Dynamic personality based on context (DM vs channel, user role, confidence level)
    - Elegant source link integration
    - Contextual intelligence and tone adaptation
    - Enhanced user experience with engaging follow-ups
    """
    
    def __init__(self):
        self.gemini_client = GeminiClient()
        
    async def generate_response(self, orchestrator_output: Dict[str, Any], message_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate sophisticated persona-based response using orchestrator's clean output.
        
        Args:
            orchestrator_output: Clean output from new orchestrator framework:
                - synthesized_response: Comprehensive answer
                - key_findings: Important points
                - source_links: Formatted links with titles/URLs
                - confidence_level: high/medium/low
                - suggested_followups: Intelligent suggestions
                - execution_summary: Process metadata
            message_context: User and channel context for personalization
            
        Returns:
            Dictionary containing enhanced response text and suggestions
        """
        try:
            start_time = time.time()
            logger.info("Enhanced Client Agent generating contextual response...")
            
            # Extract orchestrator intelligence
            base_response = orchestrator_output.get("synthesized_response", "")
            key_findings = orchestrator_output.get("key_findings", [])
            source_links = orchestrator_output.get("source_links", [])
            confidence_level = orchestrator_output.get("confidence_level", "medium")
            orchestrator_suggestions = orchestrator_output.get("suggested_followups", [])
            execution_summary = orchestrator_output.get("execution_summary", {})
            
            # Check if we have sufficient content for enhancement
            if not base_response or len(base_response.strip()) < 10:
                logger.warning(f"Base response too short ({len(base_response)} chars), using fallback")
                return await self._create_fallback_response(orchestrator_output, message_context)
            
            # Analyze context for personality adaptation
            context_analysis = self._analyze_context(message_context, confidence_level, execution_summary)
            
            # Apply sophisticated personality with contextual adaptations
            enhanced_response = await self._apply_contextual_personality(
                base_response, key_findings, source_links, context_analysis, message_context
            )
            
            # Generate enhanced follow-up suggestions
            enhanced_suggestions = await self._generate_enhanced_suggestions(
                orchestrator_suggestions, context_analysis, message_context
            )
            
            # Add elegant source integration if sources exist
            if source_links:
                enhanced_response = self._integrate_sources_elegantly(enhanced_response, source_links, context_analysis)
            
            total_time = time.time() - start_time
            logger.info(f"Enhanced Client Agent generated contextual response in {total_time:.2f}s")
            
            return {
                "text": enhanced_response,
                "suggestions": enhanced_suggestions,
                "personality_context": context_analysis,
                "confidence_communicated": confidence_level
            }
            
        except Exception as e:
            logger.error(f"Error in Enhanced Client Agent: {e}")
            return await self._create_fallback_response(orchestrator_output, message_context)
    
    def _analyze_context(self, message_context: Dict[str, Any], confidence_level: str, execution_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze context to determine personality adaptations needed.
        """
        user = message_context.get("user", {})
        context = message_context.get("context", {})
        
        # Determine communication style based on context
        is_dm = context.get("is_dm", False)
        user_title = user.get("title", "").lower()
        user_department = user.get("department", "").lower()
        steps_completed = execution_summary.get("steps_completed", 0)
        
        # Role analysis for tone adaptation
        is_technical_role = any(role in user_title for role in ["engineer", "developer", "architect", "technical"])
        is_design_role = any(role in user_title for role in ["design", "ux", "ui", "product"])
        is_management_role = any(role in user_title for role in ["manager", "director", "lead", "head"])
        
        # Confidence and complexity analysis
        is_high_confidence = confidence_level == "high"
        is_complex_query = steps_completed > 3
        
        return {
            "communication_style": "casual_direct" if is_dm else "professional_engaging",
            "expertise_level": "technical" if is_technical_role else "design" if is_design_role else "business",
            "authority_level": "peer" if not is_management_role else "leadership",
            "confidence_tone": "confident" if is_high_confidence else "thoughtful" if confidence_level == "medium" else "exploratory",
            "complexity_handled": "sophisticated" if is_complex_query else "straightforward",
            "personality_elements": {
                "use_design_references": is_design_role or "design" in user_department,
                "technical_depth": is_technical_role,
                "construct_mentions": is_dm and confidence_level == "high",  # Only in DMs when confident
                "humor_level": "subtle" if not is_management_role else "minimal"
            }
        }
    
    async def _apply_contextual_personality(self, base_response: str, key_findings: List[str], 
                                          source_links: List[Dict], context_analysis: Dict[str, Any], 
                                          message_context: Dict[str, Any]) -> str:
        """
        Apply sophisticated personality with contextual adaptations.
        """
        try:
            # Build personality adaptation prompt
            personality_prompt = self._build_personality_prompt(base_response, key_findings, context_analysis, message_context)
            
            # Get dynamic system prompt based on context
            system_prompt = self._get_contextual_system_prompt(context_analysis)
            
            logger.info(f"Client Agent calling Gemini Flash with system: {len(system_prompt)} chars, user: {len(personality_prompt)} chars")
            
            # Generate personality-enhanced response with high token limit
            enhanced_response = await asyncio.wait_for(
                self.gemini_client.generate_response(
                    system_prompt,
                    personality_prompt,
                    model=self.gemini_client.flash_model,
                    max_tokens=5000,  # High limit to ensure complex personality prompts complete
                    temperature=1.0  # Higher temperature for more personality
                ),
                timeout=12.0
            )
            
            logger.info(f"Gemini Flash response: {'SUCCESS' if enhanced_response else 'EMPTY'} ({len(enhanced_response) if enhanced_response else 0} chars)")
            
            if enhanced_response and not self._contains_inappropriate_content(enhanced_response):
                return self._post_process_personality_response(enhanced_response, context_analysis)
            else:
                # Fallback to base response with minimal enhancement
                return self._apply_minimal_personality(base_response, context_analysis, message_context)
                
        except Exception as e:
            logger.warning(f"Personality enhancement failed: {e}, using fallback")
            return self._apply_minimal_personality(base_response, context_analysis, message_context)
    
    def _build_personality_prompt(self, base_response: str, key_findings: List[str], 
                                context_analysis: Dict[str, Any], message_context: Dict[str, Any]) -> str:
        """
        Build sophisticated personality adaptation prompt.
        """
        user = message_context.get("user", {})
        context = message_context.get("context", {})
        
        prompt_parts = []
        
        # Base content to enhance
        prompt_parts.append("ENHANCE THIS RESPONSE WITH YOUR PERSONALITY:")
        prompt_parts.append(f'"{base_response}"')
        prompt_parts.append("")
        
        # Context for personality adaptation
        prompt_parts.append("CONTEXT FOR PERSONALITY:")
        if user.get("first_name"):
            prompt_parts.append(f"User: {user['first_name']} ({user.get('title', 'User')})")
        
        if context.get("is_dm"):
            prompt_parts.append("Setting: Direct message (more casual)")
        else:
            prompt_parts.append(f"Setting: #{context.get('channel_name', 'channel')} (public)")
        
        prompt_parts.append(f"Communication style: {context_analysis['communication_style']}")
        prompt_parts.append(f"Confidence level: {context_analysis['confidence_tone']}")
        prompt_parts.append("")
        
        # Key findings to potentially reference
        if key_findings:
            prompt_parts.append("KEY POINTS TO POTENTIALLY HIGHLIGHT:")
            for finding in key_findings:
                prompt_parts.append(f"• {finding}")
            prompt_parts.append("")
        
        # Personality guidance based on context
        personality_elements = context_analysis.get("personality_elements", {})
        
        if personality_elements.get("use_design_references"):
            prompt_parts.append("PERSONALITY NOTE: User has design background - you can reference design principles or art history if relevant")
        
        if personality_elements.get("technical_depth"):
            prompt_parts.append("PERSONALITY NOTE: User is technical - you can be more specific and use technical terminology")
        
        if personality_elements.get("construct_mentions") and context.get("is_dm"):
            prompt_parts.append("PERSONALITY NOTE: This is a DM and you're confident - you could mention your experiences in the Construct if naturally relevant")
        
        prompt_parts.append("")
        prompt_parts.append("ENHANCEMENT GOALS:")
        prompt_parts.append("- Add your distinctive personality and voice")
        prompt_parts.append("- Adapt tone based on context and user")
        prompt_parts.append("- Keep the core information intact")
        prompt_parts.append("- Use Slack formatting (*bold*, `code`, • bullets)")
        prompt_parts.append("- Be engaging but not overly verbose")
        
        return "\n".join(prompt_parts)
    
    def _get_contextual_system_prompt(self, context_analysis: Dict[str, Any]) -> str:
        """
        Get dynamic system prompt based on context analysis.
        """
        base_prompt = get_client_agent_prompt()
        
        # Add contextual adaptations
        adaptations = []
        
        communication_style = context_analysis.get("communication_style", "professional_engaging")
        if communication_style == "casual_direct":
            adaptations.append("This is a DM conversation - be more casual and direct.")
        
        confidence_tone = context_analysis.get("confidence_tone", "thoughtful")
        if confidence_tone == "confident":
            adaptations.append("You have high confidence in this information - be assertive and definitive.")
        elif confidence_tone == "exploratory":
            adaptations.append("You have limited information - be more exploratory and suggest next steps.")
        
        expertise_level = context_analysis.get("expertise_level", "business")
        if expertise_level == "technical":
            adaptations.append("User is technical - you can use more precise terminology and technical depth.")
        elif expertise_level == "design":
            adaptations.append("User has design background - you can reference design principles and patterns.")
        
        if adaptations:
            adapted_prompt = base_prompt + "\n\nCONTEXTUAL ADAPTATIONS FOR THIS RESPONSE:\n" + "\n".join(f"- {adaptation}" for adaptation in adaptations)
            return adapted_prompt
        
        return base_prompt
    
    def _apply_minimal_personality(self, base_response: str, context_analysis: Dict[str, Any], message_context: Dict[str, Any]) -> str:
        """
        Apply minimal personality enhancements when LLM enhancement fails.
        """
        user = message_context.get("user", {})
        confidence_tone = context_analysis.get("confidence_tone", "thoughtful")
        
        # Add confidence-based framing
        if confidence_tone == "confident":
            if user.get("first_name"):
                enhanced = f"*{user['first_name']}*, here's what I can tell you:\n\n{base_response}"
            else:
                enhanced = f"Here's what I can tell you:\n\n{base_response}"
        elif confidence_tone == "exploratory":
            enhanced = f"Based on what I found, {base_response}\n\nI'd suggest checking with the team for the most current details."
        else:
            enhanced = base_response
        
        # Ensure Slack formatting
        enhanced = enhanced.replace("**", "*")
        
        return enhanced
    
    def _integrate_sources_elegantly(self, response: str, source_links: List[Dict], context_analysis: Dict[str, Any]) -> str:
        """
        Elegantly integrate source links into organized, sectioned presentation.
        """
        if not source_links:
            return response
        
        # Enhanced source categorization with descriptive names
        source_sections = {
            "documentation": {"title": "📚 *Documentation*", "sources": []},
            "project_tickets": {"title": "🎫 *Project Tickets*", "sources": []},
            "external_resources": {"title": "🌐 *External Resources*", "sources": []},
            "team_discussions": {"title": "💬 *Team Discussions*", "sources": []}
        }
        
        # Categorize sources into appropriate sections
        for link in source_links:
            source_type = link.get("type", "web").lower()
            title = link.get("title", "Resource")
            url = link.get("url", "")
            
            if not url:
                continue
                
            # Enhanced categorization logic
            if source_type in ["confluence", "documentation", "docs"]:
                source_sections["documentation"]["sources"].append(f"• <{url}|{title}>")
            elif source_type in ["jira", "ticket", "issue"]:
                source_sections["project_tickets"]["sources"].append(f"• <{url}|{title}>")
            elif source_type in ["slack", "team", "discussion"]:
                source_sections["team_discussions"]["sources"].append(f"• <{url}|{title}>")
            else:  # web, external, etc.
                source_sections["external_resources"]["sources"].append(f"• <{url}|{title}>")
        
        # Build elegant source presentation
        source_parts = [response, ""]
        
        # Confidence-based header framing
        confidence_tone = context_analysis.get("confidence_tone", "thoughtful")
        if confidence_tone == "confident":
            # No additional header needed - sections speak for themselves
            pass
        elif confidence_tone == "exploratory":
            source_parts.append("*Worth exploring:*")
            source_parts.append("")
        elif confidence_tone == "thoughtful":
            source_parts.append("*Additional resources:*")
            source_parts.append("")
        else:  # low confidence
            source_parts.append("*Might be helpful:*")
            source_parts.append("")
        
        # Add populated sections with elegant formatting
        sections_added = 0
        for section_key, section_data in source_sections.items():
            if section_data["sources"] and sections_added < 3:  # Limit to 3 sections for readability
                source_parts.append(section_data["title"])
                
                # Add sources with proper bullet formatting
                for source in section_data["sources"][:4]:  # Max 4 sources per section
                    source_parts.append(source)
                
                source_parts.append("")  # Add spacing between sections
                sections_added += 1
        
        # Remove trailing empty line if present
        if source_parts and source_parts[-1] == "":
            source_parts.pop()
        
        return "\n".join(source_parts)
    
    async def _generate_enhanced_suggestions(self, orchestrator_suggestions: List[str], 
                                           context_analysis: Dict[str, Any], message_context: Dict[str, Any]) -> List[str]:
        """
        Generate enhanced follow-up suggestions building on orchestrator intelligence.
        """
        try:
            # If orchestrator provided good suggestions, enhance them
            if orchestrator_suggestions and len(orchestrator_suggestions) >= 2:
                enhanced = await self._enhance_existing_suggestions(orchestrator_suggestions, context_analysis, message_context)
                if enhanced:
                    return enhanced
            
            # Generate new contextual suggestions
            return await self._generate_contextual_suggestions(context_analysis, message_context)
            
        except Exception as e:
            logger.warning(f"Enhanced suggestion generation failed: {e}")
            return orchestrator_suggestions[:4] if orchestrator_suggestions else [
                "Tell me more about this",
                "How does this work in practice?",
                "What are the next steps?"
            ]
    
    async def _enhance_existing_suggestions(self, suggestions: List[str], context_analysis: Dict[str, Any], 
                                          message_context: Dict[str, Any]) -> List[str]:
        """
        Enhance orchestrator's suggestions with personality and context.
        """
        try:
            enhancement_prompt = f"""
            Enhance these follow-up suggestions with personality and context:
            
            Original suggestions:
            {chr(10).join(f'- {s}' for s in suggestions)}
            
            User context: {message_context.get('user', {}).get('title', 'User')}
            Communication style: {context_analysis.get('communication_style', 'professional')}
            
            Make them more engaging and specific to this user. Keep the same intent but add personality.
            Return 3-4 enhanced suggestions, one per line.
            """
            
            response = await asyncio.wait_for(
                self.gemini_client.generate_response(
                    "You enhance follow-up suggestions with personality while keeping them helpful and specific.",
                    enhancement_prompt,
                    model=self.gemini_client.flash_model,
                    max_tokens=1000,  # Increased for complete suggestion generation
                    temperature=0.9
                ),
                timeout=8.0
            )
            
            if response:
                enhanced_suggestions = [
                    line.strip().lstrip("1234567890.-•").strip()
                    for line in response.split("\n")
                    if line.strip() and len(line.strip()) > 10
                ]
                return enhanced_suggestions[:4]
            
        except Exception as e:
            logger.warning(f"Suggestion enhancement failed: {e}")
        
        return suggestions[:4]
    
    async def _generate_contextual_suggestions(self, context_analysis: Dict[str, Any], message_context: Dict[str, Any]) -> List[str]:
        """
        Generate contextual suggestions based on user profile and context.
        """
        user = message_context.get("user", {})
        expertise_level = context_analysis.get("expertise_level", "business")
        
        # Role-based suggestions
        if expertise_level == "technical":
            return [
                "Show me the implementation details",
                "What are the technical requirements?",
                "How do I integrate this with our system?",
                "Are there any API considerations?"
            ]
        elif expertise_level == "design":
            return [
                "What are the design patterns here?",
                "How does this impact user experience?",
                "Show me visual examples",
                "What about accessibility considerations?"
            ]
        else:
            return [
                "What's the business impact?",
                "How do we get started?",
                "What resources do we need?",
                "What are the timeline considerations?"
            ]
    
    def _post_process_personality_response(self, response: str, context_analysis: Dict[str, Any]) -> str:
        """
        Post-process personality-enhanced response for quality and formatting.
        """
        # Clean up formatting
        response = response.strip()
        response = response.replace("**", "*")  # Fix Slack formatting
        
        # Remove any JSON fragments that might have leaked through
        if "{" in response and "}" in response:
            lines = response.split("\n")
            clean_lines = [line for line in lines if not (line.strip().startswith("{") or line.strip().startswith("}"))]
            response = "\n".join(clean_lines)
        
        # Ensure appropriate length
        if len(response) > 2000:  # Slack message limit consideration
            # Truncate gracefully at sentence boundary
            sentences = response.split(". ")
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + ". ") < 1900:
                    truncated += sentence + ". "
                else:
                    break
            response = truncated.rstrip() + "\n\n_Response truncated for readability._"
        
        return response
    
    def _contains_inappropriate_content(self, response: str) -> bool:
        """
        Check for inappropriate content that shouldn't be in responses.
        """
        if not response:
            return True
        
        # Check for raw JSON contamination
        json_indicators = ['":', '{"', '"}', "null", "true", "false"]
        json_count = sum(1 for indicator in json_indicators if indicator in response)
        
        # If too much JSON-like content, it's contaminated
        if json_count > len(response.split()) * 0.3:
            return True
        
        # Check for other inappropriate patterns
        inappropriate_patterns = [
            "I don't have information",
            "I cannot provide",
            "As an AI",
            "I'm just an AI"
        ]
        
        return any(pattern.lower() in response.lower() for pattern in inappropriate_patterns)
    
    async def _create_fallback_response(self, orchestrator_output: Dict[str, Any], message_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a graceful fallback response when enhancement fails.
        """
        base_response = orchestrator_output.get("synthesized_response", "")
        confidence_level = orchestrator_output.get("confidence_level", "low")
        
        user = message_context.get("user", {})
        first_name = user.get("first_name", "")
        context = message_context.get("context", {})
        
        # Create a helpful fallback based on context
        if not base_response or len(base_response.strip()) < 10:
            # Create a contextual greeting/response based on the query
            query = message_context.get("query", "").lower()
            
            if any(word in query for word in ["hello", "hi", "hey", "test", "mention"]):
                fallback_text = f"Hi{' ' + first_name if first_name else ''}! I'm your Autopilot assistant. I can help you with project information, documentation searches, and automation guidance. What would you like to know about?"
            else:
                fallback_text = f"I'm processing your request about '{message_context.get('query', 'your question')[:50]}...' but encountered some technical difficulties. Could you try rephrasing your question or be more specific about what you're looking for?"
        else:
            # Use the base response if it exists
            if confidence_level == "high" and first_name:
                fallback_text = f"{first_name}, {base_response}"
            else:
                fallback_text = base_response
        
        # Provide helpful suggestions based on context
        default_suggestions = [
            "What can Autopilot help me with?",
            "Search for project documentation",
            "Find recent team discussions"
        ]
        
        suggestions = orchestrator_output.get("suggested_followups", default_suggestions)[:3]
        
        return {
            "text": fallback_text,
            "suggestions": suggestions,
            "personality_context": {"fallback": True, "context_aware": True},
            "confidence_communicated": confidence_level
        }