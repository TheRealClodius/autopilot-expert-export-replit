#!/usr/bin/env python3
"""
Complex Multi-Tool Execution Test

Tests the orchestrator's ability to handle complex prompts requiring multiple tool types:
- Vector search for knowledge base queries
- Perplexity search for real-time web information
- MCP calls for Atlassian data

This simulates the exact user request: "autopilot expert, please perform: 
1 vector search for uipath orchestrator, 1 perplexity search for age of the universe, 1 mcp call for jira tickets"
"""

import asyncio
import time
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService
from services.trace_manager import TraceManager
from models.schemas import ProcessedMessage
from config import Settings

async def test_complex_multi_tool_execution():
    print("🔧 COMPLEX MULTI-TOOL EXECUTION TEST")
    print("=" * 45)
    
    # Initialize services
    memory_service = MemoryService()
    trace_manager = TraceManager()
    
    # Initialize agents
    orchestrator = OrchestratorAgent(memory_service, trace_manager)
    client_agent = ClientAgent()
    
    # Create test message simulating the complex user request
    test_message = ProcessedMessage(
        user_id="U123TEST",
        user_name="TestUser",
        display_name="Test User",
        channel_id="C123TEST", 
        channel_name="test-channel",
        message_ts="1234567890.123",
        thread_ts=None,
        text="autopilot expert, please perform: 1 vector search for uipath orchestrator, 1 perplexity search for age of the universe, 1 mcp call for jira tickets",
        is_dm=False,
        is_mention=True,
        is_thread_reply=False,
        user_title="Test Engineer",
        user_department="Engineering"
    )
    
    print(f"📝 Test Query: {test_message.text}")
    print(f"🎯 Expected Tools: vector_search, perplexity_search, atlassian_search (MCP)")
    
    try:
        # Step 1: Orchestrator Analysis and Planning
        print(f"\n🔍 Step 1: Orchestrator Analysis")
        start_time = time.time()
        
        orchestrator_result = await orchestrator.process_query(test_message)
        
        analysis_time = time.time() - start_time
        print(f"   Duration: {analysis_time:.2f}s")
        print(f"   Success: {orchestrator_result is not None}")
        
        if orchestrator_result:
            # Check what tools were identified/used
            if hasattr(orchestrator_result, 'tools_used'):
                tools_used = orchestrator_result.tools_used
                print(f"   Tools Identified: {tools_used}")
            
            # Look for execution plan details
            if hasattr(orchestrator_result, 'execution_plan'):
                plan = orchestrator_result.execution_plan
                print(f"   Execution Plan: {type(plan)} with {len(plan) if isinstance(plan, (list, dict)) else 'unknown'} steps")
            
            # Check gathered information
            if hasattr(orchestrator_result, 'gathered_information'):
                info = orchestrator_result.gathered_information
                print(f"   Information Sources: {list(info.keys()) if isinstance(info, dict) else 'unknown format'}")
                
                # Count results from each tool type
                vector_results = len(info.get('vector_search_results', [])) if isinstance(info.get('vector_search_results'), list) else 0
                web_results = len(info.get('web_results', [])) if isinstance(info.get('web_results'), list) else 0
                atlassian_results = info.get('atlassian_results', {})
                mcp_results = len(atlassian_results.get('result', [])) if isinstance(atlassian_results, dict) and isinstance(atlassian_results.get('result'), list) else 0
                
                print(f"   Vector Search Results: {vector_results}")
                print(f"   Web Search Results: {web_results}")
                print(f"   MCP Atlassian Results: {mcp_results}")
        
        # Step 2: State Stack Creation and Client Response
        print(f"\n💬 Step 2: Client Response Generation")
        
        if orchestrator_result:
            # Create state stack for client agent
            state_stack = {
                "user_profile": {
                    "user_name": test_message.user_name,
                    "display_name": test_message.display_name,
                    "title": test_message.user_title,
                    "department": test_message.user_department
                },
                "current_query": test_message.text,
                "conversation_history": {"recent_exchanges": []},
                "orchestrator_analysis": {
                    "intent": "Multi-tool demonstration request",
                    "tools_used": getattr(orchestrator_result, 'tools_used', []),
                    "search_results": getattr(orchestrator_result, 'gathered_information', {}).get('vector_search_results', []),
                    "web_results": getattr(orchestrator_result, 'gathered_information', {}).get('web_results', []),
                    "atlassian_results": getattr(orchestrator_result, 'gathered_information', {}).get('atlassian_results', {})
                },
                "trace_id": getattr(orchestrator_result, 'trace_id', None)
            }
            
            client_start = time.time()
            client_response = await client_agent.generate_response(state_stack)
            client_time = time.time() - client_start
            
            print(f"   Duration: {client_time:.2f}s")
            print(f"   Response Length: {len(client_response) if client_response else 0} characters")
            
            if client_response:
                # Show first part of response
                preview = client_response[:200] + "..." if len(client_response) > 200 else client_response
                print(f"   Response Preview: {preview}")
        
        # Step 3: Analysis Summary
        total_time = analysis_time + (client_time if 'client_time' in locals() else 0)
        print(f"\n📊 Execution Summary:")
        print(f"✅ Total Processing Time: {total_time:.2f}s")
        print(f"✅ Orchestrator Analysis: {'Success' if orchestrator_result else 'Failed'}")
        print(f"✅ Client Response: {'Generated' if 'client_response' in locals() and client_response else 'Failed'}")
        
        # Tool usage verification
        if orchestrator_result and hasattr(orchestrator_result, 'gathered_information'):
            info = orchestrator_result.gathered_information
            tools_executed = []
            if info.get('vector_search_results'):
                tools_executed.append("vector_search")
            if info.get('web_results'):
                tools_executed.append("perplexity_search")
            if info.get('atlassian_results'):
                tools_executed.append("mcp_atlassian")
                
            print(f"✅ Tools Successfully Executed: {', '.join(tools_executed) if tools_executed else 'None'}")
            print(f"🎯 Multi-tool orchestration: {'SUCCESS' if len(tools_executed) >= 2 else 'PARTIAL'}")
        
    except Exception as e:
        print(f"❌ Test Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complex_multi_tool_execution())