#!/usr/bin/env python3
"""
Test MCP Results Flow Through State Stack

Check if:
1. Orchestrator executes MCP actions and observes results
2. Orchestrator includes MCP results in state stack
3. Client agent receives MCP results from state stack
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO)

async def test_mcp_state_stack_flow():
    """Test complete MCP results flow through state stack"""
    print("🔍 TESTING MCP RESULTS FLOW THROUGH STATE STACK")
    print("=" * 60)
    
    try:
        # Initialize services
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        client_agent = ClientAgent()
        
        # Create test message asking for Autopilot pages
        test_message = ProcessedMessage(
            text="Can you find pages about Autopilot for Everyone project?",
            user_id="U_TEST_USER",
            user_name="TestUser",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Software Engineer",
            user_department="Engineering",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=str(int(datetime.now().timestamp())),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        print(f"🎯 Test Query: '{test_message.text}'")
        print()
        
        # STEP 1: Test orchestrator processing
        print("1️⃣ Testing orchestrator query processing...")
        orchestrator_result = await orchestrator.process_query(test_message)
        
        if not orchestrator_result:
            print("❌ Orchestrator returned no result")
            return False
        
        print("✅ Orchestrator completed processing")
        
        # Check if orchestrator analysis contains MCP results
        orchestrator_analysis = orchestrator_result.get("orchestrator_analysis", {})
        print(f"   Orchestrator analysis keys: {list(orchestrator_analysis.keys())}")
        
        if "atlassian_results" in orchestrator_analysis:
            atlassian_results = orchestrator_analysis["atlassian_results"]
            print(f"   Found atlassian_results: {len(atlassian_results)} items")
            
            for i, result in enumerate(atlassian_results):
                success = result.get("success", False)
                error = result.get("error")
                result_data = result.get("result")
                print(f"   Result {i+1}: success={success}, error={error}")
                
                if result_data and isinstance(result_data, dict):
                    if result_data.get("success") and result_data.get("result"):
                        pages = result_data["result"]
                        if isinstance(pages, list):
                            print(f"      Retrieved {len(pages)} pages")
                            for j, page in enumerate(pages[:3]):
                                title = page.get("title", "No title") if isinstance(page, dict) else str(page)
                                print(f"         Page {j+1}: {title}")
                        else:
                            print(f"      Result type: {type(pages)}")
                    else:
                        print(f"      Result structure: {result_data}")
        else:
            print("   ❌ No atlassian_results found in orchestrator analysis")
            print(f"   Available keys: {list(orchestrator_analysis.keys())}")
        
        # STEP 2: Test state stack building
        print("\n2️⃣ Testing state stack building...")
        
        # Extract gathered information from orchestrator result
        gathered_info = orchestrator_result.get("gathered_information", {})
        execution_plan = orchestrator_result.get("execution_plan", {})
        
        # Test state stack building directly
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        
        print("✅ State stack built successfully")
        print(f"   State stack keys: {list(state_stack.keys())}")
        
        # Check if MCP results are in state stack
        if "orchestrator_analysis" in state_stack:
            orch_analysis = state_stack["orchestrator_analysis"]
            print(f"   Orchestrator analysis in state stack: {list(orch_analysis.keys())}")
            
            if "atlassian_results" in orch_analysis:
                print("   ✅ Found atlassian_results in state stack")
                results = orch_analysis["atlassian_results"]
                print(f"      Number of results: {len(results)}")
            else:
                print("   ❌ No atlassian_results in state stack orchestrator_analysis")
        else:
            print("   ❌ No orchestrator_analysis in state stack")
        
        # STEP 3: Test client agent processing
        print("\n3️⃣ Testing client agent processing...")
        
        try:
            client_response = await client_agent.generate_response(test_message, state_stack)
            
            if client_response:
                print("✅ Client agent generated response")
                response_text = client_response.get("text", "")
                print(f"   Response length: {len(response_text)} characters")
                print(f"   Response preview: {response_text[:200]}...")
                
                # Check if response mentions Confluence pages or Autopilot content
                if "autopilot" in response_text.lower() or "confluence" in response_text.lower():
                    print("   ✅ Response contains Autopilot/Confluence content")
                else:
                    print("   ⚠️ Response doesn't seem to contain specific Autopilot content")
                
                return True
            else:
                print("   ❌ Client agent returned no response")
                return False
                
        except Exception as client_error:
            print(f"   ❌ Client agent error: {client_error}")
            return False
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_state_stack_flow())
    if success:
        print("\n🎉 MCP STATE STACK FLOW WORKING")
        print("   Complete flow from orchestrator → state stack → client agent functional")
    else:
        print("\n💥 MCP STATE STACK FLOW BROKEN")
        print("   Issue in orchestrator observing results or client receiving them")