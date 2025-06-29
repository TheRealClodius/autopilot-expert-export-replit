#!/usr/bin/env python3
"""
Quick MCP Parameter Fix Verification

Quick test to verify if the orchestrator parameter fix resolves the validation issue.
"""

import asyncio
from tools.atlassian_tool import AtlassianTool

async def test_parameter_formats():
    """Test both parameter formats to ensure they work"""
    
    print("=" * 60)
    print("🔧 QUICK MCP PARAMETER VERIFICATION")
    print("=" * 60)
    
    atlassian_tool = AtlassianTool()
    
    # Test the exact formats that the orchestrator should now generate
    test_scenarios = [
        {
            "name": "Jira Search (Fixed Format)",
            "tool": "jira_search",
            "params": {
                "jql": "text ~ \"Autopilot\" OR summary ~ \"Autopilot\"",
                "limit": 10
            }
        },
        {
            "name": "Confluence Search (Fixed Format)", 
            "tool": "confluence_search",
            "params": {
                "query": "Autopilot for Everyone",
                "limit": 10
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📝 {scenario['name']}")
        print(f"   Tool: {scenario['tool']}")
        print(f"   Params: {scenario['params']}")
        
        try:
            result = await atlassian_tool.execute_mcp_tool(
                scenario['tool'], 
                scenario['params']
            )
            
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                if "message" in result:
                    print(f"      Details: {result['message']}")
            else:
                print(f"   ✅ Success!")
                if "result" in result and isinstance(result["result"], list):
                    print(f"      Found {len(result['result'])} results")
                    if result["result"]:
                        first_result = result["result"][0]
                        title = first_result.get("title", first_result.get("summary", "No title"))
                        print(f"      First result: {title}")
                        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    print("✅ If both tests show 'Success!' the parameter fix is working")
    print("❌ If either shows 'jql is a required property', more fixes needed")

if __name__ == "__main__":
    asyncio.run(test_parameter_formats())