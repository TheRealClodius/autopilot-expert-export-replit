#!/usr/bin/env python3
"""
Debug JSON Response Issue

This script tests the exact flow where the bot returns raw JSON instead of formatted responses.
We'll trace from MCP execution through state stack to client agent response generation.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from agents.slack_gateway import SlackGateway
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO)

async def debug_json_response():
    """Debug the exact scenario causing raw JSON responses"""
    
    print("🔍 DEBUGGING JSON RESPONSE ISSUE")
    print("=" * 50)
    
    try:
        # Create test message similar to user's query
        test_message = ProcessedMessage(
            channel_id="C_TEST",
            channel_name="test-channel",
            user_id="U_TEST_USER",
            user_name="andrei",
            user_first_name="Andrei",
            user_display_name="Andrei Clodius",
            text="Can you find something about andrei clodius on confluence?",
            message_ts="1234567890.123456",
            thread_ts=None,
            is_dm=False,
            raw_event={}
        )
        
        # Initialize services
        memory_service = MemoryService()
        
        # Initialize orchestrator
        orchestrator = OrchestratorAgent(memory_service=memory_service)
        
        print("1️⃣ Testing orchestrator query analysis...")
        
        # Test query analysis
        query_result = await orchestrator._analyze_query(test_message)
        execution_plan = query_result.get("execution_plan", {})
        
        print(f"   Analysis: {execution_plan.get('analysis', 'No analysis')[:80]}...")
        print(f"   Tools needed: {execution_plan.get('tools_needed', [])}")
        print(f"   Atlassian actions: {len(execution_plan.get('atlassian_actions', []))}")
        
        if "atlassian_search" not in execution_plan.get("tools_needed", []):
            print("   ❌ Orchestrator didn't identify need for Atlassian search")
            return
        
        print("   ✅ Orchestrator correctly identified Atlassian search need")
        print()
        
        print("2️⃣ Testing plan execution with MCP calls...")
        
        # Execute the plan 
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        atlassian_results = gathered_info.get("atlassian_results", [])
        
        print(f"   Gathered info keys: {list(gathered_info.keys())}")
        print(f"   Atlassian results: {len(atlassian_results)}")
        
        if not atlassian_results:
            print("   ❌ No Atlassian results returned from plan execution")
            return
        
        # Check first result structure
        first_result = atlassian_results[0]
        print(f"   First result keys: {list(first_result.keys())}")
        print(f"   Success: {first_result.get('success')}")
        
        if first_result.get("success"):
            result_data = first_result.get("result", {})
            print(f"   Result data type: {type(result_data)}")
            print(f"   Result data keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'Not a dict'}")
            
            # Check if this is the nested MCP structure
            if isinstance(result_data, dict) and result_data.get("success"):
                pages = result_data.get("result", [])
                print(f"   Pages found: {len(pages) if isinstance(pages, list) else 'Not a list'}")
                if isinstance(pages, list) and len(pages) > 0:
                    sample_page = pages[0]
                    print(f"   Sample page: {sample_page.get('title', 'No title') if isinstance(sample_page, dict) else str(sample_page)}")
        else:
            error_msg = first_result.get("error", "Unknown error")
            print(f"   Error: {error_msg}")
        
        print()
        
        print("3️⃣ Testing state stack building...")
        
        # Build state stack
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        
        print(f"   State stack keys: {list(state_stack.keys())}")
        
        # Check orchestrator analysis in state stack
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        print(f"   Orchestrator analysis keys: {list(orchestrator_analysis.keys())}")
        
        state_atlassian_results = orchestrator_analysis.get("atlassian_results", [])
        print(f"   Atlassian results in state: {len(state_atlassian_results)}")
        
        if state_atlassian_results:
            state_first_result = state_atlassian_results[0]
            print(f"   State first result keys: {list(state_first_result.keys())}")
            
            # Check if structure is preserved
            if state_first_result.get("success"):
                state_result_data = state_first_result.get("result", {})
                print(f"   State result data type: {type(state_result_data)}")
                
                if isinstance(state_result_data, dict) and state_result_data.get("success"):
                    state_pages = state_result_data.get("result", [])
                    print(f"   State pages: {len(state_pages) if isinstance(state_pages, list) else 'Not a list'}")
        
        print()
        
        print("4️⃣ Testing client agent formatting...")
        
        # Test client agent
        client_agent = ClientAgent()
        
        # Format state stack context
        formatted_context = client_agent._format_state_stack_context(state_stack)
        
        print(f"   Formatted context length: {len(formatted_context)} chars")
        
        # Check if Atlassian results appear
        has_atlassian_section = "Atlassian Actions:" in formatted_context
        print(f"   Atlassian section found: {'✅' if has_atlassian_section else '❌'}")
        
        if has_atlassian_section:
            # Extract Atlassian section
            lines = formatted_context.split('\n')
            atlassian_section = []
            in_atlassian = False
            
            for line in lines:
                if "Atlassian Actions:" in line:
                    in_atlassian = True
                    atlassian_section.append(line)
                elif in_atlassian and line.strip() == "":
                    break
                elif in_atlassian:
                    atlassian_section.append(line)
            
            print("   Atlassian section content:")
            for line in atlassian_section[:10]:  # Show first 10 lines
                print(f"      {line}")
        
        print()
        
        print("5️⃣ Testing complete client agent response generation...")
        
        # Generate complete response 
        try:
            response_result = await client_agent.generate_response(state_stack)
            
            print(f"   Response type: {type(response_result)}")
            
            if isinstance(response_result, dict):
                print(f"   Response keys: {list(response_result.keys())}")
                response_text = response_result.get("response", response_result.get("text", ""))
            else:
                response_text = str(response_result)
            
            print(f"   Response length: {len(response_text)} chars")
            print(f"   Response preview: {response_text[:200]}...")
            
            # Check if response contains raw JSON
            has_raw_json = '"limit"' in response_text or '": 10' in response_text or '"}' in response_text
            print(f"   Contains raw JSON: {'❌ YES' if has_raw_json else '✅ NO'}")
            
            if has_raw_json:
                print("   🚨 ISSUE IDENTIFIED: Response contains raw JSON!")
                
                # Find the JSON part
                lines = response_text.split('\n')
                for i, line in enumerate(lines):
                    if '"limit"' in line or '": 10' in line:
                        print(f"   Raw JSON at line {i+1}: {line}")
                        break
            
        except Exception as response_error:
            print(f"   ❌ Client agent response generation failed: {response_error}")
            import traceback
            traceback.print_exc()
        
        print()
        print("🎯 DIAGNOSIS COMPLETE")
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_json_response())