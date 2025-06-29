#!/usr/bin/env python3
"""
Test MCP server with Atlassian credentials to verify real UiPath data retrieval
"""
import asyncio
import httpx
from tools.atlassian_tool import AtlassianTool
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage

async def test_mcp_atlassian():
    """Test MCP server with Atlassian credentials"""
    
    print("🔧 Testing MCP Atlassian Integration...")
    
    # Test 1: AtlassianTool discovery
    print("\n1. Testing AtlassianTool discovery:")
    atlassian_tool = AtlassianTool()
    tools = await atlassian_tool.discover_available_tools()
    
    print(f"✅ Connected to MCP server: {atlassian_tool.mcp_server_url}")
    print(f"✅ Discovered {len(tools)} total tools")
    print(f"✅ Atlassian tools: {atlassian_tool.available_tools}")
    
    # Test 2: Orchestrator using dynamic tools
    print("\n2. Testing Orchestrator with dynamic tools:")
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Create a test message for UiPath Autopilot query
    test_message = ProcessedMessage(
        text="Show me open bugs in the AUTOPILOT project",
        user_id="test_user",
        user_name="Test User",
        channel_id="test_channel", 
        channel_name="test-channel",
        message_ts="1234567890.123",
        thread_ts=None,
        is_dm=False,
        thread_context=None
    )
    
    # Test orchestrator analysis with dynamic tools
    analysis = await orchestrator._analyze_query_and_plan(test_message)
    
    if analysis:
        print(f"✅ Orchestrator analysis completed")
        if 'atlassian_actions' in analysis:
            actions = analysis['atlassian_actions']
            print(f"✅ Generated {len(actions)} MCP actions:")
            for i, action in enumerate(actions, 1):
                tool_name = action.get('mcp_tool', 'unknown')
                print(f"   {i}. Tool: {tool_name}")
                print(f"      Args: {action.get('arguments', {})}")
        else:
            print("❌ No atlassian_actions found in analysis")
    else:
        print("❌ Orchestrator analysis failed")
    
    # Test 3: Quick health check
    print("\n3. Testing remote MCP server health:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{atlassian_tool.mcp_server_url}/health")
            if response.status_code == 200:
                print(f"✅ MCP server health check passed: {response.status_code}")
            else:
                print(f"⚠️  MCP server health check returned: {response.status_code}")
    except Exception as e:
        print(f"❌ MCP server health check failed: {e}")
    
    return tools

if __name__ == "__main__":
    asyncio.run(test_mcp_atlassian())