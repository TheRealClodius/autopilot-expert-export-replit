#!/usr/bin/env python3
"""
Test MCP with detailed logging to identify exactly where it hangs
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

async def test_mcp_with_detailed_logging():
    """Test MCP with maximum logging detail"""
    print("🔧 TESTING MCP WITH DETAILED LOGGING")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        
        if not atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            return
        
        # Test with detailed step tracking
        print("\n🔍 Step-by-step MCP connection with logging")
        
        # Execute with timeout
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                "confluence_search",
                {"query": "test", "limit": 1}
            ),
            timeout=60.0  # 1 minute timeout
        )
        
        print(f"✅ Result received: {result}")
        
        # Clean up
        await atlassian_tool._cleanup_session()
        print("✅ Cleanup completed")
        
        return result
        
    except asyncio.TimeoutError:
        print("❌ Operation timed out after 60 seconds")
        return {"error": "timeout"}
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_mcp_with_detailed_logging())
    print(f"\nFinal result: {result}")