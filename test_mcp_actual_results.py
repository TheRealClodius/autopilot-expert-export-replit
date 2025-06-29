#!/usr/bin/env python3
"""
Test MCP Actual Results - Verify we get real data back from MCP tool calls
"""

import asyncio
import json
from tools.atlassian_tool import AtlassianTool

async def test_mcp_actual_execution():
    """Test actual MCP tool execution and result parsing"""
    print("🔧 TESTING ACTUAL MCP TOOL EXECUTION")
    print("=" * 50)
    
    try:
        # Initialize tool
        atlassian_tool = AtlassianTool()
        
        print(f"Tool available: {atlassian_tool.available}")
        print(f"Available MCP tools: {atlassian_tool.available_tools}")
        
        if not atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            return
        
        # Test 1: Simple Confluence search
        print("\n🔍 Test 1: Confluence Search")
        print("Query: 'Autopilot for Everyone'")
        
        result1 = await atlassian_tool.execute_mcp_tool(
            "confluence_search",
            {"query": "Autopilot for Everyone", "limit": 3}
        )
        
        print(f"Result type: {type(result1)}")
        print(f"Result keys: {list(result1.keys()) if isinstance(result1, dict) else 'Not a dict'}")
        
        if result1.get("error"):
            print(f"❌ Error: {result1['error']}")
        else:
            print("✅ Success!")
            print(f"Response time: {result1.get('response_time', 'N/A')}s")
            print(f"MCP tool: {result1.get('mcp_tool', 'N/A')}")
            
            # Check for actual content
            if 'pages' in result1:
                pages = result1['pages']
                print(f"📄 Found {len(pages)} pages:")
                for i, page in enumerate(pages[:2], 1):  # Show first 2
                    print(f"   {i}. {page.get('title', 'No title')}")
                    print(f"      ID: {page.get('id', 'N/A')}")
                    print(f"      Space: {page.get('space', {}).get('name', 'N/A')}")
            elif 'results' in result1:
                results = result1['results']
                print(f"📄 Found {len(results)} results:")
                for i, result in enumerate(results[:2], 1):
                    print(f"   {i}. {result.get('title', 'No title')}")
            elif 'text' in result1:
                text = result1['text']
                print(f"📄 Text response: {text[:200]}...")
            else:
                print(f"📄 Full result structure:")
                print(json.dumps(result1, indent=2)[:500] + "...")
        
        # Test 2: Jira search
        print("\n🎫 Test 2: Jira Search")
        print("JQL: 'project = AUTOPILOT AND status != Done'")
        
        result2 = await atlassian_tool.execute_mcp_tool(
            "jira_search",
            {"jql": "project = AUTOPILOT AND status != Done", "max_results": 3}
        )
        
        if result2.get("error"):
            print(f"❌ Error: {result2['error']}")
        else:
            print("✅ Success!")
            print(f"Response time: {result2.get('response_time', 'N/A')}s")
            
            # Check for actual issues
            if 'issues' in result2:
                issues = result2['issues']
                print(f"🎫 Found {len(issues)} issues:")
                for i, issue in enumerate(issues[:2], 1):
                    print(f"   {i}. {issue.get('key', 'No key')}: {issue.get('fields', {}).get('summary', 'No summary')}")
            else:
                print(f"🎫 Result keys: {list(result2.keys())}")
        
        # Clean up
        await atlassian_tool._cleanup_session()
        print("\n✅ Session cleaned up")
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_actual_execution())