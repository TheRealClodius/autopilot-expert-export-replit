"""
Vector Search Tool - Handles similarity searches in the Pinecone vector database.
Provides intelligent search capabilities with query expansion and filtering.
"""

import logging
from typing import List, Dict, Any, Optional

from config import settings

logger = logging.getLogger(__name__)

class VectorSearchTool:
    """
    Tool for performing vector similarity searches in the knowledge base.
    Handles query processing, embedding generation, and result formatting.
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self._initialize_pinecone()
        
    def _initialize_pinecone(self):
        """Initialize Pinecone client and index"""
        try:
            self.pc = Pinecone(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            logger.info(f"Initialized Pinecone index: {settings.PINECONE_INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    async def search(
        self, 
        query: str, 
        top_k: int = 10, 
        filters: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional metadata filters
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of search results with content and metadata
        """
        try:
            logger.info(f"Performing vector search for: {query[:100]}...")
            
            # Generate embedding for the query
            query_embedding = await self.embedding_service.embed_text(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Prepare search parameters
            search_params = {
                "vector": query_embedding,
                "top_k": min(top_k, settings.MAX_SEARCH_RESULTS),
                "include_metadata": include_metadata
            }
            
            # Add filters if provided
            if filters:
                search_params["filter"] = self._prepare_filters(filters)
            
            # Perform the search
            search_results = self.index.query(**search_params)
            
            # Format results
            formatted_results = self._format_search_results(search_results)
            
            logger.info(f"Found {len(formatted_results)} relevant results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            return []
    
    async def search_with_multiple_queries(
        self, 
        queries: List[str], 
        top_k_per_query: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform multiple searches and combine results.
        
        Args:
            queries: List of search queries
            top_k_per_query: Results per query
            filters: Optional metadata filters
            
        Returns:
            Combined and deduplicated search results
        """
        try:
            logger.info(f"Performing multi-query search with {len(queries)} queries")
            
            all_results = []
            seen_ids = set()
            
            for query in queries:
                results = await self.search(query, top_k_per_query, filters)
                
                # Deduplicate results
                for result in results:
                    result_id = result.get("id")
                    if result_id and result_id not in seen_ids:
                        all_results.append(result)
                        seen_ids.add(result_id)
            
            # Sort by relevance score
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # Limit total results
            max_results = min(len(all_results), settings.MAX_SEARCH_RESULTS)
            final_results = all_results[:max_results]
            
            logger.info(f"Combined multi-query search returned {len(final_results)} unique results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in multi-query search: {e}")
            return []
    
    async def search_with_expansion(
        self, 
        query: str, 
        top_k: int = 10,
        expand_query: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform search with automatic query expansion.
        
        Args:
            query: Original search query
            top_k: Number of results to return
            expand_query: Whether to expand the query
            
        Returns:
            Search results from expanded queries
        """
        try:
            if not expand_query:
                return await self.search(query, top_k)
            
            # Generate expanded queries
            expanded_queries = await self._expand_query(query)
            
            if len(expanded_queries) <= 1:
                # No expansion possible, use original query
                return await self.search(query, top_k)
            
            # Search with multiple expanded queries
            return await self.search_with_multiple_queries(
                expanded_queries, 
                top_k_per_query=max(2, top_k // len(expanded_queries))
            )
            
        except Exception as e:
            logger.error(f"Error in expanded search: {e}")
            return await self.search(query, top_k)  # Fallback to simple search
    
    def _prepare_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare filters for Pinecone query format.
        
        Args:
            filters: Raw filter dictionary
            
        Returns:
            Formatted filters for Pinecone
        """
        try:
            pinecone_filters = {}
            
            for key, value in filters.items():
                if isinstance(value, list):
                    # Handle list values (e.g., channel names)
                    pinecone_filters[key] = {"$in": value}
                elif isinstance(value, dict):
                    # Handle range queries
                    pinecone_filters[key] = value
                else:
                    # Handle exact matches
                    pinecone_filters[key] = {"$eq": value}
            
            return pinecone_filters
            
        except Exception as e:
            logger.error(f"Error preparing filters: {e}")
            return {}
    
    def _format_search_results(self, search_results) -> List[Dict[str, Any]]:
        """
        Format Pinecone search results for consumption by agents.
        
        Args:
            search_results: Raw Pinecone search results
            
        Returns:
            Formatted results list
        """
        try:
            formatted_results = []
            
            if not hasattr(search_results, 'matches'):
                return formatted_results
            
            for match in search_results.matches:
                result = {
                    "id": match.id,
                    "score": float(match.score),
                    "metadata": match.metadata or {},
                    "content": ""
                }
                
                # Extract content from metadata
                if match.metadata:
                    result["content"] = match.metadata.get("content", "")
                    result["source"] = match.metadata.get("source", "Unknown")
                    result["timestamp"] = match.metadata.get("timestamp", "")
                    result["channel"] = match.metadata.get("channel", "")
                    result["user"] = match.metadata.get("user", "")
                
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error formatting search results: {e}")
            return []
    
    async def _expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms and related terms.
        
        Args:
            query: Original query string
            
        Returns:
            List of expanded queries including the original
        """
        try:
            # Simple expansion - could be enhanced with ML models
            expanded_queries = [query]
            
            # Add variations based on common patterns
            query_lower = query.lower()
            
            # Project-related expansions
            if "project" in query_lower or "autopilot" in query_lower:
                expanded_queries.extend([
                    query + " updates",
                    query + " owner",
                    query + " dependencies"
                ])
            
            # Update-related expansions
            if "latest" in query_lower or "update" in query_lower:
                expanded_queries.extend([
                    query.replace("latest", "recent"),
                    query.replace("update", "change"),
                    query + " status"
                ])
            
            # Person-related expansions
            if "who" in query_lower:
                expanded_queries.extend([
                    query.replace("who", "owner"),
                    query.replace("who", "responsible")
                ])
            
            # Remove duplicates while preserving order
            unique_queries = []
            for q in expanded_queries:
                if q not in unique_queries:
                    unique_queries.append(q)
            
            logger.info(f"Expanded query '{query}' into {len(unique_queries)} variations")
            return unique_queries[:5]  # Limit expansions
            
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return [query]
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}
