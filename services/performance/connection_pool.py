"""
Connection Pool Service for External APIs

Maintains persistent connections to reduce latency and improve performance
for external service calls during message processing.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)

class ConnectionPool:
    """
    Manages persistent HTTP connections to external APIs
    """
    
    def __init__(self):
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._connection_stats = {
            "connections_created": 0,
            "requests_made": 0,
            "cache_hits": 0,
            "average_response_time": 0.0
        }
        self._response_times = []
        
    async def get_session(self, service_name: str) -> aiohttp.ClientSession:
        """Get or create a persistent session for a service"""
        if service_name not in self._sessions:
            # Create optimized connector
            connector = aiohttp.TCPConnector(
                limit=50,  # Total connection pool size per service
                limit_per_host=20,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=60,
                enable_cleanup_closed=True,
                force_close=False,
                connector_owner=False
            )
            
            # Service-specific timeout configurations
            timeout_configs = {
                "slack": 10,
                "gemini": 30,
                "perplexity": 15,
                "pinecone": 20,
                "default": 15
            }
            
            timeout = aiohttp.ClientTimeout(
                total=timeout_configs.get(service_name, timeout_configs["default"])
            )
            
            # Service-specific headers
            headers = {
                "User-Agent": "Autopilot-Expert/1.0",
                "Connection": "keep-alive"
            }
            
            if service_name == "slack":
                headers.update({
                    "Content-Type": "application/json; charset=utf-8"
                })
            elif service_name == "gemini":
                headers.update({
                    "Content-Type": "application/json"
                })
            
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
            
            self._sessions[service_name] = session
            self._connection_stats["connections_created"] += 1
            
            logger.debug(f"Created persistent connection pool for {service_name}")
            
        return self._sessions[service_name]
    
    async def make_request(self, service_name: str, method: str, url: str, **kwargs) -> Any:
        """Make an optimized request using persistent connections"""
        start_time = time.time()
        
        try:
            session = await self.get_session(service_name)
            
            async with session.request(method, url, **kwargs) as response:
                response_time = time.time() - start_time
                self._track_response_time(response_time)
                
                self._connection_stats["requests_made"] += 1
                
                if response.status == 200:
                    if response.content_type == 'application/json':
                        data = await response.json()
                    else:
                        data = await response.text()
                    
                    logger.debug(f"Fast {service_name} request: {response_time:.3f}s")
                    return data
                else:
                    logger.warning(f"{service_name} request failed: {response.status}")
                    return None
                    
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"{service_name} request error after {response_time:.3f}s: {e}")
            return None
    
    def _track_response_time(self, response_time: float):
        """Track response times for performance metrics"""
        self._response_times.append(response_time)
        
        # Keep only last 100 response times for rolling average
        if len(self._response_times) > 100:
            self._response_times = self._response_times[-100:]
        
        # Update average
        self._connection_stats["average_response_time"] = sum(self._response_times) / len(self._response_times)
    
    async def warmup_connections(self):
        """Warmup connections to all major services"""
        services_to_warmup = [
            ("slack", "https://slack.com/api/auth.test"),
            ("gemini", "https://generativelanguage.googleapis.com"),
            ("perplexity", "https://api.perplexity.ai"),
            ("pinecone", "https://api.pinecone.io")
        ]
        
        warmup_tasks = []
        for service_name, base_url in services_to_warmup:
            task = self._warmup_service(service_name, base_url)
            warmup_tasks.append(task)
        
        # Execute warmups concurrently
        results = await asyncio.gather(*warmup_tasks, return_exceptions=True)
        
        successful_warmups = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Connection warmup completed: {successful_warmups}/{len(services_to_warmup)} successful")
    
    async def _warmup_service(self, service_name: str, base_url: str):
        """Warmup a specific service connection"""
        try:
            session = await self.get_session(service_name)
            
            # Make a lightweight connection to establish the pool
            async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                # Don't care about response - just establishing connection
                pass
                
            logger.debug(f"Warmed up {service_name} connection")
            
        except Exception as e:
            logger.debug(f"Warmup failed for {service_name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            "active_connections": len(self._sessions),
            "services": list(self._sessions.keys()),
            "stats": self._connection_stats.copy(),
            "performance": {
                "average_response_time_ms": round(self._connection_stats["average_response_time"] * 1000, 2),
                "total_requests": self._connection_stats["requests_made"],
                "connections_reused": max(0, self._connection_stats["requests_made"] - self._connection_stats["connections_created"])
            }
        }
    
    async def cleanup(self):
        """Cleanup all connections"""
        try:
            for service_name, session in self._sessions.items():
                await session.close()
                logger.debug(f"Closed {service_name} connection pool")
            
            self._sessions.clear()
            logger.info("All connection pools cleaned up")
            
        except Exception as e:
            logger.error(f"Connection cleanup failed: {e}")

# Global connection pool instance
connection_pool = ConnectionPool()