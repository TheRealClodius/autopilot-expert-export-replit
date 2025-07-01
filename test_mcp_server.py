#!/usr/bin/env python3
"""
Test script to check MCP server connectivity and Atlassian tool availability.
"""

import asyncio
import httpx
import json

async def test_mcp_server():
    """Test MCP server health and available tools"""
    
    server_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("🔍 Testing MCP Server Connectivity...")
            
            # Test 1: Health check
            print("\n1. Health Check:")
            try:
                health_response = await client.get(f"{server_url}/health")
                print(f"   Status: {health_response.status_code}")
                print(f"   Response: {health_response.text}")
            except Exception as e:
                print(f"   ❌ Health check failed: {e}")
                return
            
            # Test 2: MCP initialization
            print("\n2. MCP Initialization:")
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            try:
                init_response = await client.post(f"{server_url}/mcp", json=init_request)
                print(f"   Status: {init_response.status_code}")
                if init_response.status_code == 200:
                    init_data = init_response.json()
                    print(f"   Response: {json.dumps(init_data, indent=2)}")
                else:
                    print(f"   Error: {init_response.text}")
            except Exception as e:
                print(f"   ❌ Initialization failed: {e}")
                return
            
            # Test 3: List available tools
            print("\n3. Available Tools:")
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            try:
                tools_response = await client.post(f"{server_url}/mcp", json=tools_request)
                print(f"   Status: {tools_response.status_code}")
                if tools_response.status_code == 200:
                    tools_data = tools_response.json()
                    print(f"   Response: {json.dumps(tools_data, indent=2)}")
                    
                    # Analyze tools
                    if "result" in tools_data and "tools" in tools_data["result"]:
                        tools = tools_data["result"]["tools"]
                        print(f"\n   📊 Found {len(tools)} tools:")
                        for tool in tools:
                            print(f"      - {tool.get('name', 'unnamed')}")
                            
                        # Check for Atlassian tools
                        atlassian_tools = [t for t in tools if any(keyword in t.get('name', '').lower() for keyword in ['jira', 'confluence', 'atlassian'])]
                        if atlassian_tools:
                            print(f"\n   ✅ Atlassian tools found: {len(atlassian_tools)}")
                        else:
                            print(f"\n   ⚠️  No Atlassian tools found - only basic tools available")
                    else:
                        print("   ⚠️  No tools returned in response")
                else:
                    print(f"   Error: {tools_response.text}")
            except Exception as e:
                print(f"   ❌ Tools list failed: {e}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())