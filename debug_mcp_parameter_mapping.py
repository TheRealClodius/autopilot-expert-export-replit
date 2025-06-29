#!/usr/bin/env python3
"""
Debug MCP Parameter Mapping Issue

The MCP server is returning 'jql' is a required property, meaning our parameter 
mapping is incorrect. Let's identify what parameters are actually expected.
"""

import asyncio
import json
import httpx
from tools.atlassian_tool import AtlassianTool

async def debug_mcp_parameters():
    """Debug the MCP parameter mapping issue"""
    
    print("=" * 80)
    print("🔧 MCP PARAMETER MAPPING DIAGNOSIS")
    print("=" * 80)
    
    # Test what the orchestrator is sending vs what MCP expects
    test_scenarios = [
        {
            "name": "Current Orchestrator Format",
            "tool": "jira_search",
            "params": {
                "query": "Autopilot for Everyone",
                "limit": 10
            }
        },
        {
            "name": "JQL Format Test",
            "tool": "jira_search", 
            "params": {
                "jql": "text ~ \"Autopilot for Everyone\"",
                "limit": 10
            }
        },
        {
            "name": "Alternative JQL Format",
            "tool": "jira_search",
            "params": {
                "jql": "summary ~ \"Autopilot\" OR description ~ \"Autopilot\"",
                "maxResults": 10
            }
        },
        {
            "name": "Confluence Search Format",
            "tool": "confluence_search",
            "params": {
                "query": "Autopilot for Everyone",
                "limit": 10
            }
        }
    ]
    
    atlassian_tool = AtlassianTool()
    
    for scenario in test_scenarios:
        print(f"\n📝 Testing: {scenario['name']}")
        print(f"   Tool: {scenario['tool']}")
        print(f"   Parameters: {scenario['params']}")
        
        try:
            result = await atlassian_tool.execute_mcp_tool(
                scenario['tool'], 
                scenario['params']
            )
            
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                if "message" in result:
                    print(f"      Message: {result['message']}")
            else:
                print(f"   ✅ Success!")
                if "result" in result:
                    print(f"      Results: {len(result.get('result', []))} items")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Also test what happens when we call list_tools to see available tools
    print(f"\n🛠️ Checking Available MCP Tools:")
    try:
        tools = await atlassian_tool.list_tools()
        print(f"   Available tools: {tools}")
    except Exception as e:
        print(f"   ❌ Failed to list tools: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 PARAMETER MAPPING ANALYSIS")
    print("=" * 80)
    print("Based on the 'jql' error, the MCP server expects:")
    print("1. Jira tools need 'jql' parameter, not 'query'")
    print("2. May need 'maxResults' instead of 'limit'")
    print("3. Need to fix parameter conversion in orchestrator prompts")

if __name__ == "__main__":
    asyncio.run(debug_mcp_parameters())