"""
Webhook Caching Service

Implements intelligent caching for Slack webhook processing to reduce
redundant operations and improve response times.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached webhook processing result"""
    result: Dict[str, Any]
    timestamp: float
    processing_time: float
    hit_count: int = 0
    
class WebhookCache:
    """
    Manages webhook response caching with intelligent invalidation
    and deduplication to prevent redundant processing
    """
    
    def __init__(self, memory_service=None):
        self.memory_service = memory_service
        self.cache: Dict[str, CacheEntry] = {}
        
        # Cache configuration
        self.cache_ttl = 300  # 5 minutes default TTL
        self.max_cache_size = 1000
        self.duplicate_window = 30  # 30 seconds for duplicate detection
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "duplicates_prevented": 0,
            "processing_time_saved": 0.0
        }
        
        logger.info("Webhook cache initialized")
    
    def _generate_cache_key(self, event_data: Dict[str, Any]) -> str:
        """Generate a unique cache key for webhook event"""
        # Extract key fields for caching
        key_fields = {
            "user": event_data.get("event", {}).get("user"),
            "text": event_data.get("event", {}).get("text"),
            "channel": event_data.get("event", {}).get("channel"),
            "ts": event_data.get("event", {}).get("ts"),
            "thread_ts": event_data.get("event", {}).get("thread_ts"),
            "type": event_data.get("event", {}).get("type")
        }
        
        # Create hash from normalized key fields
        key_string = json.dumps(key_fields, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _generate_duplicate_key(self, event_data: Dict[str, Any]) -> str:
        """Generate key for duplicate detection (less specific than cache key)"""
        duplicate_fields = {
            "user": event_data.get("event", {}).get("user"),
            "text": event_data.get("event", {}).get("text"),
            "channel": event_data.get("event", {}).get("channel")
        }
        
        key_string = json.dumps(duplicate_fields, sort_keys=True)
        return f"dup_{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def get_cached_response(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check for cached response to webhook event
        Returns cached result if found and valid, None otherwise
        """
        try:
            self.stats["total_requests"] += 1
            
            cache_key = self._generate_cache_key(event_data)
            current_time = time.time()
            
            # Check memory cache first
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                
                # Check if cache entry is still valid
                if current_time - entry.timestamp <= self.cache_ttl:
                    entry.hit_count += 1
                    self.stats["cache_hits"] += 1
                    self.stats["processing_time_saved"] += entry.processing_time
                    
                    logger.info(f"📋 Cache HIT for webhook (saved {entry.processing_time:.3f}s, hit #{entry.hit_count})")
                    return entry.result
                else:
                    # Remove expired entry
                    del self.cache[cache_key]
            
            # Check persistent cache if memory service available
            if self.memory_service:
                try:
                    cached_data = await self.memory_service.get_conversation_context(f"webhook_cache_{cache_key}")
                    if cached_data and current_time - cached_data.get("timestamp", 0) <= self.cache_ttl:
                        # Restore to memory cache
                        entry = CacheEntry(
                            result=cached_data["result"],
                            timestamp=cached_data["timestamp"],
                            processing_time=cached_data["processing_time"],
                            hit_count=cached_data.get("hit_count", 0) + 1
                        )
                        self.cache[cache_key] = entry
                        
                        self.stats["cache_hits"] += 1
                        self.stats["processing_time_saved"] += entry.processing_time
                        
                        logger.info(f"📋 Persistent cache HIT for webhook (saved {entry.processing_time:.3f}s)")
                        return entry.result
                except Exception as e:
                    logger.debug(f"Persistent cache check failed: {e}")
            
            self.stats["cache_misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return None
    
    async def is_duplicate_request(self, event_data: Dict[str, Any]) -> bool:
        """
        Check if this is a duplicate request within the duplicate window
        Helps prevent processing the same message multiple times
        """
        try:
            duplicate_key = self._generate_duplicate_key(event_data)
            current_time = time.time()
            
            # Check memory cache for recent duplicates
            for key, entry in list(self.cache.items()):
                if key.startswith("dup_") and current_time - entry.timestamp <= self.duplicate_window:
                    if key == duplicate_key:
                        self.stats["duplicates_prevented"] += 1
                        logger.info(f"🔄 Duplicate webhook detected - preventing reprocessing")
                        return True
            
            # Mark this request to prevent future duplicates
            dup_entry = CacheEntry(
                result={"duplicate_marker": True},
                timestamp=current_time,
                processing_time=0.0
            )
            self.cache[duplicate_key] = dup_entry
            
            return False
            
        except Exception as e:
            logger.error(f"Duplicate check error: {e}")
            return False
    
    async def cache_response(self, event_data: Dict[str, Any], result: Dict[str, Any], 
                           processing_time: float) -> None:
        """
        Cache the webhook processing result for future use
        """
        try:
            cache_key = self._generate_cache_key(event_data)
            current_time = time.time()
            
            # Create cache entry
            entry = CacheEntry(
                result=result,
                timestamp=current_time,
                processing_time=processing_time
            )
            
            # Store in memory cache
            self.cache[cache_key] = entry
            
            # Store in persistent cache if available
            if self.memory_service:
                try:
                    cache_data = {
                        "result": result,
                        "timestamp": current_time,
                        "processing_time": processing_time,
                        "hit_count": 0
                    }
                    await self.memory_service.store_conversation_context(
                        f"webhook_cache_{cache_key}", 
                        cache_data, 
                        ttl=self.cache_ttl
                    )
                except Exception as e:
                    logger.debug(f"Persistent cache storage failed: {e}")
            
            # Cleanup old entries if cache is too large
            await self._cleanup_cache()
            
            logger.info(f"💾 Cached webhook response (processing time: {processing_time:.3f}s)")
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    async def _cleanup_cache(self) -> None:
        """Clean up expired and excess cache entries"""
        try:
            current_time = time.time()
            
            # Remove expired entries
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time - entry.timestamp > self.cache_ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            # Remove oldest entries if cache is too large
            if len(self.cache) > self.max_cache_size:
                # Sort by timestamp and remove oldest
                sorted_entries = sorted(
                    self.cache.items(),
                    key=lambda x: x[1].timestamp
                )
                
                excess_count = len(self.cache) - self.max_cache_size
                for i in range(excess_count):
                    key, _ = sorted_entries[i]
                    del self.cache[key]
                
                logger.info(f"🧹 Cache cleanup: removed {len(expired_keys)} expired + {excess_count} excess entries")
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    def should_cache_response(self, event_data: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        Determine if a response should be cached based on event type and result
        """
        try:
            event = event_data.get("event", {})
            
            # Don't cache certain event types
            if event.get("type") in ["url_verification", "challenge"]:
                return False
            
            # Don't cache error responses
            if result.get("status") == "error":
                return False
            
            # Don't cache empty or invalid responses
            if not result or "status" not in result:
                return False
            
            # Cache successful message processing
            return True
            
        except Exception:
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        current_time = time.time()
        
        # Calculate cache effectiveness
        total_requests = self.stats["total_requests"]
        cache_hits = self.stats["cache_hits"]
        hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        # Count active cache entries
        active_entries = sum(
            1 for entry in self.cache.values()
            if current_time - entry.timestamp <= self.cache_ttl
        )
        
        return {
            "cache_enabled": True,
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "cache_misses": self.stats["cache_misses"],
            "duplicates_prevented": self.stats["duplicates_prevented"],
            "hit_rate_percentage": round(hit_rate, 1),
            "processing_time_saved": round(self.stats["processing_time_saved"], 3),
            "active_cache_entries": active_entries,
            "cache_size_limit": self.max_cache_size,
            "cache_ttl_seconds": self.cache_ttl,
            "duplicate_window_seconds": self.duplicate_window
        }
    
    async def clear_cache(self) -> Dict[str, Any]:
        """Clear all cache entries and reset statistics"""
        try:
            entries_cleared = len(self.cache)
            
            self.cache.clear()
            
            # Reset statistics
            old_stats = self.stats.copy()
            self.stats = {
                "total_requests": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "duplicates_prevented": 0,
                "processing_time_saved": 0.0
            }
            
            logger.info(f"🗑️ Cache cleared: {entries_cleared} entries removed")
            
            return {
                "status": "success",
                "entries_cleared": entries_cleared,
                "previous_stats": old_stats
            }
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }