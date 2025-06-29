#!/usr/bin/env python3
"""
Startup Coordinator - Ensures proper service startup sequencing for deployment.
"""

import asyncio
import httpx
import time
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StartupCoordinator:
    """Coordinates startup of MCP server and FastAPI application"""
    
    def __init__(self):
        self.mcp_health_url = "http://localhost:8001/healthz"
        self.max_startup_wait = 120  # 2 minutes max startup time
        self.health_check_interval = 3  # Check every 3 seconds
        
    async def wait_for_mcp_server(self):
        """Wait for MCP server to be healthy before proceeding"""
        logger.info("Waiting for MCP Atlassian server to start...")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < self.max_startup_wait:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(self.mcp_health_url)
                    if response.status_code == 200:
                        logger.info(f"✅ MCP server healthy after {attempt} attempts ({time.time() - start_time:.1f}s)")
                        return True
                    else:
                        logger.warning(f"MCP server returned {response.status_code} (attempt {attempt})")
            except Exception as e:
                logger.debug(f"MCP server not ready (attempt {attempt}): {e}")
                
            await asyncio.sleep(self.health_check_interval)
        
        logger.error(f"❌ MCP server failed to start within {self.max_startup_wait}s")
        return False
    
    async def verify_mcp_functionality(self):
        """Verify MCP server is fully functional"""
        logger.info("Verifying MCP server functionality...")
        
        try:
            from tools.atlassian_tool import AtlassianTool
            
            tool = AtlassianTool()
            if not tool.available:
                logger.error("❌ AtlassianTool not available")
                return False
            
            # Test basic MCP functionality
            result = await tool.execute_mcp_tool('confluence_search', {
                'query': 'startup test',
                'limit': 1
            })
            
            if result.get('success'):
                logger.info("✅ MCP server fully functional")
                return True
            else:
                logger.error(f"❌ MCP functionality test failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ MCP functionality verification failed: {e}")
            return False
    
    async def start_services(self):
        """Start services in proper sequence"""
        logger.info("🚀 Starting coordinated service startup...")
        
        # Step 1: Verify MCP server is running and healthy
        if not await self.wait_for_mcp_server():
            logger.error("Failed to start - MCP server not responding")
            return False
        
        # Step 2: Verify full MCP functionality
        if not await self.verify_mcp_functionality():
            logger.error("Failed to start - MCP server not functional")
            return False
        
        # Step 3: Start FastAPI server
        logger.info("✅ All dependencies ready, starting FastAPI server...")
        return True

async def main():
    """Main startup coordination"""
    coordinator = StartupCoordinator()
    
    if await coordinator.start_services():
        logger.info("🎯 All services ready - starting main application")
        
        # Import and start the main FastAPI application
        import uvicorn
        from main import app
        
        # Start FastAPI with production settings
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0", 
            port=5000,
            log_level="info",
            reload=False
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    else:
        logger.error("❌ Service startup failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())