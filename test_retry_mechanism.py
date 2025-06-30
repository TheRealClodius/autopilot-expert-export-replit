#!/usr/bin/env python3
"""
Test script to verify the tenacity retry mechanism for MCP server connections.
Tests network resilience and failure recovery.
"""

import asyncio
import logging
import time
from tools.atlassian_tool import AtlassianTool
from config import settings

# Set up logging to see retry attempts
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_retry_mechanism():
    """Test the retry mechanism under various network conditions"""
    
    print("🔄 Testing Tenacity Retry Mechanism for MCP Server")
    print("=" * 60)
    
    # Test 1: Normal operation (should work without retries)
    print("\n1. Testing normal operation...")
    try:
        tool = AtlassianTool()
        start_time = time.time()
        health_status = await tool.check_server_health()
        duration = time.time() - start_time
        print(f"   ✅ Health check: {'PASS' if health_status else 'FAIL'} ({duration:.2f}s)")
        await tool.close()
    except Exception as e:
        print(f"   ❌ Normal operation failed: {e}")
    
    # Test 2: Tool discovery with retry
    print("\n2. Testing tool discovery with retry protection...")
    try:
        tool = AtlassianTool()
        start_time = time.time()
        tools = await tool.discover_available_tools()
        duration = time.time() - start_time
        print(f"   ✅ Discovered {len(tools)} tools ({duration:.2f}s)")
        print(f"   Available Atlassian tools: {tool.available_tools}")
        await tool.close()
    except Exception as e:
        print(f"   ❌ Tool discovery failed: {e}")
    
    # Test 3: MCP tool execution with retry
    print("\n3. Testing MCP tool execution with retry protection...")
    try:
        tool = AtlassianTool()
        if tool.available:
            start_time = time.time()
            result = await tool.execute_mcp_tool(
                "get_confluence_pages",
                {"query": "autopilot", "limit": 1}
            )
            duration = time.time() - start_time
            
            if "error" not in result:
                print(f"   ✅ MCP tool execution successful ({duration:.2f}s)")
                print(f"   Result type: {type(result)}")
            else:
                print(f"   ⚠️  MCP tool returned error: {result.get('error')}")
        else:
            print("   ⚠️  Atlassian credentials not configured - skipping tool execution test")
        await tool.close()
    except Exception as e:
        print(f"   ❌ MCP tool execution failed: {e}")
    
    # Test 4: Test with invalid URL to verify retry behavior
    print("\n4. Testing retry behavior with invalid server URL...")
    try:
        # Temporarily modify the MCP server URL to test retry behavior
        original_url = settings.MCP_SERVER_URL
        settings.MCP_SERVER_URL = "https://invalid-mcp-server-url.example.com"
        
        tool = AtlassianTool()
        start_time = time.time()
        
        try:
            health_status = await tool.check_server_health()
            duration = time.time() - start_time
            print(f"   📊 Failed as expected after retries ({duration:.2f}s)")
            print(f"   Health status: {health_status}")
        except Exception as e:
            duration = time.time() - start_time
            print(f"   📊 Retries exhausted as expected ({duration:.2f}s)")
            print(f"   Final exception: {type(e).__name__}: {e}")
        
        # Restore original URL
        settings.MCP_SERVER_URL = original_url
        await tool.close()
        
    except Exception as e:
        print(f"   ⚠️  Error in retry test setup: {e}")
        # Restore original URL in case of error
        settings.MCP_SERVER_URL = original_url
    
    print("\n🏁 Retry mechanism testing completed!")
    print("\nExpected behavior:")
    print("- Normal operations should complete quickly without retries")
    print("- Network failures should trigger 3 retry attempts with exponential backoff")
    print("- Retry delays should be: ~1s, ~2s, ~4s before final failure")
    print("- Tenacity logs should show retry attempts with WARNING level")

if __name__ == "__main__":
    asyncio.run(test_retry_mechanism())