#!/usr/bin/env python3
"""
Test MCP with Localhost URL

Test MCP connection using localhost:8001 instead of mcp-atlassian-server:8001
"""

import asyncio
import os
os.environ["MCP_SERVER_URL"] = "http://localhost:8001"  # Override for test

from tools.atlassian_tool import AtlassianTool

async def test_mcp_localhost():
    """Test MCP connection with localhost URL"""
    print("🔧 Testing MCP with Localhost URL")
    print("=" * 50)
    
    # Create tool with localhost URL
    tool = AtlassianTool()
    print(f"✅ AtlassianTool created")
    print(f"   MCP Server URL: {tool.mcp_server_url}")
    print(f"   SSE Endpoint: {tool.sse_endpoint}")
    print(f"   Available: {tool.available}")
    
    # Test MCP tool execution
    print("\n🔍 Testing Confluence Search:")
    try:
        result = await tool.execute_mcp_tool(
            "confluence_search", 
            {"query": "Autopilot for Everyone", "limit": 2}
        )
        
        print(f"✅ MCP Tool Execution Successful")
        
        if isinstance(result, dict) and 'result' in result:
            search_results = result['result']
            if isinstance(search_results, list):
                print(f"   Found {len(search_results)} Autopilot pages:")
                for i, page in enumerate(search_results):
                    title = page.get('title', 'No title')
                    url = page.get('url', 'No URL')
                    space = page.get('space', {}).get('name', 'Unknown space')
                    print(f"   {i+1}. {title}")
                    print(f"      Space: {space}")
                    print(f"      URL: {url}")
            else:
                print(f"   Result: {search_results}")
        else:
            print(f"   Error result: {result}")
            
    except Exception as e:
        print(f"❌ MCP Tool Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_localhost())