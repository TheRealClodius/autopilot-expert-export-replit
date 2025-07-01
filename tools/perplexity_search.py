"""
Perplexity Search Tool - Real-time web search using Perplexity API.
Provides current information and web-based answers for queries.
"""

import json
import logging
import time
import httpx
from typing import Dict, Any, Optional, List
from config import settings
from services.core.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class PerplexitySearchTool:
    """
    Perplexity-based search tool for real-time web information retrieval.
    """
    
    def __init__(self):
        """Initialize Perplexity search tool."""
        self.api_key = settings.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai"
        self.model = "llama-3.1-sonar-small-128k-online"
        self.available = bool(self.api_key)
        
        if self.available:
            logger.info("Perplexity search tool initialized successfully")
        else:
            logger.warning("Perplexity search tool unavailable - no API key configured")
    
    async def search(
        self, 
        query: str,
        max_tokens: Optional[int] = 1000,
        temperature: float = 0.2,
        search_domain_filter: Optional[List[str]] = None,
        search_recency_filter: str = "month"
    ) -> Dict[str, Any]:
        """
        Search for information using Perplexity's real-time web search.
        
        Args:
            query: The search query
            max_tokens: Maximum tokens in response (optional)
            temperature: Response randomness (0.0-1.0)
            search_domain_filter: List of domains to filter search (optional)
            search_recency_filter: Recency filter ('hour', 'day', 'week', 'month', 'year')
            
        Returns:
            Search results with content, citations, and metadata
        """
        if not self.available:
            return {
                "error": "Perplexity API not available - no API key configured",
                "content": "",
                "citations": [],
                "usage": {}
            }
        
        start_time = time.time()
        
        # Start tracing if available
        operation_id = await trace_manager.log_agent_operation(
            agent_name="perplexity_search",
            operation="web_search",
            input_data=f"Query: {query[:100]}...",
            metadata={"model": self.model, "full_query": query}
        ) if trace_manager else None
        
        try:
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Be precise and concise. Provide factual information with clear source attribution."
                    },
                    {
                        "role": "user", 
                        "content": query
                    }
                ],
                "temperature": temperature,
                "top_p": 0.9,
                "return_images": False,
                "return_related_questions": False,
                "search_recency_filter": search_recency_filter,
                "top_k": 0,
                "stream": False,
                "presence_penalty": 0,
                "frequency_penalty": 1
            }
            
            # Add optional parameters
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            if search_domain_filter:
                payload["search_domain_filter"] = search_domain_filter
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make the API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                response.raise_for_status()
                data = response.json()
            
            # Extract response data
            content = ""
            citations = data.get("citations", [])
            usage = data.get("usage", {})
            
            if data.get("choices") and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                content = message.get("content", "")
            
            search_time = time.time() - start_time
            
            result = {
                "content": content,
                "citations": citations,
                "usage": usage,
                "search_time": search_time,
                "model_used": self.model,
                "query": query
            }
            
            # Log successful operation
            if operation_id and trace_manager:
                await trace_manager.complete_agent_operation(
                    trace_id=operation_id,
                    output_data=f"Found {len(content)} characters with {len(citations)} citations",
                    success=True,
                    duration=search_time,
                    metadata={"content_length": len(content), "citations_count": len(citations)}
                )
            
            logger.info(f"Perplexity search completed in {search_time:.2f}s: {len(content)} chars, {len(citations)} citations")
            
            return result
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Perplexity API HTTP error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            
            if operation_id and trace_manager:
                await trace_manager.complete_agent_operation(
                    trace_id=operation_id,
                    output_data=f"HTTP Error: {error_msg}",
                    success=False,
                    duration=time.time() - start_time,
                    metadata={"error": error_msg}
                )
            
            return {
                "error": error_msg,
                "content": "",
                "citations": [],
                "usage": {}
            }
            
        except Exception as e:
            error_msg = f"Perplexity search failed: {str(e)}"
            logger.error(error_msg)
            
            if operation_id and trace_manager:
                await trace_manager.complete_agent_operation(
                    trace_id=operation_id,
                    output_data=f"General Error: {error_msg}",
                    success=False,
                    duration=time.time() - start_time,
                    metadata={"error": error_msg}
                )
            
            return {
                "error": error_msg,
                "content": "",
                "citations": [],
                "usage": {}
            }
    
    async def search_with_context(
        self,
        query: str,
        context: str = "",
        focus_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search with additional context for better results.
        
        Args:
            query: The main search query
            context: Additional context to improve search relevance
            focus_domains: Specific domains to focus search on
            
        Returns:
            Enhanced search results
        """
        enhanced_query = query
        if context:
            enhanced_query = f"Context: {context}\n\nQuery: {query}"
        
        return await self.search(
            query=enhanced_query,
            search_domain_filter=focus_domains,
            max_tokens=1200,
            temperature=0.1  # Lower temperature for more focused results
        )