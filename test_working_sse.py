#!/usr/bin/env python3
"""
Test Working SSE Implementation
"""

import asyncio
import logging
import sys
from tools.atlassian_tool import AtlassianTool

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_working_sse():
    """Test working SSE implementation"""
    print("🔧 TESTING WORKING SSE IMPLEMENTATION")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        
        if not atlassian_tool.available:
            print("❌ Missing credentials")
            return {"error": "missing_credentials"}
        
        # Test with reasonable timeout
        print("🔍 Testing Confluence search...")
        result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool(
                "confluence_search",
                {"query": "template", "limit": 1}
            ),
            timeout=90.0
        )
        
        print(f"✅ Result: {result}")
        return result
        
    except asyncio.TimeoutError:
        print("❌ Timeout after 90 seconds")
        return {"error": "timeout"}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_working_sse())
    print(f"\nFinal result: {result}")