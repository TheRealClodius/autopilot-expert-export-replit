#!/usr/bin/env python3
"""
Test MCP server connection with the updated URL
"""
import asyncio
import httpx
import json

async def test_mcp_connection():
    """Test connection to the updated MCP server"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Test 1: Call echo tool to verify MCP is working
            print("🔊 Testing echo tool...")
            echo_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {
                        "text": "MCP connection test successful"
                    }
                }
            }
            
            echo_response = await client.post(f"{mcp_url}/mcp", json=echo_request)
            print(f"Echo status: {echo_response.status_code}")
            
            if echo_response.status_code == 200:
                echo_data = echo_response.json()
                print("Echo response:", json.dumps(echo_data, indent=2))
            
            # Test 2: Try calling get_jira_issues with correct name
            print("\n🔍 Testing get_jira_issues directly...")
            jira_request = {
                "jsonrpc": "2.0", 
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_jira_issues",
                    "arguments": {
                        "jql": "project = AUTOPILOT",
                        "limit": 5
                    }
                }
            }
            
            jira_response = await client.post(f"{mcp_url}/mcp", json=jira_request)
            print(f"Jira search status: {jira_response.status_code}")
            
            if jira_response.status_code == 200:
                jira_data = jira_response.json()
                print("Jira response:", json.dumps(jira_data, indent=2)[:500] + "...")
                
                if 'result' in jira_data and jira_data['result']:
                    print("✅ Jira search tool is working!")
                elif 'error' in jira_data:
                    error = jira_data['error']
                    if 'Tool not found' in str(error) or 'Unknown tool' in str(error):
                        print("❌ Jira tool not available")
                    else:
                        print(f"🔧 Jira tool available but error: {error}")
            else:
                print(f"❌ Jira request failed: {jira_response.text[:200]}")
            
            # Test 3: Try get_confluence_pages with correct name
            print("\n📄 Testing get_confluence_pages directly...")
            confluence_request = {
                "jsonrpc": "2.0",
                "id": 3, 
                "method": "tools/call",
                "params": {
                    "name": "get_confluence_pages",
                    "arguments": {
                        "query": "autopilot",
                        "limit": 3
                    }
                }
            }
            
            confluence_response = await client.post(f"{mcp_url}/mcp", json=confluence_request)
            print(f"Confluence search status: {confluence_response.status_code}")
            
            if confluence_response.status_code == 200:
                confluence_data = confluence_response.json()
                print("Confluence response:", json.dumps(confluence_data, indent=2)[:500] + "...")
                
                if 'result' in confluence_data and confluence_data['result']:
                    print("✅ Confluence search tool is working!")
                elif 'error' in confluence_data:
                    error = confluence_data['error']
                    if 'Tool not found' in str(error) or 'Unknown tool' in str(error):
                        print("❌ Confluence tool not available")
                    else:
                        print(f"🔧 Confluence tool available but error: {error}")
            else:
                print(f"❌ Confluence request failed: {confluence_response.text[:200]}")
            
            # Test 4: Check Atlassian configuration status
            print("\n⚙️ Testing get_atlassian_status...")
            status_request = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call", 
                "params": {
                    "name": "get_atlassian_status",
                    "arguments": {}
                }
            }
            
            status_response = await client.post(f"{mcp_url}/mcp", json=status_request)
            print(f"Atlassian status: {status_response.status_code}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print("Status response:", json.dumps(status_data, indent=2))
                
                if 'result' in status_data and status_data['result']:
                    print("✅ Atlassian configuration tool is working!")
                elif 'error' in status_data:
                    error = status_data['error']
                    print(f"🔧 Status tool error: {error}")
            else:
                print(f"❌ Status request failed: {status_response.text[:200]}")
                
    except Exception as e:
        print(f"❌ Error testing MCP connection: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())