#!/usr/bin/env python3
"""
Test MCP Fixed Integration

Quick test to verify the MCP handshake fix works in production.
"""

import asyncio
import sys
sys.path.append('.')
from tools.atlassian_tool import AtlassianTool

async def test_mcp_fixed():
    """Test that the MCP integration now works with proper handshake"""
    
    print("🔧 TESTING FIXED MCP INTEGRATION")
    print("=" * 50)
    
    try:
        # Initialize the Atlassian tool
        print("1️⃣ Initializing Atlassian tool...")
        tool = AtlassianTool()
        
        if not tool.available:
            print("❌ Atlassian tool not available (credentials missing)")
            return False
        
        print("✅ Atlassian tool initialized successfully")
        
        # Test a simple confluence search
        print("\n2️⃣ Testing Confluence search...")
        result = await tool.execute_mcp_tool(
            "confluence_search",
            {
                "query": "Autopilot",
                "limit": 2
            }
        )
        
        print(f"Result keys: {list(result.keys())}")
        
        if "error" in result:
            print(f"❌ MCP tool execution failed: {result['error']}")
            print(f"   Message: {result.get('message', 'No details')}")
            return False
        
        if "success" in result and result["success"]:
            result_data = result.get("result", {})
            print(f"✅ MCP tool executed successfully")
            print(f"   Result type: {type(result_data)}")
            
            # Check if we got actual data
            if isinstance(result_data, list) and len(result_data) > 0:
                print(f"   Found {len(result_data)} results")
                for i, item in enumerate(result_data[:2]):
                    title = item.get("title", "No title")
                    url = item.get("url", "No URL")
                    print(f"   Result {i+1}: {title}")
                    print(f"   URL: {url}")
            elif isinstance(result_data, dict):
                print(f"   Got result dict with keys: {list(result_data.keys())}")
                # Try to extract text content
                if "text_content" in result_data:
                    text = result_data["text_content"]
                    print(f"   Text content length: {len(text)}")
                    if "Test Cloud" in text or "Autopilot" in text:
                        print("   ✅ Found UiPath content in response")
                    else:
                        print("   ⚠️ No expected UiPath content found")
            
            return True
        else:
            print(f"❌ Unexpected result format: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mcp_fixed())
    if result:
        print("\n✅ MCP INTEGRATION FIX SUCCESSFUL")
    else:
        print("\n❌ MCP INTEGRATION STILL HAS ISSUES")