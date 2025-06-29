#!/usr/bin/env python3
"""
Debug URL construction in AtlassianTool
"""
import asyncio
from tools.atlassian_tool import AtlassianTool

async def test_url_debug():
    """Test URL construction"""
    
    print("🔧 Testing URL Debug...")
    
    # Test AtlassianTool URL configuration
    tool = AtlassianTool()
    print(f"Tool MCP Server URL: {tool.mcp_server_url}")
    print(f"Tool available_tools: {tool.available_tools}")
    
    # Test URL construction in discover_available_tools
    print("\nTesting discover_available_tools URL construction:")
    tools = await tool.discover_available_tools()
    print(f"Discovered tools: {len(tools)}")
    print(f"Available tools after discovery: {tool.available_tools}")

if __name__ == "__main__":
    asyncio.run(test_url_debug())