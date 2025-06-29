#!/usr/bin/env python3
"""
Test Clean MCP-Only Implementation
"""

import asyncio
import logging
import sys
from tools.atlassian_tool import AtlassianTool

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Enable MCP client logging
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("tools.atlassian_tool").setLevel(logging.DEBUG)

async def test_clean_mcp():
    """Test clean MCP-only implementation"""
    print("🔧 TESTING CLEAN MCP-ONLY IMPLEMENTATION")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        print(f"Available tools: {atlassian_tool.available_tools}")
        
        if not atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            return
        
        # Test with timeout
        print("\n🔍 Testing Confluence search...")
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                "confluence_search",
                {"query": "template", "limit": 2}
            ),
            timeout=90.0  # 1.5 minute timeout
        )
        
        print(f"✅ Confluence search result: {result}")
        
        # Clean up
        await atlassian_tool._cleanup_session()
        print("✅ Cleanup completed")
        
        return result
        
    except asyncio.TimeoutError:
        print("❌ Operation timed out after 90 seconds")
        return {"error": "timeout"}
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_clean_mcp())
    print(f"\nFinal result: {result}")