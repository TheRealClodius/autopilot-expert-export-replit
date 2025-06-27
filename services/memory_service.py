"""
Memory Service - Redis-based memory management for the multi-agent system.
Handles short-term memory, conversation context, and graph data persistence.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
import redis.asyncio as redis
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Service for managing Redis-based memory operations.
    Handles conversation context, temporary data, and graph persistence.
    """
    
    def __init__(self):
        self.redis_client = None
        self.redis_available = False
        self._memory_cache = {}  # Fallback in-memory cache
        self._initialize_redis()
        
    def _initialize_redis(self):
        """Initialize Redis connection with fallback to in-memory cache"""
        try:
            # Parse Redis URL and create connection
            redis_url = settings.REDIS_URL
            
            # Add password if provided
            if settings.REDIS_PASSWORD:
                if "://" in redis_url:
                    protocol, rest = redis_url.split("://", 1)
                    redis_url = f"{protocol}://:{settings.REDIS_PASSWORD}@{rest}"
            
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            self.redis_available = True
            logger.info("Redis connection initialized")
            
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_available = False
            self.redis_client = None
    
    async def health_check(self) -> bool:
        """Check Redis connection health or return True for in-memory fallback"""
        if not self.redis_available:
            # In-memory cache is always "healthy"
            return True
            
        try:
            if not self.redis_client:
                return False
            
            response = await self.redis_client.ping()
            return response == True
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            # Switch to in-memory cache if Redis fails
            self.redis_available = False
            self.redis_client = None
            return True
    
    async def store_conversation_context(
        self, 
        conversation_key: str, 
        context_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store conversation context in Redis or in-memory cache.
        
        Args:
            conversation_key: Unique key for the conversation
            context_data: Context data to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize context data
            serialized_data = json.dumps(context_data, default=str)
            
            if self.redis_available and self.redis_client:
                # Store with optional TTL in Redis
                if ttl:
                    await self.redis_client.setex(
                        conversation_key, 
                        ttl, 
                        serialized_data
                    )
                else:
                    await self.redis_client.set(conversation_key, serialized_data)
            else:
                # Store in in-memory cache
                if ttl:
                    # Calculate expiry time for in-memory cache
                    expiry = datetime.now() + timedelta(seconds=ttl)
                    self._memory_cache[conversation_key] = {
                        'data': serialized_data,
                        'expiry': expiry
                    }
                else:
                    self._memory_cache[conversation_key] = {
                        'data': serialized_data,
                        'expiry': None
                    }
            
            logger.debug(f"Stored conversation context: {conversation_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing conversation context: {e}")
            return False
    
    async def get_conversation_context(self, conversation_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation context from Redis or in-memory cache.
        
        Args:
            conversation_key: Unique key for the conversation
            
        Returns:
            Context data or None if not found
        """
        try:
            if self.redis_available and self.redis_client:
                # Get from Redis
                serialized_data = await self.redis_client.get(conversation_key)
                if serialized_data:
                    return json.loads(serialized_data)
            else:
                # Get from in-memory cache
                cached_item = self._memory_cache.get(conversation_key)
                if cached_item:
                    # Check if expired
                    if cached_item['expiry'] and datetime.now() > cached_item['expiry']:
                        # Remove expired item
                        del self._memory_cache[conversation_key]
                        return None
                    
                    return json.loads(cached_item['data'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving conversation context: {e}")
            return None
    
    async def store_temp_data(
        self, 
        key: str, 
        data: Dict[str, Any], 
        ttl: int = 3600
    ) -> bool:
        """
        Store temporary data with TTL.
        
        Args:
            key: Storage key
            data: Data to store
            ttl: Time to live in seconds (default 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            serialized_data = json.dumps(data, default=str)
            await self.redis_client.setex(key, ttl, serialized_data)
            
            logger.debug(f"Stored temp data: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error storing temp data: {e}")
            return False
    
    async def get_temp_data(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve temporary data.
        
        Args:
            key: Storage key
            
        Returns:
            Data or None if not found/expired
        """
        try:
            if not self.redis_client:
                return None
            
            serialized_data = await self.redis_client.get(key)
            
            if serialized_data:
                return json.loads(serialized_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving temp data: {e}")
            return None
    
    async def store_graph_data(self, graph_key: str, graph_data: Dict[str, Any]) -> bool:
        """
        Store graph data in Redis.
        
        Args:
            graph_key: Key for the graph
            graph_data: NetworkX graph data in node-link format
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            serialized_data = json.dumps(graph_data, default=str)
            await self.redis_client.set(f"graph:{graph_key}", serialized_data)
            
            logger.debug(f"Stored graph data: {graph_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing graph data: {e}")
            return False
    
    async def get_graph_data(self, graph_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve graph data from Redis.
        
        Args:
            graph_key: Key for the graph
            
        Returns:
            Graph data or None if not found
        """
        try:
            if not self.redis_client:
                return None
            
            serialized_data = await self.redis_client.get(f"graph:{graph_key}")
            
            if serialized_data:
                return json.loads(serialized_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving graph data: {e}")
            return None
    
    async def add_to_queue(self, queue_key: str, item: Dict[str, Any]) -> bool:
        """
        Add item to a Redis list (queue).
        
        Args:
            queue_key: Queue identifier
            item: Item to add to queue
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            serialized_item = json.dumps(item, default=str)
            await self.redis_client.lpush(queue_key, serialized_item)
            
            logger.debug(f"Added item to queue: {queue_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return False
    
    async def get_queue_items(self, queue_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get items from a Redis queue.
        
        Args:
            queue_key: Queue identifier
            limit: Maximum number of items to retrieve
            
        Returns:
            List of queue items
        """
        try:
            if not self.redis_client:
                return []
            
            # Get items from the list
            serialized_items = await self.redis_client.lrange(queue_key, 0, limit - 1)
            
            items = []
            for serialized_item in serialized_items:
                try:
                    item = json.loads(serialized_item)
                    items.append(item)
                except json.JSONDecodeError as e:
                    logger.error(f"Error deserializing queue item: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Error getting queue items: {e}")
            return []
    
    async def clear_queue(self, queue_key: str) -> bool:
        """
        Clear all items from a queue.
        
        Args:
            queue_key: Queue identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            await self.redis_client.delete(queue_key)
            logger.debug(f"Cleared queue: {queue_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            return False
    
    async def store_ingestion_metadata(
        self, 
        ingestion_type: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store metadata about data ingestion runs.
        
        Args:
            ingestion_type: Type of ingestion (daily, manual, etc.)
            metadata: Metadata about the ingestion run
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            key = f"ingestion:{ingestion_type}:{timestamp}"
            
            serialized_metadata = json.dumps(metadata, default=str)
            
            # Store with 30-day TTL
            await self.redis_client.setex(key, 30 * 24 * 3600, serialized_metadata)
            
            # Also store as latest for quick access
            latest_key = f"ingestion:latest:{ingestion_type}"
            await self.redis_client.setex(latest_key, 30 * 24 * 3600, serialized_metadata)
            
            logger.info(f"Stored ingestion metadata: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing ingestion metadata: {e}")
            return False
    
    async def get_latest_ingestion_metadata(self, ingestion_type: str) -> Optional[Dict[str, Any]]:
        """
        Get latest ingestion metadata.
        
        Args:
            ingestion_type: Type of ingestion
            
        Returns:
            Latest metadata or None if not found
        """
        try:
            if not self.redis_client:
                return None
            
            latest_key = f"ingestion:latest:{ingestion_type}"
            serialized_metadata = await self.redis_client.get(latest_key)
            
            if serialized_metadata:
                return json.loads(serialized_metadata)
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest ingestion metadata: {e}")
            return None
    
    async def cache_user_info(self, user_id: str, user_info: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Cache user information.
        
        Args:
            user_id: Slack user ID
            user_info: User information
            ttl: Cache TTL in seconds (default 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                return False
            
            key = f"user:{user_id}"
            serialized_data = json.dumps(user_info, default=str)
            await self.redis_client.setex(key, ttl, serialized_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching user info: {e}")
            return False
    
    async def get_cached_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user information.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            User info or None if not cached
        """
        try:
            if not self.redis_client:
                return None
            
            key = f"user:{user_id}"
            serialized_data = await self.redis_client.get(key)
            
            if serialized_data:
                return json.loads(serialized_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached user info: {e}")
            return None
    
    async def increment_counter(self, key: str, ttl: int = None) -> int:
        """
        Increment a counter in Redis.
        
        Args:
            key: Counter key
            ttl: Optional TTL for the counter
            
        Returns:
            New counter value
        """
        try:
            if not self.redis_client:
                return 0
            
            # Increment counter
            value = await self.redis_client.incr(key)
            
            # Set TTL if provided and this is the first increment
            if ttl and value == 1:
                await self.redis_client.expire(key, ttl)
            
            return value
            
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        try:
            if not self.redis_client:
                return {}
            
            info = await self.redis_client.info("memory")
            
            stats = {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "total_system_memory": info.get("total_system_memory", 0),
                "total_system_memory_human": info.get("total_system_memory_human", "0B")
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}
    
    async def close(self):
        """Close Redis connection"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
