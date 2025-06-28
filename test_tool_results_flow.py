#!/usr/bin/env python3
"""
Test Tool Results Flow - Verify that tool call results properly flow from orchestrator to client agent

This test addresses the specific issue where:
1. Tool calls execute in LangSmith (visible as 2 tool calls with responses)
2. But client agent doesn't see the results in state stack
3. Client agent only sees basic orchestrator analysis without search results
"""

import asyncio
import json
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_tool_results_visibility():
    """Test that tool call results are properly visible to client agent"""
    
    print("🔧 Testing Tool Results Flow from Orchestrator to Client Agent")
    print("="*70)
    
    try:
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create test message that should trigger vector search
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST",
            text="Autopilot is an AI, right?",  # This should trigger knowledge base search
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
        
        print(f"📝 Query: {test_message.text}")
        print()
        
        # Step 1: Test orchestrator analysis
        print("1️⃣ Testing Orchestrator Analysis:")
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        
        if execution_plan:
            print(f"✅ Execution plan created:")
            print(f"   Analysis: {execution_plan.get('analysis', 'No analysis')[:100]}...")
            print(f"   Tools needed: {execution_plan.get('tools_needed', [])}")
            print(f"   Vector queries: {execution_plan.get('vector_queries', [])}")
        else:
            print("❌ No execution plan generated")
            return
        
        print()
        
        # Step 2: Test tool execution
        print("2️⃣ Testing Tool Execution:")
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        
        vector_results = gathered_info.get("vector_results", [])
        print(f"✅ Vector search executed:")
        print(f"   Results found: {len(vector_results)}")
        
        if vector_results:
            for i, result in enumerate(vector_results[:2], 1):
                content = result.get("content", "")[:100]
                score = result.get("score", 0.0)
                print(f"   Result {i}: {content}... (score: {score:.3f})")
        else:
            print("   No vector results found")
        
        print()
        
        # Step 3: Test state stack building
        print("3️⃣ Testing State Stack Building:")
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        
        # Check if search results are properly included
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        search_results_in_state = orchestrator_analysis.get("search_results", [])
        
        print(f"✅ State stack built:")
        print(f"   Query included: {bool(state_stack.get('query'))}")
        print(f"   Orchestrator analysis: {bool(orchestrator_analysis)}")
        print(f"   Search results in state: {len(search_results_in_state)}")
        
        if search_results_in_state:
            print(f"   First result preview: {search_results_in_state[0].get('content', '')[:100]}...")
        
        print()
        
        # Step 4: Test client agent state processing
        print("4️⃣ Testing Client Agent State Processing:")
        
        # Use the client agent's formatting method to see what it receives
        client_agent = orchestrator.client_agent
        formatted_context = client_agent._format_state_stack_context(state_stack)
        
        # Check if search results appear in the formatted context
        context_lines = formatted_context.split('\n')
        search_result_lines = [line for line in context_lines if 'Vector Search Results:' in line or line.strip().startswith(('1.', '2.', '3.'))]
        
        print(f"✅ Client agent context formatted:")
        print(f"   Total context lines: {len(context_lines)}")
        print(f"   Search result lines: {len(search_result_lines)}")
        
        if search_result_lines:
            print("   Search results found in context:")
            for line in search_result_lines[:5]:  # Show first 5 relevant lines
                print(f"     {line.strip()}")
        else:
            print("   ❌ NO SEARCH RESULTS FOUND IN CLIENT CONTEXT!")
            print("   🔍 Looking for any mention of search results...")
            
            # Debug: Show context sections that mention search
            debug_lines = [line for line in context_lines if any(keyword in line.lower() for keyword in ['search', 'result', 'vector', 'collated'])]
            if debug_lines:
                print("   Debug - Lines mentioning search/results:")
                for line in debug_lines:
                    print(f"     {line.strip()}")
        
        print()
        
        # Step 5: Show the problem area if results are missing
        if not search_result_lines:
            print("5️⃣ DEBUGGING - State Stack Structure:")
            print("   gathered_info structure:")
            print(f"     keys: {list(gathered_info.keys())}")
            print(f"     vector_results count: {len(gathered_info.get('vector_results', []))}")
            print()
            print("   state_stack.orchestrator_analysis structure:")
            print(f"     keys: {list(orchestrator_analysis.keys())}")
            print(f"     search_results count: {len(orchestrator_analysis.get('search_results', []))}")
            print()
            
            # Show first few lines of formatted context for debugging
            print("   First 20 lines of client agent context:")
            for i, line in enumerate(context_lines[:20], 1):
                print(f"   {i:2}: {line}")
        
        print()
        print("🎯 Test Summary:")
        print(f"   Vector search executed: {len(vector_results) > 0}")
        print(f"   Results in state stack: {len(search_results_in_state) > 0}")
        print(f"   Results visible to client: {len(search_result_lines) > 0}")
        
        if len(vector_results) > 0 and len(search_results_in_state) > 0 and len(search_result_lines) > 0:
            print("   ✅ TOOL RESULTS FLOW WORKING CORRECTLY!")
        else:
            print("   ❌ TOOL RESULTS FLOW BROKEN - NEEDS FIXING")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tool_results_visibility())