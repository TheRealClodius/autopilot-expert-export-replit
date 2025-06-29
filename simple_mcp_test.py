#!/usr/bin/env python3
"""
Simple test to see what the MCP server actually provides
"""

import asyncio
import httpx
import json

async def test_mcp_server():
    """Test what tools the MCP server actually provides"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    print(f"🔍 Testing MCP server at: {mcp_url}")
    
    # Test health check
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            health_response = await client.get(f"{mcp_url}/health")
            print(f"✅ Health check: {health_response.status_code}")
            
            # Test tools endpoint
            tools_response = await client.get(f"{mcp_url}/tools")
            print(f"📋 Tools endpoint: {tools_response.status_code}")
            
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                print(f"📋 Available tools: {json.dumps(tools_data, indent=2)}")
            else:
                print(f"Tools response: {tools_response.text}")
                
            # Test if there's a different endpoint
            try:
                list_tools_response = await client.post(f"{mcp_url}/mcp", json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "tools/list",
                    "params": {}
                })
                print(f"🔧 MCP tools/list: {list_tools_response.status_code}")
                if list_tools_response.status_code == 200:
                    print(f"MCP tools data: {json.dumps(list_tools_response.json(), indent=2)}")
            except Exception as e:
                print(f"MCP endpoint error: {e}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())