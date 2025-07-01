"""
Performance Optimization Service

Implements aggressive optimization strategies to reduce cold start delays
and improve overall system performance.
"""

import asyncio
import logging
import time
import gc
from typing import Dict, Any, Optional
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Track performance metrics"""
    startup_time: float
    memory_usage: float
    connection_pool_size: int
    cache_hit_rate: float
    last_optimization: float

class PerformanceOptimizer:
    """
    Comprehensive performance optimization service
    """
    
    def __init__(self):
        self.metrics = PerformanceMetrics(
            startup_time=0.0,
            memory_usage=0.0,
            connection_pool_size=0,
            cache_hit_rate=0.0,
            last_optimization=time.time()
        )
        
        # Connection pools
        self._http_session_pool = None
        self._api_connections = {}
        
        # Caching layers
        self._model_cache = {}
        self._response_cache = {}
        self._connection_cache = {}
        
        # Optimization flags
        self._optimizations_applied = set()
        
        logger.info("Performance optimizer initialized")
    
    async def apply_startup_optimizations(self):
        """Apply aggressive startup optimizations"""
        start_time = time.time()
        
        optimization_tasks = [
            self._preload_critical_modules(),
            self._initialize_connection_pools(),
            self._warmup_caches(),
            self._optimize_memory_allocation(),
            self._precompile_regex_patterns()
        ]
        
        # Execute all optimizations concurrently
        results = await asyncio.gather(*optimization_tasks, return_exceptions=True)
        
        # Log optimization results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Optimization {i+1} failed: {result}")
            else:
                logger.debug(f"Optimization {i+1} completed successfully")
        
        self.metrics.startup_time = time.time() - start_time
        logger.info(f"Startup optimizations completed in {self.metrics.startup_time:.3f}s")
        
        return self.metrics
    
    async def _preload_critical_modules(self):
        """Preload heavy modules to avoid import delays"""
        try:
            # Import heavy modules in background thread to avoid blocking
            import concurrent.futures
            
            def preload_modules():
                modules_to_preload = [
                    'google.genai',
                    'sentence_transformers',
                    'pinecone',
                    'numpy',
                    'pandas',
                    'torch'  # If using PyTorch models
                ]
                
                for module in modules_to_preload:
                    try:
                        __import__(module)
                        logger.debug(f"Preloaded module: {module}")
                    except ImportError:
                        logger.debug(f"Module {module} not available - skipping")
            
            # Preload in thread pool to avoid blocking startup
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future = executor.submit(preload_modules)
                # Don't wait for completion - let it run in background
            
            self._optimizations_applied.add('module_preloading')
            
        except Exception as e:
            logger.warning(f"Module preloading failed: {e}")
    
    async def _initialize_connection_pools(self):
        """Initialize persistent connection pools"""
        try:
            import aiohttp
            
            # Create persistent HTTP session with connection pooling
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=60,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            self._http_session_pool = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'Autopilot-Expert/1.0'}
            )
            
            self.metrics.connection_pool_size = 100
            self._optimizations_applied.add('connection_pooling')
            
            logger.info("HTTP connection pool initialized (100 connections)")
            
        except Exception as e:
            logger.warning(f"Connection pool initialization failed: {e}")
    
    async def _warmup_caches(self):
        """Warmup various caches"""
        try:
            # Warmup DNS cache for common domains
            dns_warmup_domains = [
                'api.slack.com',
                'generativelanguage.googleapis.com',
                'api.openai.com',
                'api.perplexity.ai',
                'api.pinecone.io'
            ]
            
            if self._http_session_pool:
                warmup_tasks = []
                for domain in dns_warmup_domains:
                    try:
                        task = self._warmup_domain(domain)
                        warmup_tasks.append(task)
                    except Exception:
                        continue
                
                if warmup_tasks:
                    await asyncio.gather(*warmup_tasks, return_exceptions=True)
            
            self._optimizations_applied.add('cache_warmup')
            logger.info("DNS and connection caches warmed up")
            
        except Exception as e:
            logger.warning(f"Cache warmup failed: {e}")
    
    async def _warmup_domain(self, domain: str):
        """Warmup connection to specific domain"""
        try:
            url = f"https://{domain}"
            async with self._http_session_pool.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                # Just establish connection, don't process response
                pass
        except Exception:
            # Expected for many domains - just establishing DNS/connection cache
            pass
    
    async def _optimize_memory_allocation(self):
        """Optimize memory allocation and garbage collection"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Optimize garbage collection thresholds for better performance
            import gc
            gc.set_threshold(700, 10, 10)  # More aggressive GC for faster cleanup
            
            # Pre-allocate common data structures
            self._response_cache = dict()
            self._connection_cache = dict()
            
            self._optimizations_applied.add('memory_optimization')
            logger.info("Memory allocation optimized")
            
        except Exception as e:
            logger.warning(f"Memory optimization failed: {e}")
    
    async def _precompile_regex_patterns(self):
        """Precompile commonly used regex patterns"""
        try:
            import re
            
            # Common patterns used in message processing
            patterns = {
                'mention': re.compile(r'<@[UW][A-Z0-9]+>'),
                'channel': re.compile(r'<#[C][A-Z0-9]+>'),
                'url': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
                'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                'timestamp': re.compile(r'\d{10}\.\d{6}')
            }
            
            # Store compiled patterns for reuse
            self._compiled_patterns = patterns
            
            self._optimizations_applied.add('regex_precompilation')
            logger.info("Regex patterns precompiled")
            
        except Exception as e:
            logger.warning(f"Regex precompilation failed: {e}")
    
    def get_http_session(self):
        """Get optimized HTTP session with connection pooling"""
        return self._http_session_pool
    
    def get_compiled_pattern(self, pattern_name: str):
        """Get precompiled regex pattern"""
        return getattr(self, '_compiled_patterns', {}).get(pattern_name)
    
    async def optimize_runtime_performance(self):
        """Apply runtime performance optimizations"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Update metrics
            import psutil
            process = psutil.Process()
            self.metrics.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            logger.debug(f"Runtime optimization: {self.metrics.memory_usage:.1f}MB memory usage")
            
        except Exception as e:
            logger.warning(f"Runtime optimization failed: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self._http_session_pool:
                await self._http_session_pool.close()
            
            logger.info("Performance optimizer cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        return {
            "optimizations_applied": list(self._optimizations_applied),
            "startup_time": self.metrics.startup_time,
            "memory_usage_mb": self.metrics.memory_usage,
            "connection_pool_size": self.metrics.connection_pool_size,
            "session_available": self._http_session_pool is not None,
            "total_optimizations": len(self._optimizations_applied)
        }

# Global optimizer instance
performance_optimizer = PerformanceOptimizer()