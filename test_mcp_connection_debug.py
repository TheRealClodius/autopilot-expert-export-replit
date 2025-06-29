#!/usr/bin/env python3
"""
MCP Connection Debug Test

Test MCP connection directly to identify the exact issue causing "All connection attempts failed"
"""

import asyncio
import httpx
import json
from config import settings

async def test_mcp_connection():
    """Test MCP connection step by step to identify the failure point"""
    
    print("🔧 MCP CONNECTION DEBUG TEST")
    print("=" * 50)
    
    base_url = settings.MCP_SERVER_URL
    print(f"Testing MCP server at: {base_url}")
    
    # Test 1: Basic connectivity
    print("\n1. Testing basic health check...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{base_url}/healthz")
            print(f"   ✅ Health check: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # Test 2: MCP endpoint accessibility
    print("\n2. Testing MCP endpoint...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{base_url}/mcp")
            print(f"   Status: {response.status_code}")
            if response.status_code == 307:
                redirect_url = response.headers.get("location")
                print(f"   Redirect to: {redirect_url}")
    except Exception as e:
        print(f"   ❌ MCP endpoint failed: {e}")
        return False
    
    # Test 3: Session initialization (exactly like AtlassianTool)
    print("\n3. Testing session initialization...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            base_endpoint = f"{base_url}/mcp"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            session_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "atlassian-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            print(f"   Sending initialize request to: {base_endpoint}")
            print(f"   Request: {json.dumps(session_request, indent=2)}")
            
            session_response = await client.post(base_endpoint, json=session_request, headers=headers)
            
            print(f"   Response status: {session_response.status_code}")
            print(f"   Response headers: {dict(session_response.headers)}")
            
            if session_response.status_code == 307:
                redirect_url = session_response.headers.get("location")
                print(f"   Following redirect to: {redirect_url}")
                session_response = await client.post(redirect_url, json=session_request, headers=headers)
                print(f"   Redirect response status: {session_response.status_code}")
            
            response_text = session_response.text
            print(f"   Response body: {response_text[:500]}")
            
            if session_response.status_code == 200:
                print("   ✅ Session initialization successful")
                return True
            else:
                print(f"   ❌ Session initialization failed: {session_response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ Session initialization error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_connection())
    print("\n" + "=" * 50)
    if success:
        print("✅ MCP CONNECTION TEST PASSED")
    else:
        print("❌ MCP CONNECTION TEST FAILED")