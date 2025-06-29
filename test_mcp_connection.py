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
            
            # Test 1: Basic health check
            print("🏥 Testing server health...")
            try:
                health_response = await client.get(f"{mcp_url}/health")
                print(f"Health status: {health_response.status_code}")
                if health_response.status_code == 200:
                    print("✅ Server is healthy")
                else:
                    print(f"❌ Health check failed: {health_response.text}")
            except Exception as e:
                print(f"❌ Health check error: {e}")
            
            # Test 2: Check different endpoints
            print("\n🔍 Testing different endpoints...")
            endpoints_to_try = [
                "/mcp",
                "/tools",
                "/api/tools",
                "/v1/tools"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    response = await client.get(f"{mcp_url}{endpoint}")
                    print(f"  {endpoint}: {response.status_code}")
                    if response.status_code == 200:
                        content = response.text[:100]
                        print(f"    Content preview: {content}")
                except:
                    print(f"  {endpoint}: Failed")
            
            # Test 3: Try MCP protocol with different approaches
            print("\n🔧 Testing MCP protocol variations...")
            
            # Approach 1: Standard tools/list
            tools_requests = [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "list_tools",
                    "params": {}
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "get_tools",
                    "params": {}
                }
            ]
            
            for i, request in enumerate(tools_requests, 1):
                try:
                    response = await client.post(f"{mcp_url}/mcp", json=request)
                    print(f"  Method {i} ({request['method']}): {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'result' in data and data['result'] and 'tools' in data['result']:
                            tools = data['result']['tools']
                            tool_names = [t.get('name', 'unnamed') for t in tools]
                            print(f"    Found {len(tools)} tools: {tool_names}")
                            
                            # Check for Atlassian tools
                            atlassian_tools = [name for name in tool_names if any(kw in name.lower() for kw in ['jira', 'confluence', 'atlassian'])]
                            if atlassian_tools:
                                print(f"    ✅ Atlassian tools found: {atlassian_tools}")
                                return tools  # Success!
                            else:
                                print(f"    ❌ No Atlassian tools in: {tool_names}")
                        else:
                            print(f"    Response: {str(data)[:100]}...")
                    else:
                        print(f"    Error: {response.text[:100]}")
                        
                except Exception as e:
                    print(f"    Exception: {e}")
            
            # Test 4: Try a direct tool call to see if tools exist but aren't listed
            print("\n🎯 Testing direct tool calls...")
            direct_tests = [
                ("jira_search", {"jql": "project = TEST", "limit": 1}),
                ("confluence_search", {"query": "test", "limit": 1})
            ]
            
            for tool_name, args in direct_tests:
                try:
                    call_request = {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": args
                        }
                    }
                    
                    response = await client.post(f"{mcp_url}/mcp", json=call_request)
                    print(f"  {tool_name}: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'error' in data:
                            error_msg = data['error'].get('message', str(data['error']))
                            if 'not found' in error_msg.lower() or 'unknown' in error_msg.lower():
                                print(f"    ❌ Tool not available: {error_msg}")
                            else:
                                print(f"    🔧 Tool exists but error: {error_msg}")
                        elif 'result' in data:
                            print(f"    ✅ Tool working! Result: {str(data['result'])[:50]}...")
                    else:
                        print(f"    HTTP error: {response.text[:50]}")
                        
                except Exception as e:
                    print(f"    Exception: {e}")
                    
    except Exception as e:
        print(f"❌ Connection test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())