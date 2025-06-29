#!/usr/bin/env python3
"""
Direct MCP Connection Test

Test the MCP server connection to identify the exact issue.
"""

import asyncio
import httpx
import json
import uuid

async def test_mcp_connection():
    """Test direct connection to MCP server"""
    
    print("🔧 TESTING DIRECT MCP CONNECTION")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    mcp_endpoint = f"{base_url}/mcp"
    
    try:
        # Test 1: Health check
        print("1️⃣ Testing MCP server health...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            health_response = await client.get(f"{base_url}/healthz")
            print(f"   Health status: {health_response.status_code}")
            print(f"   Health response: {health_response.text}")
        
        # Test 2: Initialize session
        print("\n2️⃣ Testing MCP session initialization...")
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
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            print(f"   Sending initialize request to: {mcp_endpoint}")
            print(f"   Request: {json.dumps(session_request, indent=2)}")
            
            session_response = await client.post(mcp_endpoint, json=session_request, headers=headers)
            
            print(f"   Initialize status: {session_response.status_code}")
            print(f"   Initialize headers: {dict(session_response.headers)}")
            print(f"   Initialize URL: {session_response.url}")
            
            if session_response.status_code == 200:
                response_text = session_response.text
                print(f"   Initialize response: {response_text[:500]}...")
                
                # Test 3: Send initialized notification
                print("\n3️⃣ Sending initialized notification...")
                
                # Get session ID if available
                session_id = session_response.headers.get("mcp-session-id")
                init_headers = headers.copy()
                if session_id:
                    init_headers["mcp-session-id"] = session_id
                    print(f"   Using session ID: {session_id}")
                
                initialized_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                session_url = session_response.url
                init_response = await client.post(str(session_url), json=initialized_request, headers=init_headers)
                print(f"   Initialized status: {init_response.status_code}")
                
                # Test 4: Try a simple tool call after proper initialization
                print("\n4️⃣ Testing tool call...")
                
                tool_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": "confluence_search",
                        "arguments": {
                            "query": "test",
                            "limit": 1
                        }
                    }
                }
                
                # Use same session headers and URL
                tool_headers = init_headers.copy()
                print(f"   Calling tool on URL: {session_url}")
                
                tool_response = await client.post(str(session_url), json=tool_request, headers=tool_headers)
                
                print(f"   Tool call status: {tool_response.status_code}")
                print(f"   Tool call headers: {dict(tool_response.headers)}")
                
                if tool_response.status_code == 200:
                    tool_text = tool_response.text
                    print(f"   Tool response: {tool_text[:1000]}...")
                    
                    # Parse the SSE response
                    print("\n5️⃣ Parsing tool response...")
                    for line in tool_text.split('\n'):
                        if line.startswith('data: '):
                            try:
                                json_data = line[6:]  # Remove 'data: ' prefix
                                parsed_data = json.loads(json_data)
                                print(f"   Parsed JSON: {json.dumps(parsed_data, indent=2)}")
                                
                                # Check for tool result
                                if "result" in parsed_data:
                                    content = parsed_data["result"].get("content", [])
                                    print(f"   ✅ Tool executed successfully with {len(content)} content items")
                                    for i, item in enumerate(content):
                                        print(f"   Content {i}: {str(item)[:200]}...")
                                    return True
                                    
                            except json.JSONDecodeError as e:
                                print(f"   JSON parse error: {e}")
                                continue
                    
                    print("   ❌ No valid tool result found in response")
                    return False
                    
                else:
                    print(f"   ❌ Tool call failed: {tool_response.text}")
                    return False
            else:
                print(f"   ❌ Session initialization failed: {session_response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mcp_connection())
    if result:
        print("\n✅ MCP CONNECTION TEST PASSED")
    else:
        print("\n❌ MCP CONNECTION TEST FAILED")