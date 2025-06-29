#!/usr/bin/env python3
"""
Test direct Atlassian tool calls to see if they're available but not listed
"""
import asyncio
import httpx
import json

async def test_direct_atlassian():
    """Test direct calls to Atlassian tools"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test direct calls to potential Atlassian tools
            test_tools = [
                ("jira_search", {"jql": "project = AUTOPILOT", "limit": 3}),
                ("confluence_search", {"query": "autopilot", "limit": 3}),
                ("jira_get", {"issue_key": "AUTOPILOT-1"}),
                ("confluence_get", {"page_id": "123456"}),
            ]
            
            for tool_name, args in test_tools:
                print(f"\n🔍 Testing {tool_name}...")
                
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": args
                    }
                }
                
                response = await client.post(f"{mcp_url}/mcp", json=request)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'error' in data:
                            error = data['error']
                            if 'Tool not found' in str(error) or 'Unknown tool' in str(error):
                                print(f"❌ Tool {tool_name} not available")
                            else:
                                print(f"🔧 Tool exists but error: {error}")
                        elif 'result' in data:
                            print(f"✅ Tool {tool_name} available and working!")
                            result = data['result']
                            if isinstance(result, dict) and 'content' in result:
                                print(f"Result preview: {str(result['content'])[:100]}...")
                            else:
                                print(f"Result preview: {str(result)[:100]}...")
                    except Exception as e:
                        print(f"Error parsing response: {e}")
                        print(f"Raw: {response.text[:200]}")
                else:
                    print(f"Failed: {response.text[:200]}")
                    
    except Exception as e:
        print(f"❌ Error testing direct calls: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_atlassian())