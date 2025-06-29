#!/usr/bin/env python3

"""
Debug MCP Direct Connection
Test the exact MCP connection that's failing in production
"""

import asyncio
import httpx
import json
import uuid
import sys

async def debug_mcp_direct():
    """Test direct MCP connection to identify the exact failure point"""
    
    print("🔧 DEBUGGING MCP DIRECT CONNECTION")
    print("="*50)
    
    try:
        # Test 1: Basic MCP server health
        print("1. Testing MCP server health...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            health_response = await client.get("http://localhost:8001/healthz")
            print(f"   Health status: {health_response.status_code}")
            print(f"   Health body: {health_response.text}")
        
        # Test 2: Initialize MCP session directly
        print("\n2. Testing MCP direct initialization...")
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Test 3: Send initialize request directly to /mcp endpoint
            print("\n3. Testing MCP initialize request...")
            init_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "debug-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            init_response = await client.post(
                "http://localhost:8001/mcp",
                json=init_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"   Initialize status: {init_response.status_code}")
            print(f"   Initialize response: {init_response.text}")
            
            if init_response.status_code not in [200, 202]:
                print(f"   ERROR: Initialize failed")
                return
            
            # Test 4: Send initialized notification
            print("\n4. Testing initialized notification...")
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            initialized_response = await client.post(
                "http://localhost:8001/mcp",
                json=initialized_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"   Initialized status: {initialized_response.status_code}")
            print(f"   Initialized response: {initialized_response.text}")
            
            # Test 5: Simple confluence search
            print("\n5. Testing simple confluence search...")
            search_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "confluence_search",
                    "arguments": {
                        "query": "autopilot",
                        "limit": 3
                    }
                }
            }
            
            search_response = await client.post(
                "http://localhost:8001/mcp",
                json=search_request,
                headers={"Content-Type": "application/json"},
                timeout=60.0
            )
            
            print(f"   Search status: {search_response.status_code}")
            print(f"   Search response: {search_response.text[:500]}...")
            
            if search_response.status_code == 200:
                try:
                    search_data = search_response.json()
                    if "result" in search_data and search_data["result"]:
                        print(f"   SUCCESS: Found {len(search_data['result'])} results")
                        for i, result in enumerate(search_data["result"][:2]):
                            print(f"   Result {i+1}: {result.get('title', 'No title')}")
                    else:
                        print(f"   No results found in response")
                except Exception as e:
                    print(f"   Error parsing search response: {e}")
            
        print("\n✅ MCP direct connection test completed")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_mcp_direct())