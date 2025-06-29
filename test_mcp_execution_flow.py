#!/usr/bin/env python3
"""
Test the complete MCP execution flow to see where content is lost
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_mcp_execution_flow():
    """Test complete MCP execution to see actual content"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    print(f"🔍 TESTING COMPLETE MCP EXECUTION FLOW")
    print(f"Time: {datetime.now().isoformat()}")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # Step 1: List available tools
        print("1. Listing available tools...")
        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            response = await client.post(
                f"{mcp_url}/mcp",
                json=tools_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                tools = data.get("result", {}).get("tools", [])
                print(f"   Found {len(tools)} tools")
                for tool in tools:
                    print(f"     - {tool.get('name')}: {tool.get('description')}")
            else:
                print(f"   Error: {response.text}")
                return
                
        except Exception as e:
            print(f"   Error: {e}")
            return
        
        print()
        
        # Step 2: Execute actual Confluence search
        print("2. Executing Confluence search for 'Autopilot'...")
        try:
            search_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_confluence_pages",
                    "arguments": {
                        "query": "Autopilot"
                    }
                }
            }
            
            response = await client.post(
                f"{mcp_url}/mcp",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Full response: {json.dumps(data, indent=2)}")
                
                result = data.get("result")
                if result:
                    content = result.get("content", [])
                    if isinstance(content, list):
                        print(f"   Found {len(content)} pages:")
                        for i, page in enumerate(content[:3]):  # Show first 3
                            print(f"     Page {i+1}:")
                            print(f"       Title: {page.get('title', 'No title')}")
                            print(f"       URL: {page.get('url', 'No URL')}")
                            print(f"       Space: {page.get('space', 'No space')}")
                            excerpt = page.get('excerpt', 'No excerpt')[:100]
                            print(f"       Excerpt: {excerpt}...")
                    else:
                        print(f"   Unexpected content format: {type(content)}")
                        print(f"   Content: {content}")
                else:
                    print(f"   No result field in response")
            else:
                print(f"   Error response: {response.text}")
                
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Step 3: Execute Jira search
        print("3. Executing Jira search for Autopilot bugs...")
        try:
            jira_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_jira_issues",
                    "arguments": {
                        "jql": "project = AUTOPILOT AND issuetype = Bug"
                    }
                }
            }
            
            response = await client.post(
                f"{mcp_url}/mcp",
                json=jira_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response keys: {list(data.keys())}")
                
                result = data.get("result")
                if result:
                    issues = result.get("content", [])
                    if isinstance(issues, list):
                        print(f"   Found {len(issues)} issues:")
                        for i, issue in enumerate(issues[:2]):  # Show first 2
                            print(f"     Issue {i+1}:")
                            print(f"       Key: {issue.get('key', 'No key')}")
                            print(f"       Summary: {issue.get('summary', 'No summary')}")
                            print(f"       Status: {issue.get('status', 'No status')}")
                    else:
                        print(f"   Unexpected issues format: {type(issues)}")
                        print(f"   Issues: {issues}")
                else:
                    print(f"   No result field in response")
                    print(f"   Full response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error response: {response.text}")
                
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_execution_flow())