#!/usr/bin/env python3
"""
Complete MCP Integration Test

Test the complete flow:
1. Orchestrator executes MCP action
2. Results stored in gathered_information  
3. State stack built with results
4. Client agent processes and formats results
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

logging.basicConfig(level=logging.INFO)

async def test_complete_mcp_integration():
    """Test complete MCP integration end-to-end"""
    print("🔧 TESTING COMPLETE MCP INTEGRATION")
    print("=" * 50)
    
    try:
        # Initialize services
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        client_agent = ClientAgent()
        
        # Create test message asking for Autopilot documentation
        test_message = ProcessedMessage(
            text="Find pages about Autopilot for Everyone",
            user_id="U_TEST_USER",
            user_name="TestUser",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Engineer",
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
        
        # Test just the MCP action execution 
        print("1️⃣ Testing direct MCP action execution...")
        
        test_action = {
            "mcp_tool": "confluence_search",
            "arguments": {
                "query": "autopilot for everyone",
                "limit": 3
            }
        }
        
        # Execute the action directly 
        mcp_result = await orchestrator._execute_single_tool_action("atlassian", test_action)
        
        if mcp_result and mcp_result.get("success"):
            print("✅ MCP action executed successfully")
            print(f"   Result structure: {type(mcp_result)}")
            
            # Create mock gathered_info with real MCP result
            gathered_info = {
                "vector_results": [],
                "perplexity_results": [],
                "atlassian_results": [
                    {
                        "action_type": "confluence_search",
                        "result": mcp_result,  # Use the actual MCP result
                        "success": True
                    }
                ]
            }
            
            execution_plan = {
                "analysis": "User is asking for Autopilot documentation",
                "tools_needed": ["atlassian_search"]
            }
            
            print("\n2️⃣ Building state stack with real MCP results...")
            
            # Build state stack 
            state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
            
            print("✅ State stack built")
            
            # Check what's in the state stack
            orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
            atlassian_results = orchestrator_analysis.get("atlassian_results", [])
            
            print(f"   Atlassian results in state stack: {len(atlassian_results)}")
            
            if atlassian_results:
                first_result = atlassian_results[0]
                print(f"   First result structure: {list(first_result.keys())}")
                
                # Check the actual MCP result data
                result_data = first_result.get("result", {})
                print(f"   Result data type: {type(result_data)}")
                
                if isinstance(result_data, dict) and result_data.get("success"):
                    pages = result_data.get("result", [])
                    print(f"   Pages found: {len(pages) if isinstance(pages, list) else 'not a list'}")
                    
                    if isinstance(pages, list) and len(pages) > 0:
                        print(f"   Sample page: {pages[0].get('title', 'No title')}")
            
            print("\n3️⃣ Testing client agent formatting...")
            
            # Test client agent formatting
            formatted_context = client_agent._format_state_stack_context(state_stack)
            
            # Check if Atlassian results appear
            if "Atlassian Actions:" in formatted_context:
                print("✅ Client agent found Atlassian results")
                
                # Extract the Atlassian section
                lines = formatted_context.split('\n')
                atlassian_section = []
                in_atlassian = False
                
                for line in lines:
                    if "Atlassian Actions:" in line:
                        in_atlassian = True
                    elif in_atlassian and line.strip() == "":
                        break
                    
                    if in_atlassian:
                        atlassian_section.append(line)
                
                print("   Atlassian section from client agent:")
                for line in atlassian_section[:10]:  # First 10 lines
                    print(f"     {line}")
                
                return True
            else:
                print("❌ Client agent did not find Atlassian results")
                print(f"   Context length: {len(formatted_context)}")
                print("   Context preview:")
                print(formatted_context[:500] + "...")
                return False
        else:
            print("❌ MCP action failed")
            print(f"   Result: {mcp_result}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_mcp_integration())
    if success:
        print("\n🎉 COMPLETE MCP INTEGRATION WORKING")
        print("   End-to-end flow from MCP execution → state stack → client formatting successful")
    else:
        print("\n💥 MCP INTEGRATION BROKEN")
        print("   Issue in the complete flow - need to debug further")