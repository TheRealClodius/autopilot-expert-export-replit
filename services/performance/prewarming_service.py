"""
Service Pre-warming and Keep-Alive System

This service implements connection pre-warming and keep-alive pings
to prevent cold starts and maintain ready connections to external services.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)

@dataclass
class ServiceHealth:
    """Track health status of external services"""
    name: str
    last_ping: float
    response_time: float
    success: bool
    error: Optional[str] = None

class PrewarmingService:
    """
    Manages service pre-warming and keep-alive operations
    to minimize cold start delays and maintain ready connections
    """
    
    def __init__(self, slack_client=None, memory_service=None, vector_search=None, perplexity_search=None):
        self.slack_client = slack_client
        self.memory_service = memory_service
        self.vector_search = vector_search
        self.perplexity_search = perplexity_search
        
        # Service health tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        
        # Keep-alive configuration
        self.keep_alive_interval = 60   # 1 minute for aggressive warm-keeping
        self.serverless_ping_interval = 30  # 30 seconds for serverless functions
        self.max_response_time = 5.0    # 5 seconds
        
        # Pre-warming tasks
        self._keep_alive_task: Optional[asyncio.Task] = None
        self._serverless_warm_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("Pre-warming service initialized")
    
    async def start_prewarming(self):
        """Start the pre-warming and keep-alive system"""
        try:
            logger.info("🚀 Starting service pre-warming sequence...")
            
            # Perform initial pre-warming
            await self._perform_initial_prewarming()
            
            # Start keep-alive tasks
            self._is_running = True
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
            self._serverless_warm_task = asyncio.create_task(self._serverless_keep_warm_loop())
            
            logger.info("✅ Service pre-warming completed and keep-alive started")
            
        except Exception as e:
            logger.error(f"❌ Pre-warming failed: {e}")
            raise
    
    async def stop_prewarming(self):
        """Stop the keep-alive system"""
        self._is_running = False
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
        logger.info("Pre-warming service stopped")
    
    async def _perform_initial_prewarming(self):
        """Perform initial pre-warming of all services"""
        prewarm_start = time.time()
        
        # Pre-warm services in parallel for speed
        tasks = []
        
        if self.slack_client:
            tasks.append(self._prewarm_slack_api())
        
        if self.memory_service:
            tasks.append(self._prewarm_memory_service())
        
        if self.vector_search:
            tasks.append(self._prewarm_vector_search())
        
        if self.perplexity_search:
            tasks.append(self._prewarm_perplexity_api())
        
        # Execute all pre-warming tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Pre-warming task {i} failed: {result}")
        
        prewarm_duration = time.time() - prewarm_start
        logger.info(f"🎯 Initial pre-warming completed in {prewarm_duration:.3f}s")
    
    async def _prewarm_slack_api(self):
        """Pre-warm Slack API connection"""
        try:
            start_time = time.time()
            
            # Test basic API connectivity
            response = self.slack_client.auth_test()
            
            response_time = time.time() - start_time
            success = response.get("ok", False)
            
            self.service_health["slack_api"] = ServiceHealth(
                name="Slack API",
                last_ping=time.time(),
                response_time=response_time,
                success=success
            )
            
            if success:
                logger.info(f"✅ Slack API pre-warmed successfully ({response_time:.3f}s)")
            else:
                logger.warning(f"⚠️  Slack API pre-warm failed: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Slack API pre-warming failed: {e}")
            self.service_health["slack_api"] = ServiceHealth(
                name="Slack API",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    async def _prewarm_memory_service(self):
        """Pre-warm memory service"""
        try:
            start_time = time.time()
            
            # Test memory service with a small operation
            test_key = f"prewarm_test_{int(time.time())}"
            await self.memory_service.store_conversation_context(
                test_key, {"prewarmed": True}, ttl=60
            )
            
            # Verify retrieval
            retrieved = await self.memory_service.get_conversation_context(test_key)
            
            response_time = time.time() - start_time
            success = retrieved is not None and retrieved.get("prewarmed") is True
            
            self.service_health["memory_service"] = ServiceHealth(
                name="Memory Service",
                last_ping=time.time(),
                response_time=response_time,
                success=success
            )
            
            if success:
                logger.info(f"✅ Memory service pre-warmed successfully ({response_time:.3f}s)")
            else:
                logger.warning(f"⚠️  Memory service pre-warm failed")
                
        except Exception as e:
            logger.error(f"❌ Memory service pre-warming failed: {e}")
            self.service_health["memory_service"] = ServiceHealth(
                name="Memory Service",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    async def _prewarm_vector_search(self):
        """Pre-warm vector search service"""
        try:
            start_time = time.time()
            
            if self.vector_search:
                # Test vector search with a simple query
                search_results = await self.vector_search.search(
                    query="test prewarming query",
                    top_k=1
                )
                
                response_time = time.time() - start_time
                success = isinstance(search_results, list)
            else:
                # Skip if vector search not available
                response_time = 0.0
                success = True
                logger.info("Vector search not configured - skipping pre-warm")
            
            self.service_health["vector_search"] = ServiceHealth(
                name="Vector Search",
                last_ping=time.time(),
                response_time=response_time,
                success=success
            )
            
            if success and self.vector_search:
                logger.info(f"✅ Vector search pre-warmed successfully ({response_time:.3f}s)")
                
        except Exception as e:
            logger.error(f"❌ Vector search pre-warming failed: {e}")
            self.service_health["vector_search"] = ServiceHealth(
                name="Vector Search",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    async def _prewarm_perplexity_api(self):
        """Pre-warm Perplexity API connection"""
        try:
            start_time = time.time()
            
            if self.perplexity_search:
                # Test Perplexity API with a minimal query
                search_results = await self.perplexity_search.search(
                    query="test connection",
                    max_results=1
                )
                
                response_time = time.time() - start_time
                success = isinstance(search_results, dict) and "results" in search_results
            else:
                # Skip if Perplexity search not available
                response_time = 0.0
                success = True
                logger.info("Perplexity search not configured - skipping pre-warm")
            
            self.service_health["perplexity_api"] = ServiceHealth(
                name="Perplexity API",
                last_ping=time.time(),
                response_time=response_time,
                success=success
            )
            
            if success and self.perplexity_search:
                logger.info(f"✅ Perplexity API pre-warmed successfully ({response_time:.3f}s)")
                
        except Exception as e:
            logger.error(f"❌ Perplexity API pre-warming failed: {e}")
            self.service_health["perplexity_api"] = ServiceHealth(
                name="Perplexity API",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    async def _keep_alive_loop(self):
        """Main keep-alive loop to maintain warm connections"""
        logger.info(f"🔄 Keep-alive loop started (interval: {self.keep_alive_interval}s)")
        
        while self._is_running:
            try:
                await asyncio.sleep(self.keep_alive_interval)
                
                if not self._is_running:
                    break
                
                logger.debug("🔄 Performing keep-alive pings...")
                await self._perform_keep_alive_pings()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keep-alive loop error: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
        
        logger.info("Keep-alive loop stopped")
    
    async def _serverless_keep_warm_loop(self):
        """Aggressive keep-warm loop specifically for serverless functions"""
        logger.info(f"🔥 Serverless keep-warm loop started (interval: {self.serverless_ping_interval}s)")
        
        while self._is_running:
            try:
                await asyncio.sleep(self.serverless_ping_interval)
                
                if not self._is_running:
                    break
                
                # Ping production serverless function aggressively
                await self._ping_serverless_function()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Serverless keep-warm error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
        
        logger.info("Serverless keep-warm loop stopped")
    
    async def _perform_keep_alive_pings(self):
        """Perform keep-alive pings for all services"""
        ping_tasks = []
        
        if self.slack_client:
            ping_tasks.append(self._ping_slack_api())
        
        if self.memory_service:
            ping_tasks.append(self._ping_memory_service())
        
        # Add serverless function keep-warm ping
        ping_tasks.append(self._ping_serverless_function())
        
        # Execute pings concurrently
        if ping_tasks:
            results = await asyncio.gather(*ping_tasks, return_exceptions=True)
            
            # Log any failures
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Keep-alive ping failed: {result}")
    
    async def _ping_serverless_function(self):
        """Keep-warm ping for the production serverless deployment"""
        try:
            import aiohttp
            import os
            
            start_time = time.time()
            
            # Get the production deployment URL from environment or use default
            deployment_url = os.getenv("REPLIT_DEPLOYMENT_URL", "https://intelligent-autopilot-andreiclodius.replit.app")
            health_endpoint = f"{deployment_url}/health"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(health_endpoint) as response:
                    response_time = time.time() - start_time
                    success = response.status == 200
                    
                    self.service_health["serverless_function"] = ServiceHealth(
                        name="Serverless Function",
                        last_ping=time.time(),
                        response_time=response_time,
                        success=success
                    )
                    
                    if success:
                        if response_time > 2.0:  # Warn if response is slow
                            logger.warning(f"🐌 Serverless function warming up: {response_time:.3f}s")
                        else:
                            logger.debug(f"🔥 Serverless function warm: {response_time:.3f}s")
                    else:
                        logger.warning(f"❌ Serverless function unhealthy: HTTP {response.status}")
                        
        except Exception as e:
            logger.warning(f"Serverless function keep-warm ping failed: {e}")
            self.service_health["serverless_function"] = ServiceHealth(
                name="Serverless Function",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    async def _ping_slack_api(self):
        """Keep-alive ping for Slack API"""
        try:
            start_time = time.time()
            response = self.slack_client.auth_test()
            response_time = time.time() - start_time
            
            success = response.get("ok", False)
            
            self.service_health["slack_api"] = ServiceHealth(
                name="Slack API",
                last_ping=time.time(),
                response_time=response_time,
                success=success
            )
            
            if response_time > self.max_response_time:
                logger.warning(f"🐌 Slack API slow response: {response_time:.3f}s")
            
        except Exception as e:
            logger.warning(f"Slack API keep-alive failed: {e}")
            self.service_health["slack_api"] = ServiceHealth(
                name="Slack API",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    async def _ping_memory_service(self):
        """Keep-alive ping for memory service"""
        try:
            start_time = time.time()
            
            # Simple memory operation to keep connection warm
            test_key = f"keepalive_{int(time.time())}"
            await self.memory_service.store_conversation_context(
                test_key, {"keepalive": True}, ttl=30
            )
            
            response_time = time.time() - start_time
            
            self.service_health["memory_service"] = ServiceHealth(
                name="Memory Service",
                last_ping=time.time(),
                response_time=response_time,
                success=True
            )
            
            if response_time > self.max_response_time:
                logger.warning(f"🐌 Memory service slow response: {response_time:.3f}s")
            
        except Exception as e:
            logger.warning(f"Memory service keep-alive failed: {e}")
            self.service_health["memory_service"] = ServiceHealth(
                name="Memory Service",
                last_ping=time.time(),
                response_time=0.0,
                success=False,
                error=str(e)
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all services"""
        current_time = time.time()
        status = {
            "prewarming_active": self._is_running,
            "services": {},
            "overall_health": "healthy"
        }
        
        unhealthy_count = 0
        
        for service_name, health in self.service_health.items():
            age = current_time - health.last_ping
            
            service_status = {
                "name": health.name,
                "last_ping": health.last_ping,
                "ping_age_seconds": round(age, 1),
                "response_time": health.response_time,
                "success": health.success,
                "error": health.error
            }
            
            if not health.success or age > (self.keep_alive_interval * 2):
                service_status["status"] = "unhealthy"
                unhealthy_count += 1
            else:
                service_status["status"] = "healthy"
            
            status["services"][service_name] = service_status
        
        # Determine overall health
        if unhealthy_count == 0:
            status["overall_health"] = "healthy"
        elif unhealthy_count <= len(self.service_health) // 2:
            status["overall_health"] = "degraded"
        else:
            status["overall_health"] = "unhealthy"
        
        return status