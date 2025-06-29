#!/usr/bin/env python3
"""
Test the execution error fix with intelligent retry logic
"""

import asyncio
import logging
from services.memory_service import MemoryService
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from datetime import datetime

# Set up logging to see detailed execution
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_execution_error_fix():
    """Test the execution error fix with the exact scenario that was failing"""
    
    print("🧪 TESTING EXECUTION ERROR FIX")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        print("1️⃣ Initializing orchestrator with retry logic...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        print(f"   Atlassian tool available: {orchestrator.atlassian_tool.available}")
        
        # Test the exact scenario from your production logs
        print("\n2️⃣ Testing the exact query that was failing...")
        
        # Create the exact ProcessedMessage from your trace
        test_message = ProcessedMessage(
            text="any idea where I can find the last ticket created that is related to Autopilot for Everyone?",
            user_id="U06JC1TABL3",
            user_name="testuser",
            user_email="test@uipath.com",
            user_display_name="Test User", 
            user_first_name="Test",
            user_title="",
            user_department="",
            channel_id="D092WU3A3A9",
            channel_name="test-dm",
            is_dm=True,
            is_mention=False,
            thread_ts="1751214317.726569",
            message_ts="1751214360.170409"
        )
        
        print(f"   Query: {test_message.text}")
        
        # Process the full query
        start_time = datetime.now()
        response = await orchestrator.process_query(test_message)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n📊 PROCESSING RESULTS:")
        print("=" * 40)
        print(f"Processing time: {processing_time:.2f} seconds")
        
        if response:
            response_text = response.get('text', '')
            
            # Check for specific error indicators
            error_indicators = [
                "execution error", 
                "execution_error",
                "FAILED",
                "encountered an issue",
                "cannot access that information",
                "Sorry, I couldn't process"
            ]
            
            has_error = any(indicator.lower() in response_text.lower() for indicator in error_indicators)
            
            if has_error:
                print("❌ Response contains error indicators:")
                print(f"   Full response: {response_text}")
                return False
            else:
                print("✅ Response looks healthy!")
                print(f"   Response length: {len(response_text)} characters")
                print(f"   Response preview: {response_text[:200]}...")
                
                # Check for positive indicators
                positive_indicators = [
                    "PLTPD-3413",  # The specific ticket we should find
                    "Autopilot for everyone",
                    "Alexandre Blain",  # The assignee
                    "ticket",
                    "created"
                ]
                
                found_indicators = [indicator for indicator in positive_indicators 
                                  if indicator.lower() in response_text.lower()]
                
                print(f"   Found positive indicators: {found_indicators}")
                
                if found_indicators:
                    print("✅ Response contains expected content!")
                    return True
                else:
                    print("⚠️ Response doesn't contain expected ticket information")
                    return False
        else:
            print("❌ No response generated")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_mcp_retry_logic():
    """Test the new MCP retry logic specifically"""
    
    print("\n🔄 TESTING MCP RETRY LOGIC")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Test the exact MCP action that was failing
        mcp_action = {
            'mcp_tool': 'jira_search', 
            'arguments': {
                'jql': 'text ~ "Autopilot for Everyone" ORDER BY created DESC', 
                'limit': 1
            }
        }
        
        print(f"Testing MCP action: {mcp_action}")
        
        # Test the new retry method
        result = await orchestrator._execute_mcp_action_with_retry(mcp_action)
        
        print(f"\n📊 RETRY LOGIC RESULT:")
        print("=" * 30)
        
        if result:
            if result.get("error"):
                print(f"❌ Error: {result.get('error')}")
                print(f"   Success: {result.get('success', False)}")
                return False
            else:
                print(f"✅ Success: {result.get('success', True)}")
                print(f"   Result type: {type(result.get('result'))}")
                
                # Check if we got actual ticket data
                mcp_result = result.get("result", {})
                if isinstance(mcp_result, dict) and "issues" in mcp_result:
                    issues = mcp_result["issues"]
                    print(f"   Found {len(issues)} issues")
                    
                    if issues:
                        first_issue = issues[0]
                        print(f"   First issue: {first_issue.get('key')} - {first_issue.get('summary')}")
                    
                    return True
                else:
                    print(f"   Unexpected result format: {mcp_result}")
                    return False
        else:
            print("❌ No result returned")
            return False
            
    except Exception as e:
        print(f"❌ Error testing retry logic: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run comprehensive test of the execution error fix"""
    
    # Test 1: Full query processing
    print("🎯 TESTING EXECUTION ERROR FIX")
    print("=" * 60)
    
    full_test_success = await test_execution_error_fix()
    
    # Test 2: Specific retry logic
    retry_test_success = await test_mcp_retry_logic()
    
    # Summary
    print(f"\n🏁 TEST SUMMARY")
    print("=" * 30)
    print(f"Full query test: {'✅ PASS' if full_test_success else '❌ FAIL'}")
    print(f"Retry logic test: {'✅ PASS' if retry_test_success else '❌ FAIL'}")
    
    if full_test_success and retry_test_success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("The execution error fix is working correctly.")
        print("Your Slack bot should now handle MCP tool calls reliably.")
    else:
        print(f"\n⚠️ SOME TESTS FAILED")
        print("The execution error fix may need additional adjustments.")
        
        if not full_test_success:
            print("- Full query processing still has issues")
        if not retry_test_success:
            print("- MCP retry logic needs debugging")

if __name__ == "__main__":
    asyncio.run(main())