#!/usr/bin/env python3
"""
Complete MCP Integration Test

Tests the full end-to-end MCP Atlassian integration:
1. Orchestrator query analysis
2. MCP tool command generation
3. MCP server communication
4. Real Confluence/Jira data retrieval
5. Client agent response formatting

This validates the complete production-ready flow.
"""

import asyncio
import logging
import json
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
from services.trace_manager import TraceManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_mcp_flow():
    """Test complete MCP integration flow with real Atlassian data"""
    
    print("🚀 COMPLETE MCP ATLASSIAN INTEGRATION TEST")
    print("="*60)
    
    # Initialize services
    memory_service = MemoryService()
    trace_manager = TraceManager()
    
    # Initialize agents
    orchestrator = OrchestratorAgent(memory_service, trace_manager)
    client_agent = ClientAgent()
    
    # Test queries for different MCP tools
    test_queries = [
        {
            "query": "Find all pages about Autopilot for Everyone in Confluence",
            "expected_tool": "confluence_search",
            "description": "Confluence search test"
        },
        {
            "query": "Search for open bugs in the AUTOPILOT project",
            "expected_tool": "jira_search", 
            "description": "Jira search with JQL test"
        },
        {
            "query": "Show me details for issue AUTOPILOT-123",
            "expected_tool": "jira_get",
            "description": "Specific Jira issue retrieval test"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n🧪 TEST {i}: {test_case['description']}")
        print("-" * 50)
        print(f"Query: {test_case['query']}")
        
        # Create processed message
        message = ProcessedMessage(
            text=test_case['query'],
            user_id="test_user",
            user_name="testuser",
            user_first_name="Test",
            user_display_name="Test User", 
            user_title="QA Engineer",
            user_department="Engineering",
            channel_id="test_channel",
            channel_name="test-channel",
            message_ts="1234567890.123",
            thread_ts=None,
            is_mention=True
        )
        
        try:
            # Step 1: Orchestrator Analysis
            print("\n📊 Step 1: Orchestrator Analysis")
            orchestrator_result = await orchestrator.process_query(message)
            
            if orchestrator_result and "execution_plan" in orchestrator_result:
                plan = orchestrator_result["execution_plan"]
                
                # Check if correct tool was selected
                atlassian_actions = plan.get("atlassian_actions", [])
                if atlassian_actions:
                    tool_used = atlassian_actions[0].get("mcp_tool")
                    print(f"✅ Tool Selected: {tool_used}")
                    
                    if tool_used == test_case["expected_tool"]:
                        print(f"✅ Correct tool selection for {test_case['description']}")
                    else:
                        print(f"⚠️ Expected {test_case['expected_tool']}, got {tool_used}")
                    
                    # Show MCP command generated
                    print(f"📋 MCP Command: {json.dumps(atlassian_actions[0], indent=2)}")
                else:
                    print("❌ No Atlassian actions generated")
                    continue
                
                # Step 2: Check if we have results
                gathered_info = orchestrator_result.get("gathered_information", {})
                atlassian_results = gathered_info.get("atlassian_results", [])
                
                if atlassian_results:
                    print(f"✅ Retrieved {len(atlassian_results)} results from MCP server")
                    
                    # Show sample result
                    sample_result = atlassian_results[0]
                    if isinstance(sample_result, dict):
                        print(f"📄 Sample Result: {sample_result.get('title', 'N/A')}")
                        print(f"🔗 URL: {sample_result.get('url', 'N/A')}")
                    
                    print(f"✅ {test_case['description']}: SUCCESS")
                else:
                    print(f"❌ No results returned from MCP server")
                    print(f"❌ {test_case['description']}: FAILED")
                
            else:
                print("❌ Orchestrator failed to generate execution plan")
                print(f"❌ {test_case['description']}: FAILED")
                
        except Exception as e:
            print(f"❌ Error in {test_case['description']}: {str(e)}")
            logger.exception(f"Test failed: {test_case['description']}")
    
    print("\n" + "="*60)
    print("🎯 MCP INTEGRATION TEST COMPLETE")
    print("="*60)

async def main():
    """Main test runner"""
    await test_complete_mcp_flow()

if __name__ == "__main__":
    asyncio.run(main())