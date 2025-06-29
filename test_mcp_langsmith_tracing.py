#!/usr/bin/env python3
"""
Test MCP Tool LangSmith Tracing Integration

Verify that MCP tool operations are properly traced in LangSmith.
"""

import asyncio
import json
from tools.atlassian_tool import AtlassianTool
from services.trace_manager import TraceManager

async def test_mcp_langsmith_tracing():
    """Test MCP tool with LangSmith tracing"""
    print("🔍 Testing MCP Tool LangSmith Tracing")
    print("=" * 50)
    
    # Initialize trace manager
    trace_manager = TraceManager()
    print(f"✅ TraceManager initialized (enabled: {trace_manager.is_enabled()})")
    
    # Start a conversation session for tracing context
    session_id = await trace_manager.start_conversation_session(
        user_id="test_user",
        message="Test MCP tracing",
        channel_id="test_channel",
        message_ts="test_ts"
    )
    print(f"✅ Started conversation session: {session_id}")
    
    # Initialize AtlassianTool with trace manager
    atlassian_tool = AtlassianTool(trace_manager=trace_manager)
    print(f"✅ AtlassianTool initialized with tracing")
    print(f"   MCP Server URL: {atlassian_tool.mcp_server_url}")
    print(f"   Available: {atlassian_tool.available}")
    
    # Test MCP tool execution with tracing
    print("\n🔍 Testing Confluence Search with LangSmith Tracing:")
    
    try:
        result = await atlassian_tool.execute_mcp_tool(
            tool_name="confluence_search",
            arguments={
                "query": "Autopilot for Everyone",
                "limit": 2
            }
        )
        
        print("✅ MCP Tool Execution Completed")
        print(f"   Result type: {type(result)}")
        print(f"   Success: {result.get('success', False)}")
        
        if result.get("success"):
            mcp_result = result.get("result", {})
            if isinstance(mcp_result, list):
                print(f"   Found {len(mcp_result)} pages")
            elif isinstance(mcp_result, dict) and "result" in mcp_result:
                pages = mcp_result.get("result", [])
                print(f"   Found {len(pages)} pages")
                for i, page in enumerate(pages[:2], 1):
                    title = page.get("title", "Unknown")
                    print(f"   {i}. {title}")
        else:
            print(f"   Error: {result.get('error', 'unknown')}")
            print(f"   Message: {result.get('message', 'No message')}")
            
    except Exception as e:
        print(f"❌ MCP Tool Execution Failed: {e}")
    
    # Complete the conversation session
    await trace_manager.complete_conversation_session(
        final_response="MCP tracing test completed"
    )
    print(f"✅ Completed conversation session")
    
    print("\n📊 LangSmith Tracing Results:")
    print("- Check your LangSmith dashboard for the trace")
    print("- Look for 'mcp_atlassian_confluence_search' tool operation")
    print("- Trace should include inputs, outputs, duration, and any errors")
    print("- Parent trace: 'slack_conversation_test_channel'")

async def main():
    await test_mcp_langsmith_tracing()

if __name__ == "__main__":
    asyncio.run(main())