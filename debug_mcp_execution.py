#!/usr/bin/env python3
"""
Debug MCP execution error specifically.
Test the exact scenario causing "execution error" in orchestrator.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool
import logging

logging.basicConfig(level=logging.INFO)

async def debug_mcp_execution_error():
    """Debug the specific MCP execution error"""
    print("🔧 DEBUGGING MCP EXECUTION ERROR")
    print("=" * 50)
    
    try:
        # Initialize the tool
        tool = AtlassianTool()
        print(f"✅ Tool initialized: {tool.available}")
        
        # Test server health first
        health = await tool.check_server_health()
        print(f"✅ Server health: {health}")
        
        # Test the exact MCP call that orchestrator would make
        print("\n🧪 Testing exact MCP call from orchestrator...")
        print("MCP Tool: confluence_search")
        print("Arguments: {'query': 'autopilot for everyone', 'limit': 10}")
        
        result = await tool.execute_mcp_tool(
            "confluence_search",
            {
                "query": "autopilot for everyone", 
                "limit": 10
            }
        )
        
        if result is None:
            print("❌ EXECUTION ERROR: Tool returned None")
            return False
        
        if isinstance(result, dict) and result.get("error"):
            print(f"❌ EXECUTION ERROR: {result.get('error')}")
            return False
        
        print(f"✅ SUCCESS: Tool execution completed")
        print(f"   Result type: {type(result)}")
        
        if isinstance(result, list):
            print(f"   Number of results: {len(result)}")
            for i, item in enumerate(result[:3], 1):
                title = item.get("title", "No title") if isinstance(item, dict) else str(item)
                print(f"   Result {i}: {title}")
        else:
            print(f"   Result: {str(result)[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(debug_mcp_execution_error())