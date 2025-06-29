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
        async with httpx.AsyncClient(timeout=45.0) as client:
            
            # Step 1: Initialize the MCP session properly
            print("🔧 Initializing MCP session...")
            
            # Check if server is responding at all
            try:
                health_response = await client.get(f"{mcp_url}/health", timeout=10)
                print(f"Health check: {health_response.status_code}")
            except:
                print("Health endpoint not available")
            
            # Try tools/list without initialization first (some servers support this)
            print("\n📋 Checking available tools...")
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            tools_response = await client.post(f"{mcp_url}/mcp", json=tools_request)
            print(f"Tools list status: {tools_response.status_code}")
            
            if tools_response.status_code == 200:
                try:
                    tools_data = tools_response.json()
                    print("Response structure:")
                    print(json.dumps(tools_data, indent=2)[:500] + "..." if len(str(tools_data)) > 500 else json.dumps(tools_data, indent=2))
                    
                    # Check if we have tools in the response
                    if 'result' in tools_data and tools_data['result'] and 'tools' in tools_data['result']:
                        tools = tools_data['result']['tools']
                        print(f"\n✅ Found {len(tools)} tools:")
                        
                        for tool in tools:
                            name = tool.get('name', 'unnamed')
                            desc = tool.get('description', 'No description')
                            print(f"  📌 {name}: {desc}")
                            
                            # Check if it's an Atlassian tool
                            if any(keyword in name.lower() for keyword in ['jira', 'confluence', 'atlassian']):
                                print(f"    🎯 Atlassian tool detected!")
                                
                                # Try to get the input schema
                                if 'inputSchema' in tool:
                                    schema = tool['inputSchema']
                                    if 'properties' in schema:
                                        props = list(schema['properties'].keys())
                                        print(f"    📝 Parameters: {', '.join(props[:5])}")
                        
                        # Test one Atlassian tool if available
                        atlassian_tools = [t for t in tools if any(keyword in t['name'].lower() for keyword in ['jira', 'confluence'])]
                        if atlassian_tools:
                            print(f"\n🔍 Testing first Atlassian tool: {atlassian_tools[0]['name']}")
                            await test_tool_call(client, mcp_url, atlassian_tools[0])
                        else:
                            print("\n❌ No Atlassian tools found in the list")
                            print("Available tools are:", [t['name'] for t in tools])
                            
                    else:
                        print("❌ No tools found in response or unexpected format")
                        
                except Exception as e:
                    print(f"❌ Error parsing tools response: {e}")
                    print(f"Raw response: {tools_response.text[:300]}")
            else:
                print(f"❌ Tools request failed: {tools_response.text[:300]}")
                
    except Exception as e:
        print(f"❌ Error discovering tools: {e}")

async def test_tool_call(client, mcp_url, tool_info):
    """Test calling a specific tool"""
    tool_name = tool_info['name']
    
    # Create a simple test based on tool name
    if 'jira' in tool_name.lower() and 'search' in tool_name.lower():
        test_args = {"jql": "project = AUTOPILOT", "limit": 2}
    elif 'confluence' in tool_name.lower() and 'search' in tool_name.lower():
        test_args = {"query": "autopilot", "limit": 2}
    elif 'jira' in tool_name.lower() and 'get' in tool_name.lower():
        test_args = {"issue_key": "AUTOPILOT-1"}
    else:
        print(f"  ⚠️ Skipping {tool_name} - unknown test pattern")
        return
    
    print(f"  🔧 Testing {tool_name} with args: {test_args}")
    
    test_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": test_args
        }
    }
    
    try:
        response = await client.post(f"{mcp_url}/mcp", json=test_request)
        print(f"  📊 Tool call status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                print(f"  ✅ Tool working! Result preview: {str(data['result'])[:100]}...")
            elif 'error' in data:
                error = data['error']
                print(f"  ❌ Tool error: {error.get('message', error)}")
            else:
                print(f"  ⚠️ Unexpected response: {data}")
        else:
            print(f"  ❌ HTTP error: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ Exception testing tool: {e}")

if __name__ == "__main__":
    asyncio.run(discover_mcp_tools())