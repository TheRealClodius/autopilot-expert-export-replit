#!/usr/bin/env python3
"""
Test MCP with verbose debugging enabled
"""

import asyncio
import logging
import sys
import os
from tools.atlassian_tool import AtlassianTool

# Set MCP debugging environment variables
os.environ["MCP_VERY_VERBOSE"] = "true"
os.environ["MCP_LOGGING_STDOUT"] = "true"

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Enable MCP client logging
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("tools.atlassian_tool").setLevel(logging.DEBUG)
logging.getLogger("fastmcp").setLevel(logging.DEBUG)

async def test_mcp_verbose():
    """Test MCP with verbose debugging"""
    print("🔧 TESTING MCP WITH VERBOSE DEBUGGING")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        
        if not atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            return
        
        # Test with shorter timeout to avoid long hangs
        print("\n🔍 Testing with verbose MCP logging...")
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                "confluence_search",
                {"query": "test", "limit": 1}
            ),
            timeout=60.0  # 1 minute timeout
        )
        
        print(f"✅ Result: {result}")
        
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
    result = asyncio.run(test_mcp_verbose())
    print(f"\nFinal result: {result}")