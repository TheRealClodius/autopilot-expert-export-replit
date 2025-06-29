#!/usr/bin/env python3
"""
Test orchestrator MCP integration end-to-end
"""

import asyncio
import sys
sys.path.append('.')

from agents.orchestrator_agent import OrchestratorAgent
from tools.atlassian_tool import AtlassianTool
from tools.vector_search import VectorSearchTool
from tools.perplexity_search import PerplexitySearchTool
from tools.outlook_meeting import OutlookMeetingTool
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker
from models.schemas import ProcessedMessage

async def test_orchestrator_mcp():
    """Test complete orchestrator to MCP integration"""
    print("🧪 Testing Orchestrator MCP Integration...")
    
    # Initialize services
    memory_service = MemoryService()
    progress_tracker = ProgressTracker()
    
    # Initialize orchestrator (tools are initialized internally)
    orchestrator = OrchestratorAgent(
        memory_service=memory_service,
        progress_tracker=progress_tracker
    )
    
    # Test tool discovery
    print("\n1. Testing Tool Discovery:")
    discovered_tools = await orchestrator.discover_and_update_tools()
    print(f"✅ Discovered {len(discovered_tools)} tools")
    print(f"✅ Atlassian tools available: {orchestrator.atlassian_tool.available_tools}")
    
    # Test query analysis and plan generation
    print("\n2. Testing Query Analysis:")
    test_message = ProcessedMessage(
        channel_id="C087QKECFKQ",
        user_id="U12345TEST", 
        text="Find all open bugs in project AUTOPILOT",
        message_ts="1640995200.001500",
        thread_ts=None,
        user_name="test_user",
        user_first_name="Test",
        user_display_name="Test User", 
        user_title="Software Engineer",
        user_department="Engineering",
        channel_name="general",
        is_dm=False,
        thread_context=""
    )
    
    execution_plan = await orchestrator._analyze_query_and_plan(test_message)
    print(f"✅ Generated execution plan: {execution_plan is not None}")
    
    if execution_plan:
        print(f"   Analysis: {execution_plan.get('analysis', 'N/A')[:100]}...")
        atlassian_actions = execution_plan.get('atlassian_actions', [])
        print(f"   Atlassian actions: {len(atlassian_actions)}")
        
        if atlassian_actions:
            first_action = atlassian_actions[0]
            print(f"   First action tool: {first_action.get('mcp_tool')}")
            print(f"   First action args: {first_action.get('arguments')}")
            
            # Test actual MCP execution
            print("\n3. Testing MCP Tool Execution:")
            try:
                result = await orchestrator.atlassian_tool.execute_mcp_tool(
                    first_action.get('mcp_tool'),
                    first_action.get('arguments', {})
                )
                print(f"✅ MCP execution successful: {result.get('success', False)}")
                
                if result.get('success'):
                    content = result.get('result', {}).get('content', {})
                    print(f"   Result type: {type(content)}")
                    if isinstance(content, dict):
                        print(f"   Keys: {list(content.keys())}")
                        if 'message' in content:
                            print(f"   Message: {content['message'][:100]}...")
                            
            except Exception as e:
                print(f"❌ MCP execution failed: {e}")
    
    print("\n🎉 Integration test complete!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_mcp())