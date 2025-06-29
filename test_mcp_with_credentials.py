#!/usr/bin/env python3
"""
Test MCP server with Atlassian credentials to verify real UiPath data retrieval
"""
import asyncio
import httpx
import json

async def test_mcp_atlassian():
    """Test MCP server with Atlassian credentials"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            
            # Test 1: Get available tools
            print("🛠️ Getting available tools...")
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            tools_response = await client.post(f"{mcp_url}/mcp", json=tools_request)
            
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                if 'result' in tools_data and 'tools' in tools_data['result']:
                    tools = tools_data['result']['tools']
                    print(f"Available tools ({len(tools)}):")
                    
                    atlassian_tools = []
                    for tool in tools:
                        name = tool.get('name', 'unnamed')
                        desc = tool.get('description', 'No description')
                        print(f"  📌 {name}: {desc}")
                        
                        if any(keyword in name.lower() for keyword in ['jira', 'confluence', 'atlassian']):
                            atlassian_tools.append(name)
                    
                    print(f"\n🎯 Found {len(atlassian_tools)} Atlassian tools: {atlassian_tools}")
                    
                    # Test 2: Try calling get_jira_issues with AUTOPILOT project
                    if 'get_jira_issues' in atlassian_tools:
                        print(f"\n🔍 Testing get_jira_issues with AUTOPILOT project...")
                        
                        jira_request = {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "get_jira_issues",
                                "arguments": {
                                    "jql": "project = AUTOPILOT AND issuetype = Bug",
                                    "max_results": 5
                                }
                            }
                        }
                        
                        jira_response = await client.post(f"{mcp_url}/mcp", json=jira_request)
                        print(f"Jira call status: {jira_response.status_code}")
                        
                        if jira_response.status_code == 200:
                            jira_data = jira_response.json()
                            
                            if 'result' in jira_data:
                                result = jira_data['result']
                                print("✅ Success! Jira data retrieved:")
                                
                                if 'content' in result:
                                    content = result['content']
                                    if 'issues' in content:
                                        issues = content['issues']
                                        print(f"  Found {len(issues)} issues in AUTOPILOT project")
                                        
                                        for i, issue in enumerate(issues[:3], 1):
                                            key = issue.get('key', 'N/A')
                                            fields = issue.get('fields', {})
                                            summary = fields.get('summary', 'No summary')
                                            status = fields.get('status', {}).get('name', 'No status')
                                            print(f"    {i}. {key}: {summary} [{status}]")
                                    
                                    if 'total' in content:
                                        print(f"  Total issues in project: {content['total']}")
                                        
                                    if 'jira_url' in content:
                                        print(f"  Connected to: {content['jira_url']}")
                                
                                print(f"  Full result: {str(result)[:200]}...")
                                
                            elif 'error' in jira_data:
                                error = jira_data['error']
                                print(f"❌ MCP Error: {error}")
                        else:
                            print(f"❌ HTTP Error: {jira_response.text}")
                    
                    # Test 3: Try Confluence search
                    if 'get_confluence_pages' in atlassian_tools:
                        print(f"\n🔍 Testing get_confluence_pages...")
                        
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
                        print(f"Confluence call status: {confluence_response.status_code}")
                        
                        if confluence_response.status_code == 200:
                            confluence_data = confluence_response.json()
                            
                            if 'result' in confluence_data:
                                result = confluence_data['result']
                                print("✅ Success! Confluence data retrieved:")
                                
                                if 'content' in result:
                                    content = result['content']
                                    if 'results' in content:
                                        pages = content['results']
                                        print(f"  Found {len(pages)} pages matching 'autopilot'")
                                        
                                        for i, page in enumerate(pages[:3], 1):
                                            title = page.get('title', 'No title')
                                            url = page.get('_links', {}).get('webui', 'No URL')
                                            print(f"    {i}. {title}")
                                            if url and url != 'No URL':
                                                print(f"       URL: {url}")
                                
                                print(f"  Full result: {str(result)[:200]}...")
                                
                            elif 'error' in confluence_data:
                                error = confluence_data['error']
                                print(f"❌ MCP Error: {error}")
                        else:
                            print(f"❌ HTTP Error: {confluence_response.text}")
                            
            else:
                print(f"❌ Failed to get tools: {tools_response.text}")
                
    except Exception as e:
        print(f"❌ Error testing MCP: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_atlassian())