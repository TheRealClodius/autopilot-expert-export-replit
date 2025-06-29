#!/usr/bin/env python3
"""
Test HTTP MCP Integration

Tests the HTTP-based AtlassianTool connecting to the running MCP server.
"""

import asyncio
import logging
import sys
from tools.atlassian_tool import AtlassianTool

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_http_mcp_integration():
    """Test HTTP-based MCP integration"""
    print("🔧 TESTING HTTP MCP INTEGRATION")
    print("=" * 50)
    
    try:
        # Initialize HTTP-based tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        print(f"Available tools: {atlassian_tool.available_tools}")
        
        if not atlassian_tool.available:
            print("❌ Missing credentials")
            return {"error": "missing_credentials"}
        
        # Test server health first
        print("🏥 Checking MCP server health...")
        health_ok = await atlassian_tool.check_server_health()
        print(f"Health check: {'✅ OK' if health_ok else '❌ Failed'}")
        
        if not health_ok:
            return {"error": "server_health_failed"}
        
        # Test Confluence search
        print("🔍 Testing Confluence search...")
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                "confluence_search",
                {"query": "template", "limit": 2}
            ),
            timeout=30.0
        )
        
        print(f"✅ Result: {result}")
        return result
        
    except asyncio.TimeoutError:
        print("❌ Timeout after 30 seconds")
        return {"error": "timeout"}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_http_mcp_integration())
    print(f"\nFinal result: {result}")