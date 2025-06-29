#!/usr/bin/env python3
"""
Test MCP Parameter Fix Verification

Test if the orchestrator prompt fix resolves the parameter validation issue
"""

import asyncio
import json
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.trace_manager import TraceManager
from models.schemas import ProcessedMessage

async def test_mcp_fix():
    """Test if MCP parameter fix works"""
    
    print("=" * 80)
    print("🔧 TESTING MCP PARAMETER FIX")
    print("=" * 80)
    
    # Initialize services
    memory_service = MemoryService()
    trace_manager = TraceManager()
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        memory_service=memory_service,
        trace_manager=trace_manager
    )
    
    # Test queries that should trigger MCP calls
    test_queries = [
        "Find me information about Autopilot for Everyone",
        "What Jira tickets are related to UiPath design system?",
        "Show me Confluence pages about Autopilot templates"
    ]
    
    for query in test_queries:
        print(f"\n📝 Testing Query: {query}")
        
        # Create test message
        test_message = ProcessedMessage(
            text=query,
            user_id="test_user",
            user_name="Test User",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Test Title",
            user_department="Test Dept",
            channel_id="test_channel",
            channel_name="test", 
            message_ts="test_ts",
            is_dm=False,
            is_mention=True,
            is_thread_reply=False
        )
        
        try:
            print("🧠 Analyzing query with orchestrator...")
            result = await orchestrator.process_query(test_message)
            
            if result and "orchestrator_analysis" in result:
                analysis = result["orchestrator_analysis"]
                
                # Check for atlassian tool usage
                tools_used = analysis.get("tools_used", [])
                print(f"   Tools used: {tools_used}")
                
                if "atlassian_search" in tools_used:
                    print("   ✅ Orchestrator correctly routed to MCP Atlassian")
                    
                    # Check search results
                    search_results = analysis.get("search_results", [])
                    if search_results:
                        print(f"   📊 Retrieved {len(search_results)} results:")
                        for i, result in enumerate(search_results[:3]):
                            title = result.get("title", "No title")
                            print(f"      {i+1}. {title}")
                    else:
                        print("   ⚠️  No search results returned")
                        
                    # Check for any errors
                    if "errors" in analysis:
                        print(f"   ❌ Errors: {analysis['errors']}")
                else:
                    print("   ⚠️  Orchestrator did not use MCP Atlassian tools")
                    
            else:
                print("   ❌ No orchestrator analysis returned")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("🎯 MCP PARAMETER FIX RESULTS")
    print("=" * 80)
    print("If the fix worked, you should see:")
    print("1. ✅ MCP Atlassian tools being used")
    print("2. 📊 Real UiPath data being retrieved")
    print("3. ❌ No more 'jql is a required property' errors")

if __name__ == "__main__":
    asyncio.run(test_mcp_fix())