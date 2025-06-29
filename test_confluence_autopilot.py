#!/usr/bin/env python3
"""
Test Confluence search for Autopilot for Everyone project
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_confluence_autopilot():
    """Test Confluence search for Autopilot for Everyone"""
    print("🔍 Testing Confluence search for Autopilot for Everyone project...")
    
    tool = AtlassianTool()
    
    # Check tool availability
    print(f"✅ Tool available: {tool.available}")
    
    # Check server health
    health = await tool.check_server_health()
    print(f"✅ MCP server health: {health}")
    
    if not health:
        print("❌ MCP server not healthy, cannot proceed")
        return
    
    # Test simple confluence search for "Autopilot for Everyone"
    print("\n🔍 Searching Confluence for 'Autopilot for Everyone'...")
    try:
        result = await tool.execute_mcp_tool(
            "confluence_search",
            {
                "query": "Autopilot for Everyone",
                "max_results": 10
            }
        )
        
        print(f"📋 Search result: {result}")
        
        if result.get("success"):
            search_results = result.get("result", {})
            if isinstance(search_results, list):
                print(f"✅ Found {len(search_results)} pages")
                for i, page in enumerate(search_results[:3]):
                    print(f"  {i+1}. {page.get('title', 'Unknown Title')}")
            elif isinstance(search_results, dict):
                if "text_content" in search_results:
                    print(f"✅ Text result: {search_results['text_content'][:200]}...")
                else:
                    print(f"✅ Dict result with keys: {list(search_results.keys())}")
        else:
            print(f"❌ Search failed: {result}")
            
    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_confluence_autopilot())