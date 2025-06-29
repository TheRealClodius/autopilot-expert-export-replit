"""
Test script to debug why Jira issue links aren't showing up as clickable in Slack.
This will trace the data flow from Atlassian tool → Orchestrator → Client Agent.
"""

import asyncio
import json
from tools.atlassian_tool import AtlassianTool
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService
from services.trace_manager import TraceManager
from models.schemas import ProcessedMessage

async def debug_link_flow():
    """Debug the complete flow to see where links are lost"""
    
    print("🔍 DEBUGGING JIRA LINK FLOW")
    print("=" * 50)
    
    # Step 1: Test Atlassian tool directly
    print("\n1. Testing Atlassian Tool Direct Response:")
    print("-" * 40)
    
    atlassian_tool = AtlassianTool()
    
    # Test a Jira search that should return issues with URLs
    test_result = await atlassian_tool.search_jira_issues(
        query="project = DESIGN AND assignee = 'Andrei Clodius'",
        max_results=3
    )
    
    if "jira_search_results" in test_result:
        issues = test_result["jira_search_results"]["issues"]
        for issue in issues[:3]:
            print(f"Issue Key: {issue.get('key')}")
            print(f"URL: {issue.get('url')}")
            print(f"Summary: {issue.get('summary', '')[:50]}...")
            print()
    else:
        print(f"Atlassian tool error: {test_result}")
    
    # Step 2: Test orchestrator with Atlassian action
    print("\n2. Testing Orchestrator State Stack:")
    print("-" * 40)
    
    memory_service = MemoryService()
    trace_manager = TraceManager()
    orchestrator = OrchestratorAgent(memory_service, trace_manager=trace_manager)
    
    # Mock a Slack message asking for Jira issues
    message = ProcessedMessage(
        channel_id="C123",
        user_id="U123",
        text="Who is currently assigned to the most Jira tickets?",
        timestamp="123.456",
        message_type="channel_message",
        user_name="Test User",
        channel_name="test-channel"
    )
    
    # Process through orchestrator
    state_stack = await orchestrator.process_query(message)
    
    print("State Stack Keys:", list(state_stack.keys()))
    
    if "orchestrator_analysis" in state_stack:
        analysis = state_stack["orchestrator_analysis"]
        if "atlassian_results" in analysis:
            print("\nAtlassian Results Found in State Stack:")
            atlassian_data = analysis["atlassian_results"]
            print(json.dumps(atlassian_data, indent=2)[:500] + "...")
        else:
            print("No atlassian_results in orchestrator analysis")
            print("Analysis keys:", list(analysis.keys()))
    else:
        print("No orchestrator_analysis in state stack")
    
    # Step 3: Test client agent formatting
    print("\n3. Testing Client Agent Link Formatting:")
    print("-" * 40)
    
    client_agent = ClientAgent()
    
    # Test direct formatting with mock atlassian data
    mock_state_stack = {
        "current_query": "Who is currently assigned to the most Jira tickets?",
        "conversation_history": {"recent_exchanges": []},
        "orchestrator_analysis": {
            "intent": "Find user with most Jira assignments",
            "atlassian_results": [
                {
                    "action_type": "search_jira_issues", 
                    "success": True,
                    "result": {
                        "jira_search_results": {
                            "query": "project = DESIGN",
                            "total_found": 3,
                            "issues": [
                                {
                                    "key": "DESIGN-10321",
                                    "summary": "Messages component issue",
                                    "status": "In Design",
                                    "url": "https://uipath.atlassian.net/browse/DESIGN-10321"
                                },
                                {
                                    "key": "DESIGN-10572", 
                                    "summary": "Baseline component Messages",
                                    "status": "Closed",
                                    "url": "https://uipath.atlassian.net/browse/DESIGN-10572"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    }
    
    response = await client_agent.generate_response(mock_state_stack)
    if response:
        print("Client Agent Response:")
        print(response.get("text", "No text found"))
        
        # Check if links are in the response
        response_text = response.get("text", "")
        if "https://uipath.atlassian.net/browse/" in response_text:
            print("\n✅ URLs are present in client response!")
        else:
            print("\n❌ URLs are missing from client response!")
            
        if "<https://" in response_text and "|" in response_text and ">" in response_text:
            print("✅ Slack link format detected!")
        else:
            print("❌ No Slack link format found!")
    else:
        print("Client agent returned None")

if __name__ == "__main__":
    asyncio.run(debug_link_flow())