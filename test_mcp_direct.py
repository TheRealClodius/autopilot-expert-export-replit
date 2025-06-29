#!/usr/bin/env python3
"""
Direct MCP Server Test

Test direct communication with MCP server to debug SSE issues.
"""
import asyncio
import json
import httpx

async def test_mcp_server_direct():
    """Test direct communication with MCP server"""
    print("🔧 TESTING DIRECT MCP SERVER COMMUNICATION")
    print("=" * 50)
    
    mcp_server_url = "http://localhost:8001"
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            print("1. Testing health endpoint...")
            health_response = await client.get(f"{mcp_server_url}/healthz")
            print(f"   Status: {health_response.status_code}")
            print(f"   Response: {health_response.text}")
            
            if health_response.status_code != 200:
                print("❌ Health check failed")
                return False
            
            print("✅ Health check passed")
            
            # Test SSE endpoint availability
            print("\n2. Testing SSE endpoint...")
            try:
                sse_response = await client.get(f"{mcp_server_url}/sse")
                print(f"   Status: {sse_response.status_code}")
                print(f"   Headers: {dict(sse_response.headers)}")
            except Exception as e:
                print(f"   SSE endpoint error: {e}")
            
            # Check what endpoints are available
            print("\n3. Testing root endpoint...")
            try:
                root_response = await client.get(mcp_server_url)
                print(f"   Status: {root_response.status_code}")
                print(f"   Response: {root_response.text[:200]}...")
            except Exception as e:
                print(f"   Root endpoint error: {e}")
            
            return True
            
    except Exception as e:
        print(f"💥 Direct communication failed: {e}")
        return False

async def main():
    success = await test_mcp_server_direct()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ MCP SERVER: ACCESSIBLE")
    else:
        print("❌ MCP SERVER: COMMUNICATION ISSUES")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())