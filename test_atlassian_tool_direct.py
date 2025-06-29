#!/usr/bin/env python3
"""
Direct AtlassianTool Test

Test the AtlassianTool directly to isolate the connection issue.
"""

import asyncio
import sys
from tools.atlassian_tool import AtlassianTool

async def test_atlassian_tool():
    """Test AtlassianTool with a simple search"""
    
    print("🧪 ATLASSIAN TOOL DIRECT TEST")
    print("=" * 50)
    
    # Initialize the tool
    print("1. Initializing AtlassianTool...")
    try:
        tool = AtlassianTool()
        print("   ✅ AtlassianTool initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    # Test MCP tool call
    print("\n2. Testing MCP tool call...")
    try:
        result = await tool.execute_mcp_tool(
            tool_name="confluence_search",
            arguments={
                "query": "autopilot",
                "limit": 3
            }
        )
        
        print(f"   Result type: {type(result)}")
        print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and "error" in result:
            print(f"   ❌ Tool call failed: {result['error']} - {result.get('message', '')}")
            return False
        else:
            print("   ✅ Tool call successful")
            
            # Show some result details
            if isinstance(result, dict) and "result" in result:
                tool_result = result.get("result", {})
                if isinstance(tool_result, dict) and "result" in tool_result:
                    pages = tool_result.get("result", [])
                    print(f"   Found {len(pages)} pages")
                    for i, page in enumerate(pages[:2]):  # Show first 2
                        title = page.get("title", "No title")
                        url = page.get("url", "No URL")
                        print(f"     {i+1}. {title}")
                        print(f"        URL: {url}")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Tool call exception: {e}")
        print(f"   Exception type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_atlassian_tool())
    print("\n" + "=" * 50)
    if success:
        print("✅ ATLASSIAN TOOL TEST PASSED")
    else:
        print("❌ ATLASSIAN TOOL TEST FAILED")
    sys.exit(0 if success else 1)