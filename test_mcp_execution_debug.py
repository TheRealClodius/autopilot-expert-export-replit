#!/usr/bin/env python3
"""
Debug MCP tool execution to identify why Jira searches are failing
"""
import asyncio
import httpx
from tools.atlassian_tool import AtlassianTool

async def test_mcp_execution():
    """Test MCP tool execution step by step"""
    
    print("🔧 Testing MCP Execution Debug...")
    
    # Test 1: MCP Server Health
    print("\n1. Testing MCP Server Health:")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get("https://remote-mcp-server-andreiclodius.replit.app/health")
            print(f"✅ Health Status: {response.status_code}")
            print(f"✅ Health Response: {response.json()}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
    
    # Test 2: Tool Discovery
    print("\n2. Testing Tool Discovery:")
    atlassian_tool = AtlassianTool()
    tools = await atlassian_tool.discover_available_tools()
    print(f"✅ Discovered tools: {len(tools)}")
    print(f"✅ Available tools: {atlassian_tool.available_tools}")
    
    # Test 3: Direct MCP Tool Execution
    print("\n3. Testing Direct MCP Tool Execution:")
    try:
        # Test simple Jira search
        result = await atlassian_tool.execute_mcp_tool(
            "get_jira_issues",
            {"jql": "project = AUTOPILOT AND issuetype = Bug", "limit": 5}
        )
        print(f"✅ MCP Tool Result: {result}")
        
        if result.get("status") == "error":
            print(f"❌ MCP Tool Error: {result.get('error', 'Unknown error')}")
        elif result.get("result"):
            print(f"✅ Found {len(result.get('result', []))} results")
        else:
            print("⚠️  No results returned")
            
    except Exception as e:
        print(f"❌ MCP Tool Execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Alternative JQL Query
    print("\n4. Testing Alternative JQL Query:")
    try:
        # Try a broader search
        result = await atlassian_tool.execute_mcp_tool(
            "get_jira_issues", 
            {"jql": "text ~ 'autopilot'", "limit": 3}
        )
        print(f"✅ Alternative Query Result: {result}")
        
        if result.get("result"):
            print(f"✅ Found {len(result.get('result', []))} results with broader search")
            
    except Exception as e:
        print(f"❌ Alternative query failed: {e}")
    
    # Test 5: Get Atlassian Status
    print("\n5. Testing Atlassian Status:")
    try:
        result = await atlassian_tool.execute_mcp_tool("get_atlassian_status", {})
        print(f"✅ Status Result: {result}")
    except Exception as e:
        print(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_execution())