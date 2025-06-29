#!/usr/bin/env python3
"""
Test MCP with Environment Variables Configuration
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

async def test_mcp_env_vars():
    """Test MCP with environment variables configuration"""
    print("🔧 TESTING MCP WITH ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        
        if not atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            return
        
        # Test with timeout
        print("\n🔍 Testing Confluence search with env vars...")
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                "confluence_search",
                {"query": "template", "limit": 1}
            ),
            timeout=90.0  # 1.5 minute timeout
        )
        
        print(f"✅ Result: {result}")
        
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
    result = asyncio.run(test_mcp_env_vars())
    print(f"\nFinal result: {result}")