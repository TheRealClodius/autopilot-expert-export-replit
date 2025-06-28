"""
Gemini Client - Wrapper for Google Gemini API interactions.
Provides structured interfaces for different types of AI model calls.
"""

import json
import logging
import os
import asyncio
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Client wrapper for Google Gemini API interactions.
    Handles different model types and structured response generation with request queuing.
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.pro_model = settings.GEMINI_PRO_MODEL
        self.flash_model = settings.GEMINI_FLASH_MODEL
        # Simple delay tracking to prevent rate limiting
        self._last_request_time = 0

        
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Generate a basic text response using Gemini.
        
        Args:
            system_prompt: System instruction for the model
            user_prompt: User's input prompt
            model: Model to use (defaults to flash)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Generated text response or None on failure
        """
        try:
            model_name = model or self.flash_model
            
            # Simple rate limiting - ensure 100ms between requests
            import time
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < 0.1:
                await asyncio.sleep(0.1 - time_since_last)
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(role="user", parts=[types.Part(text=user_prompt)])
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            self._last_request_time = time.time()
            
            if response and response.text:
                logger.debug(f"Generated response with {model_name}")
                return response.text.strip()
            
            logger.warning(f"Empty response from {model_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            return None
    
    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "json",
        model: str = None,
        schema: Optional[BaseModel] = None
    ) -> Optional[str]:
        """
        Generate a structured response (JSON) using Gemini.
        
        Args:
            system_prompt: System instruction for the model
            user_prompt: User's input prompt
            response_format: Expected response format
            model: Model to use (defaults to flash for speed)
            schema: Optional Pydantic schema for validation
            
        Returns:
            Generated structured response or None on failure
        """
        try:
            model_name = model or self.flash_model
            
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
            
            # Add schema if provided
            if schema:
                config.response_schema = schema
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(role="user", parts=[types.Part(text=user_prompt)])
                ],
                config=config
            )
            
            if response and response.text:
                logger.debug(f"Generated structured response with {model_name}")
                return response.text.strip()
            
            logger.warning(f"Empty structured response from {model_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating structured Gemini response: {e}")
            return None
    
    async def analyze_query_intent(
        self,
        query: str,
        context: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze query intent and extract key information.
        
        Args:
            query: User query to analyze
            context: Additional context information
            
        Returns:
            Dictionary with intent analysis or None on failure
        """
        try:
            system_prompt = """You are an expert at analyzing user queries in a workplace context.

Analyze the user's query and extract:
1. Intent type (information_seeking, troubleshooting, person_lookup, project_status, etc.)
2. Key entities mentioned (people, projects, technologies, etc.)
3. Time references (latest, yesterday, last week, etc.)
4. Urgency level (low, medium, high)
5. Specificity level (vague, specific, very_specific)

Return your analysis as JSON with these fields:
- intent_type: string
- entities: list of strings
- time_references: list of strings
- urgency: string
- specificity: string
- confidence: float (0.0 to 1.0)
- suggested_tools: list of strings (vector_search, etc.)
"""
            
            context_str = ""
            if context:
                context_str = f"\nContext: {json.dumps(context, indent=2)}"
            
            user_prompt = f"""Query to analyze: "{query}"{context_str}

Provide a comprehensive analysis of this query."""
            
            response = await self.generate_structured_response(
                system_prompt,
                user_prompt,
                response_format="json"
            )
            
            if response:
                try:
                    return json.loads(response)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse query intent JSON: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing query intent: {e}")
            return None
    
    async def generate_search_queries(
        self,
        original_query: str,
        max_queries: int = 5
    ) -> List[str]:
        """
        Generate multiple search queries from an original query.
        
        Args:
            original_query: The original user query
            max_queries: Maximum number of queries to generate
            
        Returns:
            List of generated search queries
        """
        try:
            system_prompt = f"""You are an expert at generating search queries for a knowledge base.

Given an original query, generate {max_queries} related search queries that would help find relevant information.

Guidelines:
- Include the original query as one of the results
- Generate variations with different keywords
- Consider different aspects of the question
- Keep queries specific and actionable
- Focus on finding concrete information

Return only a JSON array of query strings."""
            
            user_prompt = f'Original query: "{original_query}"'
            
            response = await self.generate_structured_response(
                system_prompt,
                user_prompt,
                response_format="json"
            )
            
            if response:
                try:
                    queries = json.loads(response)
                    if isinstance(queries, list):
                        # Ensure we have the original query
                        if original_query not in queries:
                            queries.insert(0, original_query)
                        return queries[:max_queries]
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse search queries JSON: {e}")
            
            # Fallback to original query
            return [original_query]
            
        except Exception as e:
            logger.error(f"Error generating search queries: {e}")
            return [original_query]
    
    async def summarize_content(
        self,
        content: str,
        max_length: int = 200,
        context: str = None
    ) -> Optional[str]:
        """
        Summarize content with optional context.
        
        Args:
            content: Content to summarize
            max_length: Maximum length of summary
            context: Optional context for summarization
            
        Returns:
            Summary text or None on failure
        """
        try:
            context_instruction = ""
            if context:
                context_instruction = f" Focus on aspects relevant to: {context}"
            
            system_prompt = f"""Summarize the following content concisely in no more than {max_length} characters.{context_instruction}

Maintain key information and actionable details. Make the summary clear and useful."""
            
            user_prompt = f"Content to summarize:\n\n{content}"
            
            response = await self.generate_response(
                system_prompt,
                user_prompt,
                model=self.flash_model,
                max_tokens=max_length // 3  # Rough token estimate
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
            return None
    
    async def extract_entities(
        self,
        text: str,
        entity_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.
        
        Args:
            text: Text to analyze
            entity_types: Types of entities to look for
            
        Returns:
            List of extracted entities with metadata
        """
        try:
            default_types = ["PERSON", "PROJECT", "TECHNOLOGY", "ORGANIZATION", "DATE"]
            types_to_extract = entity_types or default_types
            
            system_prompt = f"""Extract named entities from the text. Look for these types: {', '.join(types_to_extract)}

Return a JSON array of objects with:
- text: the entity text
- type: entity type
- confidence: confidence score (0.0 to 1.0)
- context: surrounding context if relevant

Only include entities you're confident about."""
            
            user_prompt = f"Text to analyze:\n\n{text}"
            
            response = await self.generate_structured_response(
                system_prompt,
                user_prompt,
                response_format="json"
            )
            
            if response:
                try:
                    entities = json.loads(response)
                    if isinstance(entities, list):
                        return entities
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse entities JSON: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    async def evaluate_response_quality(
        self,
        query: str,
        response: str,
        source_info: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of a generated response.
        
        Args:
            query: Original user query
            response: Generated response
            source_info: Information about sources used
            
        Returns:
            Quality evaluation metrics
        """
        try:
            source_context = ""
            if source_info:
                source_context = f"\nSources used: {len(source_info)} sources"
            
            system_prompt = """Evaluate the quality of this AI response to a user query.

Provide scores (0.0 to 1.0) for:
- relevance: How well does it answer the query?
- completeness: Does it provide sufficient information?
- accuracy: Is the information likely accurate based on sources?
- clarity: Is it easy to understand?
- helpfulness: Would this help the user?

Also provide:
- overall_score: Average of all scores
- feedback: Brief feedback for improvement
- missing_elements: What could be added

Return as JSON."""
            
            user_prompt = f"""Query: "{query}"

Response: "{response}"{source_context}

Evaluate this response comprehensively."""
            
            response_eval = await self.generate_structured_response(
                system_prompt,
                user_prompt,
                response_format="json"
            )
            
            if response_eval:
                try:
                    return json.loads(response_eval)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse evaluation JSON: {e}")
            
            # Return default evaluation
            return {
                "relevance": 0.5,
                "completeness": 0.5,
                "accuracy": 0.5,
                "clarity": 0.5,
                "helpfulness": 0.5,
                "overall_score": 0.5,
                "feedback": "Unable to evaluate response quality",
                "missing_elements": []
            }
            
        except Exception as e:
            logger.error(f"Error evaluating response quality: {e}")
            return {"overall_score": 0.0, "error": str(e)}
    
    async def test_connection(self) -> bool:
        """
        Test connection to Gemini API.
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            response = await self.generate_response(
                "You are a helpful assistant.",
                "Reply with exactly: 'Connection test successful'",
                max_tokens=10
            )
            
            if response and "Connection test successful" in response:
                logger.info("Gemini API connection test successful")
                return True
            
            logger.warning("Gemini API connection test failed - unexpected response")
            return False
            
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
