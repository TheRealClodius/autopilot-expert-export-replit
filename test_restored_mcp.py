#!/usr/bin/env python3
"""
Test the restored MCP AtlassianTool to verify it's working correctly
"""
import asyncio
from tools.atlassian_tool import AtlassianTool

async def test_restored_mcp():
    """Test the restored MCP integration"""
    print("🔄 TESTING RESTORED MCP ATLASSIAN TOOL")
    print("-" * 50)
    
    try:
        # Initialize the tool
        tool = AtlassianTool()
        print(f"✅ Tool initialized successfully")
        print(f"   MCP Server URL: {tool.mcp_server_url}")
        print(f"   Available tools: {tool.available_tools}")
        
        # Test tool discovery
        print("\n1. Testing tool discovery...")
        available_tools = await tool.discover_available_tools()
        print(f"   Discovered {len(available_tools)} tools:")
        for tool_info in available_tools:
            print(f"     - {tool_info.get('name')}: {tool_info.get('description')}")
        
        # Test server health
        print("\n2. Testing server health...")
        health = await tool.check_server_health()
        print(f"   Server health: {'✅ Healthy' if health else '❌ Unhealthy'}")
        
        # Test actual MCP tool execution
        print("\n3. Testing MCP tool execution...")
        result = await tool.execute_mcp_tool("get_confluence_pages", {"query": "Autopilot"})
        print(f"   Execution result keys: {list(result.keys())}")
        
        if 'content' in result:
            content = result['content']
            if isinstance(content, list):
                print(f"   Found {len(content)} pages")
                for i, page in enumerate(content[:2]):
                    print(f"     Page {i+1}: {page.get('title', 'No title')}")
            elif isinstance(content, dict):
                pages = content.get('pages', [])
                print(f"   Found {len(pages)} pages in content dict")
                print(f"   Content keys: {list(content.keys())}")
                if content.get('message'):
                    print(f"   Message: {content['message']}")
        
        print("\n✅ MCP integration test completed successfully")
        
    except Exception as e:
        print(f"\n❌ Error testing MCP integration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_restored_mcp())