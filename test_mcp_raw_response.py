#!/usr/bin/env python3
"""
Test raw MCP responses to understand what the server is actually returning
"""
import asyncio
import httpx
import json
import uuid

async def test_raw_mcp():
    """Test raw MCP responses"""
    
    print("🔧 Testing Raw MCP Responses...")
    
    base_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Step 1: Test basic health
        print("\n1. Testing Health:")
        health_response = await client.get(f"{base_url}/health")
        print(f"Health: {health_response.status_code} - {health_response.json()}")
        
        # Step 2: Test tools discovery
        print("\n2. Testing Tools Discovery:")
        tools_response = await client.post(f"{base_url}/mcp")
        print(f"Tools Status: {tools_response.status_code}")
        print(f"Tools Headers: {dict(tools_response.headers)}")
        print(f"Tools Response: {tools_response.text[:500]}...")
        
        # Step 3: Initialize session
        print("\n3. Testing Session Initialization:")
        session_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        session_response = await client.post(f"{base_url}/mcp", json=session_request, headers=headers)
        print(f"Session Status: {session_response.status_code}")
        print(f"Session Headers: {dict(session_response.headers)}")
        print(f"Session Content-Type: {session_response.headers.get('content-type')}")
        print(f"Session Response: {session_response.text[:500]}...")
        
        if session_response.status_code == 200:
            session_url = session_response.url
            session_id = session_response.headers.get("mcp-session-id")
            
            # Try to parse the response
            try:
                session_data = session_response.json()
                print(f"Session JSON: {session_data}")
            except Exception as e:
                print(f"Session JSON parse failed: {e}")
                # Try SSE parsing
                for line in session_response.text.split('\n'):
                    if line.strip().startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            print(f"SSE data: {data}")
                        except:
                            pass
            
            # Step 4: Send initialized notification
            print("\n4. Testing Initialized Notification:")
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            init_headers = headers.copy()
            if session_id:
                init_headers["mcp-session-id"] = session_id
            
            init_response = await client.post(str(session_url), json=initialized_request, headers=init_headers)
            print(f"Initialized Status: {init_response.status_code}")
            print(f"Initialized Response: {init_response.text[:200]}...")
            
            # Step 5: Test tool call
            print("\n5. Testing Tool Call:")
            tool_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "get_atlassian_status",
                    "arguments": {}
                }
            }
            
            tool_response = await client.post(str(session_url), json=tool_request, headers=init_headers)
            print(f"Tool Status: {tool_response.status_code}")
            print(f"Tool Headers: {dict(tool_response.headers)}")
            print(f"Tool Content-Type: {tool_response.headers.get('content-type')}")
            print(f"Tool Response: {tool_response.text[:800]}...")

if __name__ == "__main__":
    asyncio.run(test_raw_mcp())