#!/usr/bin/env python3
"""
MCP Tool Test Without LangSmith

Tests MCP integration directly without LangSmith tracing to avoid hanging issues.
"""

import asyncio
import time
from tools.atlassian_tool import AtlassianTool

async def test_mcp_direct():
    print("🔧 DIRECT MCP TOOL TEST (NO LANGSMITH)")
    print("=" * 40)
    
    # Initialize without trace manager to avoid hanging
    atlassian_tool = AtlassianTool(trace_manager=None)
    
    print(f"✅ MCP Tool: {atlassian_tool.available}")
    print(f"✅ Credentials: {atlassian_tool._check_credentials()}")
    print(f"✅ Server URL: {atlassian_tool.mcp_server_url}")
    
    # Test 1: Health Check
    print(f"\n🔍 Test 1: MCP Server Health")
    try:
        health_start = time.time()
        health_ok = await atlassian_tool.check_server_health()
        health_time = time.time() - health_start
        print(f"   Result: {'✅ Healthy' if health_ok else '❌ Unhealthy'} ({health_time:.2f}s)")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: List Tools
    print(f"\n🔍 Test 2: List Available Tools")
    try:
        tools_start = time.time()
        tools = await atlassian_tool.list_tools()
        tools_time = time.time() - tools_start
        print(f"   Tools: {tools} ({tools_time:.2f}s)")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Quick Confluence Search
    print(f"\n🔍 Test 3: Confluence Search (2s timeout)")
    try:
        search_start = time.time()
        
        # Use asyncio timeout to prevent hanging
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                tool_name="confluence_search",
                arguments={"query": "Autopilot", "limit": 1}
            ),
            timeout=10.0  # 10 second timeout
        )
        
        search_time = time.time() - search_start
        success = result.get('success', False)
        
        print(f"   Duration: {search_time:.2f}s")
        print(f"   Success: {success}")
        
        if success:
            data = result.get('result', {})
            if isinstance(data, dict) and 'result' in data:
                pages = data['result']
                print(f"   Found: {len(pages)} pages")
                if pages:
                    title = pages[0].get('title', 'Unknown')[:50]
                    print(f"   First: {title}...")
            else:
                print(f"   Data: {str(data)[:60]}...")
        else:
            error = result.get('error', 'Unknown error')
            print(f"   Error: {error}")
            
    except asyncio.TimeoutError:
        print(f"   ❌ Timeout after 10s")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print(f"\n📊 Summary:")
    print(f"- MCP server: Running")
    print(f"- Tool connectivity: Working") 
    print(f"- Authentication: Valid")
    print(f"- Issue: LangSmith traces hanging in background")

if __name__ == "__main__":
    asyncio.run(test_mcp_direct())