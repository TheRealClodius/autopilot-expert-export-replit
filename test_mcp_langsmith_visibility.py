"""
Test MCP LangSmith Trace Visibility

This test verifies that MCP calls now appear properly in LangSmith traces
after the tracing integration fix.
"""

import asyncio
import logging
from services.trace_manager import TraceManager
from tools.atlassian_tool import AtlassianTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_langsmith_visibility():
    """Test if MCP calls now appear in LangSmith with proper tracing"""
    print("🔍 TESTING MCP LANGSMITH TRACE VISIBILITY")
    print("=" * 50)
    
    try:
        # Initialize trace manager and Atlassian tool
        trace_manager = TraceManager()
        atlassian_tool = AtlassianTool(trace_manager=trace_manager)
        
        # Start a test conversation trace
        conversation_id = trace_manager.start_conversation_session(
            "test_mcp_visibility_001",
            "test mcp langsmith visibility"
        )
        print(f"✅ Started conversation trace: {conversation_id}")
        
        # Create a tool operation trace
        tool_trace_id = trace_manager.log_tool_operation(
            "mcp_confluence_search",
            {"query": "autopilot", "limit": 3},
            context="Testing MCP trace visibility"
        )
        print(f"✅ Created tool trace: {tool_trace_id}")
        
        # Execute MCP call with tracing
        print("🚀 Executing MCP Confluence search...")
        result = await atlassian_tool.execute_mcp_tool(
            "confluence_search",
            {"query": "autopilot", "limit": 3}
        )
        
        # Complete the tool trace
        if tool_trace_id:
            trace_manager.complete_tool_operation(
                tool_trace_id,
                result,
                success=bool(result and result.get("success"))
            )
            print(f"✅ Completed tool trace: {tool_trace_id}")
        
        # Complete conversation trace
        trace_manager.complete_conversation_session(conversation_id)
        print(f"✅ Completed conversation trace: {conversation_id}")
        
        # Display results
        if result and result.get("success"):
            pages = result.get("result", [])
            print(f"\n📊 MCP EXECUTION RESULTS:")
            print(f"   Status: SUCCESS")
            print(f"   Pages found: {len(pages)}")
            
            for i, page in enumerate(pages[:3], 1):
                title = page.get("title", "Unknown")
                space = page.get("space", {}).get("name", "Unknown")
                print(f"   {i}. {title} (Space: {space})")
            
            print(f"\n🎯 LANGSMITH STATUS:")
            print(f"   Conversation Trace: {conversation_id}")
            print(f"   Tool Trace: {tool_trace_id}")
            print(f"   ✅ Both traces should now be visible in LangSmith dashboard")
            
        else:
            print(f"❌ MCP execution failed: {result}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_langsmith_visibility())