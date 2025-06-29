#!/usr/bin/env python3
"""
Test MCP server with credentials to verify Atlassian tools are working
"""
import asyncio
import httpx
import json

async def test_mcp_atlassian():
    """Test MCP server with Atlassian credentials"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Check available tools
            print("🛠️ Testing available tools...")
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            tools_response = await client.post(f"{mcp_url}/mcp", json=tools_request)
            print(f"Tools status: {tools_response.status_code}")
            
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                if 'result' in tools_data and 'tools' in tools_data['result']:
                    tools = tools_data['result']['tools']
                    print("Available tools:")
                    for tool in tools:
                        print(f"  📌 {tool['name']}: {tool.get('description', 'No description')}")
                    
                    # Check if we have Atlassian tools
                    atlassian_tools = [t for t in tools if any(keyword in t['name'] for keyword in ['jira', 'confluence'])]
                    if atlassian_tools:
                        print(f"\n✅ Found {len(atlassian_tools)} Atlassian tools!")
                        
                        # Test 2: Try calling a Jira search
                        print("\n🔍 Testing Jira search...")
                        jira_request = {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "jira_search",
                                "arguments": {
                                    "jql": "project = AUTOPILOT",
                                    "limit": 3
                                }
                            }
                        }
                        
                        jira_response = await client.post(f"{mcp_url}/mcp", json=jira_request)
                        print(f"Jira search status: {jira_response.status_code}")
                        
                        if jira_response.status_code == 200:
                            jira_data = jira_response.json()
                            print("Jira search result:")
                            print(json.dumps(jira_data, indent=2)[:500] + "...")
                        else:
                            print(f"Jira search failed: {jira_response.text}")
                            
                    else:
                        print("❌ No Atlassian tools found. Still using basic test tools.")
                        print("This means the MCP server credentials may not be configured correctly.")
                else:
                    print(f"Unexpected response: {tools_data}")
            else:
                print(f"Tools request failed: {tools_response.text}")
                
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_atlassian())