#!/usr/bin/env python3
"""
Test MCP execution directly to verify the tool is working
and identify if the issue is in webhook parsing or MCP execution
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.memory_service import MemoryService
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from datetime import datetime

async def test_mcp_directly():
    """Test MCP execution bypassing Slack webhook issues"""
    
    print("🧪 TESTING MCP EXECUTION DIRECTLY")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        print("1️⃣ Initializing orchestrator...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        if not orchestrator.atlassian_tool.available:
            print("❌ Atlassian tool not available - check credentials")
            return False
        
        print("✅ Orchestrator initialized")
        
        # Test the exact MCP action that was failing
        print("\n2️⃣ Testing exact MCP action from your logs...")
        
        # This is the exact action from your orchestrator output
        mcp_action = {
            'mcp_tool': 'jira_search', 
            'arguments': {
                'jql': 'text ~ "Autopilot for Everyone" ORDER BY created DESC', 
                'limit': 1
            }
        }
        
        print(f"MCP Action: {mcp_action}")
        
        # Call the direct MCP execution method
        result = await orchestrator._execute_mcp_action_direct(mcp_action)
        
        print(f"\n📊 MCP EXECUTION RESULT:")
        print("=" * 40)
        
        if result:
            print(f"✅ MCP execution completed")
            print(f"Success: {result.get('success', False)}")
            
            if result.get("error"):
                print(f"❌ Error: {result.get('error')}")
                print(f"Error details: {result}")
                return False
            else:
                print(f"✅ Result type: {type(result.get('result'))}")
                
                # Check if we got actual results
                mcp_result = result.get("result", [])
                if isinstance(mcp_result, list):
                    print(f"✅ Found {len(mcp_result)} issues")
                    
                    # Show first result if available
                    if mcp_result:
                        first_issue = mcp_result[0]
                        if isinstance(first_issue, dict):
                            print(f"   First issue: {first_issue.get('key', 'No key')} - {first_issue.get('summary', 'No summary')}")
                        else:
                            print(f"   First result: {str(first_issue)[:100]}...")
                elif isinstance(mcp_result, dict):
                    print(f"✅ Result keys: {list(mcp_result.keys())}")
                else:
                    print(f"✅ Result: {str(mcp_result)[:200]}...")
                
                return True
        else:
            print("❌ No result returned from MCP execution")
            return False
            
    except Exception as e:
        print(f"❌ Error testing MCP directly: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_full_orchestrator_flow():
    """Test full orchestrator flow with a proper ProcessedMessage"""
    
    print("\n🔄 TESTING FULL ORCHESTRATOR FLOW")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create a proper ProcessedMessage that would normally come from Slack Gateway
        test_message = ProcessedMessage(
            text="any idea where I can find the last ticket created that is related to Autopilot for Everyone?",
            user_id="U123456789",
            user_name="testuser",
            user_email="test@uipath.com",
            user_display_name="Test User",
            user_first_name="Test",
            user_title="Developer",
            user_department="Engineering",
            channel_id="C123456789",
            channel_name="test-channel",
            is_dm=False,
            is_mention=True,
            thread_ts=None,
            message_ts=str(datetime.now().timestamp())
        )
        
        print(f"Test message: {test_message.text}")
        
        # Process the query
        response = await orchestrator.process_query(test_message)
        
        if response:
            print(f"✅ Full flow completed")
            print(f"Response text length: {len(response.get('text', ''))}")
            print(f"Response preview: {response.get('text', '')[:200]}...")
            return True
        else:
            print("❌ No response from full orchestrator flow")
            return False
            
    except Exception as e:
        print(f"❌ Error in full orchestrator flow: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    async def main():
        # Test MCP directly first
        mcp_success = await test_mcp_directly()
        
        if mcp_success:
            # If MCP works, test full flow
            full_success = await test_full_orchestrator_flow()
            
            if full_success:
                print("\n🎉 CONCLUSION: MCP execution works fine!")
                print("The issue is likely in Slack webhook parsing, not MCP execution.")
                print("Check why user/text fields are null in webhook data.")
            else:
                print("\n⚠️ CONCLUSION: MCP works but full flow fails")
                print("Issue is in orchestrator flow, not webhook parsing.")
        else:
            print("\n❌ CONCLUSION: MCP execution itself is failing")
            print("Issue is in MCP tool implementation or server connectivity.")
    
    asyncio.run(main())