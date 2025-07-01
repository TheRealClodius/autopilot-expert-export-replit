#!/usr/bin/env python3
"""
Test specific Atlassian tool functionality
"""

import asyncio
import httpx
import json

async def test_atlassian_tool():
    """Test a specific Atlassian tool call"""
    
    server_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("🔍 Testing Atlassian Tool Functionality...")
            
            # Test Atlassian status
            print("\n1. Checking Atlassian Status:")
            status_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_atlassian_status",
                    "arguments": {}
                }
            }
            
            try:
                status_response = await client.post(f"{server_url}/mcp", json=status_request)
                print(f"   Status: {status_response.status_code}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Response: {json.dumps(status_data, indent=2)}")
                else:
                    print(f"   Error: {status_response.text}")
            except Exception as e:
                print(f"   ❌ Status check failed: {e}")
            
            # Test Jira search with a simple query
            print("\n2. Testing Jira Search:")
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
            
            try:
                jira_response = await client.post(f"{server_url}/mcp", json=jira_request)
                print(f"   Status: {jira_response.status_code}")
                if jira_response.status_code == 200:
                    jira_data = jira_response.json()
                    print(f"   Response: {json.dumps(jira_data, indent=2)}")
                else:
                    print(f"   Error: {jira_response.text}")
            except Exception as e:
                print(f"   ❌ Jira search failed: {e}")
                
            # Test Confluence search
            print("\n3. Testing Confluence Search:")
            confluence_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call", 
                "params": {
                    "name": "get_confluence_pages",
                    "arguments": {
                        "query": "autopilot",
                        "limit": 5
                    }
                }
            }
            
            try:
                confluence_response = await client.post(f"{server_url}/mcp", json=confluence_request)
                print(f"   Status: {confluence_response.status_code}")
                if confluence_response.status_code == 200:
                    confluence_data = confluence_response.json()
                    print(f"   Response: {json.dumps(confluence_data, indent=2)}")
                else:
                    print(f"   Error: {confluence_response.text}")
            except Exception as e:
                print(f"   ❌ Confluence search failed: {e}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_atlassian_tool())