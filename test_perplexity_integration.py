#!/usr/bin/env python3
"""
Test Perplexity Integration - Complete End-to-End Verification

This script tests the complete Perplexity integration from query analysis 
through web search execution to response generation.
"""

import asyncio
import json
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_perplexity_complete_flow():
    """Test complete flow including Perplexity web search integration"""
    
    print("🌐 Testing Perplexity Integration - Complete End-to-End Flow")
    print("="*70)
    
    try:
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create test message that should trigger Perplexity search
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST",
            text="What are the latest trends in AI automation for 2025?",  # Future-looking query for web search
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="AI Engineer",
            user_department="Engineering",
            channel_name="general",
            is_dm=False,
            thread_context=""
        )
        
        print(f"📝 Query: {test_message.text}")
        print()
        
        # Step 1: Test orchestrator analysis
        print("1️⃣ Testing Orchestrator Query Analysis:")
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        
        if execution_plan:
            print(f"✅ Execution plan created:")
            print(f"   Analysis: {execution_plan.get('analysis', 'No analysis')[:100]}...")
            print(f"   Tools needed: {execution_plan.get('tools_needed', [])}")
            print(f"   Perplexity queries: {execution_plan.get('perplexity_queries', [])}")
            
            # Check if Perplexity is correctly selected
            perplexity_selected = "perplexity_search" in execution_plan.get('tools_needed', [])
            print(f"   Perplexity correctly selected: {'✅' if perplexity_selected else '❌'}")
        else:
            print("❌ Failed to create execution plan")
            return
        
        print()
        
        # Step 2: Test plan execution with web search
        print("2️⃣ Testing Plan Execution (Web Search):")
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        
        web_results = gathered_info.get("perplexity_results", [])
        vector_results = gathered_info.get("vector_results", [])
        
        print(f"✅ Plan execution completed:")
        print(f"   Vector search results: {len(vector_results)}")
        print(f"   Web search results: {len(web_results)}")
        
        if web_results:
            first_result = web_results[0]
            print(f"   First web result preview:")
            print(f"     Query: {first_result.get('query', 'N/A')}")
            print(f"     Content length: {len(first_result.get('content', ''))}")
            print(f"     Citations: {len(first_result.get('citations', []))}")
            print(f"     Search time: {first_result.get('search_time', 0):.2f}s")
        
        print()
        
        # Step 3: Test state stack building
        print("3️⃣ Testing State Stack Building:")
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        state_web_results = orchestrator_analysis.get("web_results", [])
        
        print(f"✅ State stack built:")
        print(f"   Query: {state_stack.get('query', 'N/A')}")
        print(f"   User: {state_stack.get('user', {}).get('first_name', 'N/A')}")
        print(f"   Web results in state: {len(state_web_results)}")
        print(f"   Tools used in analysis: {orchestrator_analysis.get('tools_used', [])}")
        
        print()
        
        # Step 4: Test client agent formatting
        print("4️⃣ Testing Client Agent Context Formatting:")
        client_agent = orchestrator.client_agent
        formatted_context = client_agent._format_state_stack_context(state_stack)
        
        # Check if web results appear in the formatted context
        has_web_results = "Real-Time Web Search Results:" in formatted_context
        
        print(f"✅ Client agent context formatted:")
        print(f"   Context length: {len(formatted_context)} characters")
        print(f"   Web results section found: {'✅' if has_web_results else '❌'}")
        
        if has_web_results:
            # Show preview of web results section
            lines = formatted_context.split('\n')
            showing = False
            web_lines = []
            for line in lines:
                if "Real-Time Web Search Results:" in line:
                    showing = True
                elif showing and line.strip() == "":
                    break
                
                if showing:
                    web_lines.append(line)
                    if len(web_lines) >= 5:  # Show first 5 lines
                        break
            
            print(f"   Web results preview:")
            for line in web_lines:
                print(f"     {line}")
        
        print()
        
        # Step 5: Test complete response generation
        print("5️⃣ Testing Complete Response Generation:")
        response = await orchestrator.process_query(test_message)
        
        if response:
            response_text = response.get("text", "")
            print(f"✅ Complete response generated:")
            print(f"   Response length: {len(response_text)} characters")
            print(f"   Response preview: {response_text[:200]}...")
            
            # Check if response mentions web search insights
            has_current_info = any(keyword in response_text.lower() for keyword in ["2025", "trend", "latest", "current", "recent"])
            print(f"   Contains current/trend information: {'✅' if has_current_info else '❌'}")
        else:
            print("❌ Failed to generate complete response")
        
        print()
        print("🎉 PERPLEXITY INTEGRATION TEST COMPLETE")
        print(f"   Orchestrator intelligence: {'✅' if perplexity_selected else '❌'}")
        print(f"   Web search execution: {'✅' if len(web_results) > 0 else '❌'}")
        print(f"   State stack integration: {'✅' if len(state_web_results) > 0 else '❌'}")
        print(f"   Client agent formatting: {'✅' if has_web_results else '❌'}")
        print(f"   End-to-end response: {'✅' if response else '❌'}")
        
        overall_success = all([
            perplexity_selected,
            len(web_results) > 0,
            len(state_web_results) > 0,
            has_web_results,
            response is not None
        ])
        
        print(f"\n🚀 OVERALL STATUS: {'FULLY OPERATIONAL' if overall_success else 'NEEDS ATTENTION'}")
        
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_perplexity_complete_flow())