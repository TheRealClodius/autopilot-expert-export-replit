#!/usr/bin/env python3
"""
Test SSE Implementation of Atlassian Tool
"""

import asyncio
import logging
import sys
from tools.atlassian_tool_sse import AtlassianToolSSE

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_sse_implementation():
    """Test SSE-based MCP implementation"""
    print("🔧 TESTING SSE IMPLEMENTATION")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianToolSSE()
        
        print(f"Tool available: {atlassian_tool.available}")
        print(f"Available tools: {atlassian_tool.available_tools}")
        
        if not atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            return
        
        # Test using async context manager
        async with atlassian_tool:
            print("\n🔍 Testing Confluence search via SSE...")
            result = await asyncio.wait_for(
                atlassian_tool.execute_mcp_tool(
                    "confluence_search",
                    {"query": "template", "limit": 2}
                ),
                timeout=120.0  # 2 minute timeout for server startup
            )
            
            print(f"✅ SSE Result: {result}")
            return result
        
    except asyncio.TimeoutError:
        print("❌ Operation timed out after 2 minutes")
        return {"error": "timeout"}
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_sse_implementation())
    print(f"\nFinal result: {result}")