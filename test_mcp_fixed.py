#!/usr/bin/env python3
"""
Test MCP with Fixed Endpoints

This script tests the MCP connection with corrected endpoints (/mcp/sse)
and proper headers to verify the fix works.
"""

import asyncio
import httpx
from tools.atlassian_tool import AtlassianTool

async def test_mcp_fixed():
    """Test MCP connection with fixed endpoints"""
    print("🔧 Testing MCP with Fixed Endpoints")
    print("=" * 50)
    
    # Test 1: Check correct SSE endpoint with proper headers
    print("\n1. Testing SSE Endpoint with Proper Headers:")
    try:
        headers = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8001/mcp/sse", headers=headers)
            print(f"✅ SSE Endpoint: {response.status_code}")
            
            if response.status_code == 200:
                # Parse SSE response
                lines = response.text.strip().split('\n')
                print(f"   SSE Response Lines: {len(lines)}")
                for i, line in enumerate(lines[:5]):  # Show first 5 lines
                    print(f"   Line {i}: {line}")
            else:
                print(f"   Error: {response.text}")
                
    except Exception as e:
        print(f"❌ SSE Endpoint Error: {e}")
    
    # Test 2: Initialize AtlassianTool with fixed endpoints
    print("\n2. Testing AtlassianTool Initialization:")
    try:
        tool = AtlassianTool()
        print(f"✅ AtlassianTool created")
        print(f"   MCP Server URL: {tool.mcp_server_url}")
        print(f"   SSE Endpoint: {tool.sse_endpoint}")
        print(f"   Available: {tool.available}")
        print(f"   Available Tools: {tool.available_tools}")
        
    except Exception as e:
        print(f"❌ AtlassianTool Error: {e}")
        return
    
    # Test 3: Try actual MCP tool execution
    print("\n3. Testing MCP Tool Execution:")
    try:
        # Test confluence search
        result = await tool.execute_mcp_tool(
            "confluence_search", 
            {"query": "Autopilot", "limit": 3}
        )
        
        print(f"✅ MCP Tool Execution Successful")
        print(f"   Result type: {type(result)}")
        
        if isinstance(result, dict) and 'result' in result:
            search_results = result['result']
            if isinstance(search_results, list):
                print(f"   Found {len(search_results)} results")
                for i, page in enumerate(search_results[:2]):
                    title = page.get('title', 'No title')
                    url = page.get('url', 'No URL')
                    print(f"   {i+1}. {title}")
                    print(f"      URL: {url}")
            else:
                print(f"   Result: {search_results}")
        else:
            print(f"   Raw result: {result}")
            
    except Exception as e:
        print(f"❌ MCP Tool Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_fixed())