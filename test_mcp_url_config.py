#!/usr/bin/env python3
"""
Test MCP URL Configuration Fix

Test the deployment-aware URL configuration to ensure it works correctly.
"""

import asyncio
import os
from tools.atlassian_tool import AtlassianTool

async def test_mcp_url_config():
    """Test MCP URL configuration with deployment detection"""
    
    print("=" * 70)
    print("🔧 TESTING MCP URL CONFIGURATION FIX")
    print("=" * 70)
    
    # Show current environment
    print("🌍 Environment Variables:")
    print(f"   REPLIT_DOMAINS = {os.getenv('REPLIT_DOMAINS', '<not set>')}")
    print(f"   MCP_SERVER_URL = {os.getenv('MCP_SERVER_URL', '<not set>')}")
    
    # Test AtlassianTool URL selection
    print(f"\n🛠️ Testing AtlassianTool URL Configuration:")
    
    try:
        # Create AtlassianTool instance
        atlassian_tool = AtlassianTool()
        
        print(f"   Selected MCP URL: {atlassian_tool.mcp_server_url}")
        print(f"   SSE Endpoint: {atlassian_tool.sse_endpoint}")
        
        # Test basic tool execution
        print(f"\n⚡ Testing Basic Tool Execution:")
        
        result = await atlassian_tool.execute_mcp_tool("confluence_search", {
            "query": "Autopilot deployment test",
            "limit": 3
        })
        
        if "error" in result:
            print(f"   ❌ Tool execution failed: {result['error']}")
            if "message" in result:
                print(f"      Details: {result['message']}")
        else:
            print(f"   ✅ Tool execution successful!")
            if "result" in result and isinstance(result["result"], list):
                print(f"      Retrieved {len(result['result'])} results")
                if result["result"]:
                    first_result = result["result"][0]
                    title = first_result.get("title", "No title")
                    print(f"      First result: {title}")
                    
    except Exception as e:
        print(f"   ❌ Exception during testing: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("🎯 URL CONFIGURATION TEST COMPLETE")
    print("=" * 70)
    
    print("\nExpected Results:")
    print("✅ URL should be correctly configured for deployment environment")
    print("✅ Tool execution should work without SSE session errors")
    print("✅ Should retrieve authentic UiPath Confluence data")

if __name__ == "__main__":
    asyncio.run(test_mcp_url_config())