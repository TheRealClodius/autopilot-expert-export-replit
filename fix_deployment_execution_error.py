#!/usr/bin/env python3
"""
Fix deployment execution error by identifying and resolving the specific issue
causing "execution_error" in production environment
"""

import asyncio
import logging
import json
from services.memory_service import MemoryService
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from datetime import datetime

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def diagnose_deployment_execution_error():
    """Diagnose the exact deployment issue causing execution_error"""
    
    print("🔍 DIAGNOSING DEPLOYMENT EXECUTION ERROR")
    print("=" * 60)
    
    try:
        # Step 1: Initialize orchestrator and check basic setup
        print("1️⃣ Initializing orchestrator...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        print(f"   Atlassian tool available: {orchestrator.atlassian_tool.available}")
        print(f"   MCP server URL: {orchestrator.atlassian_tool.mcp_server_url}")
        
        # Step 2: Test MCP server health
        print("\n2️⃣ Testing MCP server health...")
        try:
            health = await orchestrator.atlassian_tool.check_server_health()
            print(f"   MCP server health: {health}")
        except Exception as health_error:
            print(f"   ❌ MCP health check failed: {health_error}")
            return False
        
        # Step 3: Test the exact MCP action that was failing
        print("\n3️⃣ Testing exact MCP action from production...")
        
        # This is exactly what your orchestrator generated
        mcp_action = {
            'mcp_tool': 'jira_search', 
            'arguments': {
                'jql': 'text ~ "Autopilot for Everyone" ORDER BY created DESC', 
                'limit': 1
            }
        }
        
        print(f"   MCP Action: {mcp_action}")
        
        try:
            # Call the exact method that's failing in production
            result = await orchestrator._execute_mcp_action_direct(mcp_action)
            
            print(f"\n📊 DIRECT MCP EXECUTION RESULT:")
            print("=" * 40)
            
            if result:
                if result.get("error"):
                    print(f"❌ Error occurred: {result.get('error')}")
                    
                    # Check for specific error types
                    error_msg = result.get("error", "")
                    if error_msg == "execution_error":
                        print(f"🔍 This is the EXACT error you're experiencing!")
                        print(f"   Message: {result.get('message', 'No message')}")
                        print(f"   Exception type: {result.get('exception_type', 'Unknown')}")
                        
                        debug_info = result.get("debug_info", {})
                        if debug_info:
                            print(f"\n🐛 DEBUG INFO:")
                            for key, value in debug_info.items():
                                if key != "stack_trace":
                                    print(f"   {key}: {value}")
                            
                            # Show stack trace
                            stack_trace = debug_info.get("stack_trace", "")
                            if stack_trace:
                                print(f"\n📜 STACK TRACE:")
                                print(stack_trace[:1000] + "..." if len(stack_trace) > 1000 else stack_trace)
                    
                    return False
                else:
                    print(f"✅ MCP execution successful!")
                    print(f"   Success: {result.get('success', False)}")
                    print(f"   Result type: {type(result.get('result'))}")
                    return True
            else:
                print("❌ No result returned")
                return False
                
        except Exception as exec_error:
            print(f"❌ Exception during MCP execution: {exec_error}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return False
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_full_production_scenario():
    """Test the full production scenario exactly as it happens in Slack"""
    
    print("\n🔄 TESTING FULL PRODUCTION SCENARIO")
    print("=" * 60)
    
    try:
        # Initialize orchestrator
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create the exact ProcessedMessage that would come from Slack
        # Using the context from your trace
        test_message = ProcessedMessage(
            text="any idea where I can find the last ticket created that is related to Autopilot for Everyone?",
            user_id="U06JC1TABL3",
            user_name="Unknown",
            user_email="",
            user_display_name="Unknown", 
            user_first_name="Unknown",
            user_title="",
            user_department="",
            channel_id="D092WU3A3A9",
            channel_name="Unknown",
            is_dm=True,
            is_mention=False,
            thread_ts="1751214317.726569",
            message_ts="1751214360.170409"
        )
        
        print(f"Processing query: {test_message.text}")
        
        # Process the full query exactly as production does
        response = await orchestrator.process_query(test_message)
        
        if response:
            print(f"✅ Full production scenario successful!")
            print(f"Response text length: {len(response.get('text', ''))}")
            
            # Check if response contains error indicators
            response_text = response.get('text', '')
            if "execution_error" in response_text.lower() or "failed" in response_text.lower():
                print(f"⚠️ Response contains error indicators:")
                print(f"   Preview: {response_text[:300]}...")
                return False
            else:
                print(f"✅ Response looks healthy:")
                print(f"   Preview: {response_text[:200]}...")
                return True
        else:
            print("❌ No response from full production scenario")
            return False
            
    except Exception as e:
        print(f"❌ Error in full production scenario: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run comprehensive diagnosis and fix"""
    
    # Test 1: Diagnose exact deployment error
    diagnosis_success = await diagnose_deployment_execution_error()
    
    if diagnosis_success:
        print("\n✅ DIAGNOSIS SUCCESSFUL - MCP execution works fine")
        
        # Test 2: Test full production scenario
        production_success = await test_full_production_scenario()
        
        if production_success:
            print("\n🎉 CONCLUSION: Everything works fine!")
            print("The issue may be intermittent or environment-specific.")
            print("Consider checking:")
            print("- Network connectivity issues")
            print("- Resource constraints during high load")
            print("- Intermittent MCP server availability")
        else:
            print("\n⚠️ CONCLUSION: MCP works but full flow fails")
            print("Issue is in orchestrator flow, not MCP execution itself.")
    else:
        print("\n❌ CONCLUSION: MCP execution failing")
        print("Issue is in MCP tool implementation or deployment environment.")
        print("Check the debug info above for specific error details.")

if __name__ == "__main__":
    asyncio.run(main())