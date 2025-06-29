#!/usr/bin/env python3
"""
Direct test of MCP server connectivity to diagnose the issue
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_mcp_direct():
    """Test direct MCP server connection"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    print(f"🔍 Testing MCP Server Connectivity")
    print(f"URL: {mcp_url}")
    print(f"Time: {datetime.now().isoformat()}")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Basic health check
        print("1. Health Check...")
        try:
            response = await client.get(f"{mcp_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        
        # Test 2: MCP Protocol handshake
        print("2. MCP Protocol Test...")
        try:
            mcp_request = {
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
            
            response = await client.post(
                f"{mcp_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                # Send initialized notification
                print("3. Sending initialized notification...")
                init_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                
                init_response = await client.post(
                    f"{mcp_url}/mcp",
                    json=init_request,
                    headers={"Content-Type": "application/json"}
                )
                print(f"   Init Status: {init_response.status_code}")
                
                # Test tool listing
                print("4. Testing tool listing...")
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                tools_response = await client.post(
                    f"{mcp_url}/mcp",
                    json=tools_request,
                    headers={"Content-Type": "application/json"}
                )
                print(f"   Tools Status: {tools_response.status_code}")
                print(f"   Tools Response: {tools_response.text[:1000]}...")
                
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_direct())