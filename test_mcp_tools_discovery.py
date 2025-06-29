#!/usr/bin/env python3
"""
Test script to discover available MCP tools from the remote MCP server
"""
import asyncio
import httpx
import json

async def discover_mcp_tools():
    """Discover what tools are available from the MCP server"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Check server health
            print("🔍 Testing MCP server health...")
            health_response = await client.get(f"{mcp_url}/health")
            print(f"Health status: {health_response.status_code}")
            
            # Test 2: Initialize MCP session
            print("\n🤝 Initializing MCP session...")
            session_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            init_response = await client.post(f"{mcp_url}/mcp", json=session_request)
            print(f"Initialize status: {init_response.status_code}")
            
            if init_response.status_code == 200:
                try:
                    init_data = init_response.json()
                    print(f"Initialize response: {json.dumps(init_data, indent=2)}")
                    result = init_data.get('result', {}) if init_data else {}
                    capabilities = result.get('capabilities', {}) if result else {}
                    print(f"Server capabilities: {json.dumps(capabilities, indent=2)}")
                except Exception as e:
                    print(f"Failed to parse init response: {e}")
                    print(f"Raw response: {init_response.text}")
                
                # Test 3: Send 'initialized' notification
                print("\n📋 Sending initialized notification...")
                initialized_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                notify_response = await client.post(f"{mcp_url}/mcp", json=initialized_request)
                print(f"Initialized notification status: {notify_response.status_code}")
                
                # Test 4: List available tools
                print("\n🛠️ Listing available tools...")
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
                
                tools_response = await client.post(f"{mcp_url}/mcp", json=tools_request)
                print(f"Tools list status: {tools_response.status_code}")
                
                if tools_response.status_code == 200:
                    tools_data = tools_response.json()
                    print(f"Available tools:")
                    
                    if 'result' in tools_data and 'tools' in tools_data['result']:
                        for tool in tools_data['result']['tools']:
                            print(f"  📌 {tool['name']}")
                            print(f"     Description: {tool.get('description', 'No description')}")
                            if 'inputSchema' in tool:
                                print(f"     Parameters: {list(tool['inputSchema'].get('properties', {}).keys())}")
                            print()
                    else:
                        print(f"Unexpected tools response: {json.dumps(tools_data, indent=2)}")
                else:
                    print(f"Tools list failed: {tools_response.text}")
            else:
                print(f"Initialize failed: {init_response.text}")
                
    except Exception as e:
        print(f"❌ Error discovering MCP tools: {e}")

if __name__ == "__main__":
    asyncio.run(discover_mcp_tools())