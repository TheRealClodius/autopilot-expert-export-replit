#!/usr/bin/env python3
"""
Test deployment readiness and MCP server wake-up timing.
"""

import asyncio
import httpx
import time
from tools.atlassian_tool import AtlassianTool

async def test_deployment_readiness():
    """Test if MCP server is ready and responsive in deployment environment"""
    print("🚀 TESTING DEPLOYMENT READINESS")
    print("=" * 50)
    
    # Test 1: MCP Server Health Check
    print("Step 1: Testing MCP server health...")
    
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8001/healthz")
                if response.status_code == 200:
                    print(f"✅ MCP server healthy (attempt {attempt + 1})")
                    break
                else:
                    print(f"❌ MCP server returned {response.status_code} (attempt {attempt + 1})")
        except Exception as e:
            print(f"❌ MCP server connection failed (attempt {attempt + 1}): {e}")
            
        if attempt < max_attempts - 1:
            print(f"   Waiting 3 seconds before retry...")
            await asyncio.sleep(3)
    else:
        print("❌ MCP server failed all health checks")
        return False
    
    # Test 2: MCP Tool Initialization
    print("\nStep 2: Testing MCP tool initialization...")
    
    tool = AtlassianTool()
    if tool.available:
        print("✅ AtlassianTool initialized successfully")
    else:
        print("❌ AtlassianTool initialization failed")
        return False
    
    # Test 3: MCP Tool Execution with Retry
    print("\nStep 3: Testing MCP tool execution with retry...")
    
    max_tool_attempts = 5
    for attempt in range(max_tool_attempts):
        try:
            print(f"   Attempt {attempt + 1}: Testing confluence_search...")
            
            result = await tool.execute_mcp_tool('confluence_search', {
                'query': 'test deployment readiness',
                'limit': 1
            })
            
            if result.get('success'):
                print(f"✅ MCP tool execution successful (attempt {attempt + 1})")
                pages = result.get('result', [])
                print(f"   Found {len(pages)} results")
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"❌ MCP tool execution failed (attempt {attempt + 1}): {error_msg}")
                
        except Exception as e:
            print(f"❌ MCP tool exception (attempt {attempt + 1}): {e}")
            
        if attempt < max_tool_attempts - 1:
            print(f"   Waiting 5 seconds before retry...")
            await asyncio.sleep(5)
    
    print("❌ All MCP tool execution attempts failed")
    return False

async def test_production_environment():
    """Test in production-like environment conditions"""
    print("\n🌐 TESTING PRODUCTION ENVIRONMENT CONDITIONS")
    print("=" * 50)
    
    # Simulate cold start scenario
    print("Simulating cold start scenario...")
    
    # Wait for services to warm up
    await asyncio.sleep(10)
    
    # Test with production-like query
    tool = AtlassianTool()
    
    try:
        result = await asyncio.wait_for(
            tool.execute_mcp_tool('confluence_search', {
                'query': 'Autopilot for Everyone roadmap',
                'limit': 3
            }),
            timeout=30.0  # Production timeout
        )
        
        if result.get('success'):
            pages = result.get('result', [])
            print(f"✅ Production query successful: {len(pages)} results")
            return True
        else:
            print(f"❌ Production query failed: {result}")
            return False
            
    except asyncio.TimeoutError:
        print("❌ Production query timed out (30s)")
        return False
    except Exception as e:
        print(f"❌ Production query exception: {e}")
        return False

if __name__ == "__main__":
    async def run_tests():
        readiness_ok = await test_deployment_readiness()
        production_ok = await test_production_environment()
        
        print(f"\n{'=' * 50}")
        print("🎯 DEPLOYMENT READINESS SUMMARY")
        print(f"{'=' * 50}")
        print(f"Basic readiness: {'✅ PASS' if readiness_ok else '❌ FAIL'}")
        print(f"Production ready: {'✅ PASS' if production_ok else '❌ FAIL'}")
        
        if readiness_ok and production_ok:
            print("🚀 DEPLOYMENT READY")
        else:
            print("⚠️  DEPLOYMENT NEEDS FIXES")
    
    asyncio.run(run_tests())