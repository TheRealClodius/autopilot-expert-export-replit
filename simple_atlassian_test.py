#!/usr/bin/env python3
"""
Simple test for Atlassian connection
"""

import asyncio
import logging
import httpx

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def simple_test():
    """Simple test without importing the full class"""
    
    server_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    print("Testing basic MCP server connectivity...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health
            health_response = await client.get(f"{server_url}/health")
            print(f"Health: {health_response.status_code}")
            
            # Test tool list
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list", 
                "params": {}
            }
            
            tools_response = await client.post(f"{server_url}/mcp", json=tools_request)
            print(f"Tools list: {tools_response.status_code}")
            
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                tools = tools_data.get("result", {}).get("tools", [])
                print(f"Found {len(tools)} tools")
                atlassian_tools = [t for t in tools if any(kw in t.get('name', '').lower() for kw in ['jira', 'confluence'])]
                print(f"Atlassian tools: {[t.get('name') for t in atlassian_tools]}")
                
                # Test simple Jira call
                jira_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_jira_issues",
                        "arguments": {
                            "jql": "project = AUTOPILOT",
                            "limit": 2
                        }
                    }
                }
                
                print("Testing Jira call...")
                jira_response = await client.post(f"{server_url}/mcp", json=jira_request, timeout=60.0)
                print(f"Jira response: {jira_response.status_code}")
                
                if jira_response.status_code == 200:
                    jira_data = jira_response.json()
                    if "result" in jira_data and "content" in jira_data["result"]:
                        issues = jira_data["result"]["content"].get("issues", [])
                        print(f"✅ Found {len(issues)} Jira issues")
                        if issues:
                            print(f"First issue: {issues[0].get('key')} - {issues[0].get('summary')}")
                    else:
                        print(f"Unexpected Jira response structure: {jira_data}")
                else:
                    print(f"Jira call failed: {jira_response.text}")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_test())