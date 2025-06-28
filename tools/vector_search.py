"""
Vector Search Tool - Pinecone-based vector search for Slack knowledge base.
Uses Pinecone for storing and searching conversation embeddings.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from config import settings
from services.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class VectorSearchTool:
    """
    Pinecone-based vector search tool for semantic search of Slack conversations.
    """
    
    def __init__(self):
        """Initialize Pinecone vector search tool."""
        self.pinecone_available = bool(settings.PINECONE_API_KEY)
        
        if self.pinecone_available:
            try:
                from pinecone import Pinecone
                self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                self.index_name = settings.PINECONE_INDEX_NAME
                
                # Get the index
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Pinecone vector search initialized with index: {self.index_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {e}")
                self.pinecone_available = False
        
        if not self.pinecone_available:
            logger.warning("Vector search in placeholder mode - Pinecone not available")
    
    async def search(
        self, 
        query: str, 
        top_k: int = 10, 
        filters: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content in the Pinecone vector database.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of search results with content and metadata
        """
        if not self.pinecone_available:
            logger.info(f"Vector search called with query: '{query[:50]}...' (placeholder mode)")
            return []
        
        try:
            start_time = time.time()
            
            # Generate embedding for the query using our embedding service
            from services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            query_embedding = await embedding_service.embed_text(query)
            
            if not query_embedding:
                logger.warning(f"Failed to generate embedding for query: '{query[:50]}...'")
                return []
            
            # Query Pinecone with the generated embedding
            query_response = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=include_metadata,
                filter=filters or {}
            )
            
            search_duration_ms = (time.time() - start_time) * 1000
            
            results = []
            if query_response and hasattr(query_response, 'matches'):
                for match in query_response.matches:
                    result = {
                        "id": match.id,
                        "score": match.score,
                        "content": match.metadata.get("content", "") if match.metadata else "",
                        "metadata": match.metadata or {}
                    }
                    results.append(result)
            
            # Log vector search trace
            await trace_manager.log_vector_search(
                query=query,
                results=results,
                search_duration_ms=search_duration_ms,
                metadata={"filters": filters, "top_k": top_k}
            )
            
            logger.info(f"Vector search returned {len(results)} results for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    async def search_with_multiple_queries(
        self, 
        queries: List[str], 
        top_k_per_query: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with multiple queries and combine results.
        
        Args:
            queries: List of search queries
            top_k_per_query: Results per query
            filters: Optional metadata filters
            
        Returns:
            Combined list of search results
        """
        if not self.pinecone_available:
            logger.info(f"Multi-query search called with {len(queries)} queries (placeholder mode)")
            return []
        
        all_results = []
        for query in queries:
            results = await self.search(query, top_k_per_query, filters)
            all_results.extend(results)
        
        # Remove duplicates based on ID
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                unique_results.append(result)
        
        return unique_results
    
    async def search_with_expansion(
        self, 
        query: str, 
        top_k: int = 10,
        expand_query: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search with query expansion (simplified version without ML).
        
        Args:
            query: Original search query
            top_k: Number of results to return
            expand_query: Whether to expand the query (currently unused)
            
        Returns:
            List of search results
        """
        if not self.pinecone_available:
            logger.info(f"Expanded search called with query: '{query[:50]}...' (placeholder mode)")
            return []
        
        # For now, just perform a regular search
        # In the future, this could use the Gemini API to expand queries
        return await self.search(query, top_k)
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Return empty index stats."""
        return {
            "status": "placeholder_mode",
            "total_vectors": 0,
            "message": "Vector search not yet available"
        }