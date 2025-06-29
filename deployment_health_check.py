#!/usr/bin/env python3
"""
Deployment Health Check - Comprehensive system to verify all services are ready
"""

import asyncio
import httpx
import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DeploymentHealthChecker:
    """Comprehensive health checking for deployment environments"""
    
    def __init__(self):
        self.checks = [
            ("MCP Server Health", self._check_mcp_health),
            ("MCP Tool Functionality", self._check_mcp_tools),
            ("Atlassian Connectivity", self._check_atlassian_connectivity),
            ("Memory Service", self._check_memory_service),
            ("Vector Search", self._check_vector_search),
        ]
        
    async def _check_mcp_health(self) -> tuple[bool, str]:
        """Check MCP server health endpoint"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8001/healthz")
                if response.status_code == 200:
                    return True, "MCP server healthy"
                else:
                    return False, f"MCP server returned {response.status_code}"
        except Exception as e:
            return False, f"MCP server unreachable: {e}"
    
    async def _check_mcp_tools(self) -> tuple[bool, str]:
        """Check MCP tool functionality"""
        try:
            from tools.atlassian_tool import AtlassianTool
            
            tool = AtlassianTool()
            if not tool.available:
                return False, "AtlassianTool not available"
            
            # Test basic functionality with minimal query
            result = await asyncio.wait_for(
                tool.execute_mcp_tool('confluence_search', {
                    'query': 'test',
                    'limit': 1
                }),
                timeout=15.0
            )
            
            if result.get('success'):
                return True, "MCP tools functional"
            else:
                return False, f"MCP tool test failed: {result.get('error', 'Unknown error')}"
                
        except asyncio.TimeoutError:
            return False, "MCP tool test timed out"
        except Exception as e:
            return False, f"MCP tool test error: {e}"
    
    async def _check_atlassian_connectivity(self) -> tuple[bool, str]:
        """Check Atlassian API connectivity"""
        try:
            # Check if credentials are available
            import os
            jira_url = os.getenv("ATLASSIAN_JIRA_URL")
            confluence_url = os.getenv("ATLASSIAN_CONFLUENCE_URL")
            
            if not jira_url or not confluence_url:
                return False, "Atlassian credentials not configured"
            
            return True, "Atlassian credentials available"
        except Exception as e:
            return False, f"Atlassian check error: {e}"
    
    async def _check_memory_service(self) -> tuple[bool, str]:
        """Check memory service functionality"""
        try:
            from services.memory_service import MemoryService
            
            memory_service = MemoryService()
            # Test basic memory operations
            test_key = f"health_check_{int(time.time())}"
            test_data = {"test": "data"}
            
            await memory_service.store_conversation_context(test_key, test_data, ttl=60)
            retrieved = await memory_service.get_conversation_context(test_key)
            
            if retrieved:
                return True, "Memory service functional"
            else:
                return False, "Memory service store/retrieve failed"
                
        except Exception as e:
            return False, f"Memory service error: {e}"
    
    async def _check_vector_search(self) -> tuple[bool, str]:
        """Check vector search availability"""
        try:
            from tools.vector_search import VectorSearchTool
            
            vector_tool = VectorSearchTool()
            if vector_tool.is_available():
                return True, "Vector search available"
            else:
                return False, "Vector search not available"
                
        except Exception as e:
            return False, f"Vector search error: {e}"
    
    async def run_all_checks(self) -> Dict[str, tuple[bool, str]]:
        """Run all health checks and return results"""
        results = {}
        
        logger.info("Running deployment health checks...")
        
        for check_name, check_func in self.checks:
            try:
                start_time = time.time()
                success, message = await check_func()
                duration = time.time() - start_time
                
                results[check_name] = (success, message)
                status = "✅ PASS" if success else "❌ FAIL"
                logger.info(f"{status} {check_name}: {message} ({duration:.2f}s)")
                
            except Exception as e:
                results[check_name] = (False, f"Check failed: {e}")
                logger.error(f"❌ FAIL {check_name}: Check failed: {e}")
        
        return results
    
    async def wait_for_readiness(self, max_wait_time: int = 120, check_interval: int = 5) -> bool:
        """Wait for all systems to be ready"""
        logger.info(f"Waiting for deployment readiness (max {max_wait_time}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            results = await self.run_all_checks()
            
            # Check if all critical checks pass
            critical_checks = ["MCP Server Health", "MCP Tool Functionality"]
            all_critical_pass = all(
                results.get(check, (False, ""))[0] 
                for check in critical_checks
            )
            
            if all_critical_pass:
                elapsed = time.time() - start_time
                logger.info(f"🎯 Deployment ready after {elapsed:.1f}s")
                return True
            
            logger.info(f"Waiting for readiness... ({time.time() - start_time:.1f}s elapsed)")
            await asyncio.sleep(check_interval)
        
        logger.error(f"❌ Deployment not ready after {max_wait_time}s")
        return False
    
    def get_readiness_status(self, results: Dict[str, tuple[bool, str]]) -> Dict[str, any]:
        """Get comprehensive readiness status"""
        total_checks = len(results)
        passed_checks = sum(1 for success, _ in results.values() if success)
        
        critical_checks = ["MCP Server Health", "MCP Tool Functionality"]
        critical_passed = sum(
            1 for check in critical_checks 
            if results.get(check, (False, ""))[0]
        )
        
        return {
            "ready": critical_passed == len(critical_checks),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "critical_passed": critical_passed,
            "critical_total": len(critical_checks),
            "details": results
        }

# Global health checker instance
health_checker = DeploymentHealthChecker()

async def verify_deployment_ready() -> bool:
    """Quick deployment readiness verification"""
    return await health_checker.wait_for_readiness(max_wait_time=30, check_interval=3)

if __name__ == "__main__":
    async def main():
        results = await health_checker.run_all_checks()
        status = health_checker.get_readiness_status(results)
        
        print(f"\n{'='*50}")
        print("DEPLOYMENT HEALTH CHECK SUMMARY")
        print(f"{'='*50}")
        print(f"Overall Status: {'✅ READY' if status['ready'] else '❌ NOT READY'}")
        print(f"Checks Passed: {status['passed_checks']}/{status['total_checks']}")
        print(f"Critical Passed: {status['critical_passed']}/{status['critical_total']}")
        
    asyncio.run(main())