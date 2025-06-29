#!/usr/bin/env python3
"""
Test MCP Localhost - Debug why JQL restrictions are appearing in local testing
"""

import asyncio
import httpx
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_localhost():
    """Test MCP server directly to debug JQL restriction issue"""
    
    print("=" * 80)
    print("🔍 MCP LOCALHOST DEBUGGING")
    print("=" * 80)
    
    # Check MCP server health first
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            health_response = await client.get("http://localhost:8001/healthz")
            print(f"✅ MCP Server Health: {health_response.status_code} - {health_response.text}")
    except Exception as e:
        print(f"❌ MCP Server Health Check Failed: {e}")
        return
    
    # Test MCP protocol directly with correct headers
    try:
        # Use the same headers as AtlassianTool
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Initialize session
            init_request = {
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {}
                }
            }
            
            print("🚀 Initializing MCP session...")
            init_response = await client.post("http://localhost:8001/mcp/", json=init_request, headers=headers)
            print(f"Init response: {init_response.status_code}")
            
            # Send initialized notification
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            print("📡 Sending initialized notification...")
            notif_response = await client.post("http://localhost:8001/mcp/", json=initialized_request, headers=headers)
            print(f"Notification response: {notif_response.status_code}")
            
            # Test simple Jira search with project restriction
            jira_search_request = {
                "jsonrpc": "2.0",
                "id": "search",
                "method": "tools/call",
                "params": {
                    "name": "jira_search",
                    "arguments": {
                        "jql": "project = DESIGN ORDER BY created DESC",
                        "limit": 3
                    }
                }
            }
            
            print("🎫 Testing Jira search with project restriction...")
            search_response = await client.post("http://localhost:8001/mcp/", json=jira_search_request, headers=headers)
            print(f"Search response status: {search_response.status_code}")
            
            if search_response.status_code == 200:
                result = search_response.json()
                print(f"Search result: {json.dumps(result, indent=2)}")
                
                if "result" in result and "content" in result["result"]:
                    content = result["result"]["content"]
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "")
                        if "Error calling tool" in text_content:
                            print("❌ Still getting tool error even with project restriction")
                        else:
                            print("✅ Jira search successful with project restriction")
                    else:
                        print("⚠️ Empty content in search result")
                else:
                    print("⚠️ Unexpected result structure")
            else:
                print(f"❌ Search failed: {search_response.text}")
                
            # Test even simpler query - just get a specific issue
            simple_request = {
                "jsonrpc": "2.0",
                "id": "simple",
                "method": "tools/call",
                "params": {
                    "name": "jira_get",
                    "arguments": {
                        "issue_key": "DESIGN-1467"
                    }
                }
            }
            
            print("🔍 Testing simple Jira get by issue key...")
            simple_response = await client.post("http://localhost:8001/mcp/", json=simple_request, headers=headers)
            print(f"Simple get response: {simple_response.status_code}")
            
            if simple_response.status_code == 200:
                simple_result = simple_response.json()
                print(f"Simple result preview: {str(simple_result)[:200]}...")
                
    except Exception as e:
        print(f"❌ MCP Test Failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("🎯 MCP LOCALHOST DEBUG COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mcp_localhost())