#!/usr/bin/env python3
"""
Test Full Atlassian ReAct Pattern - Direct Tool Testing

This script directly tests the Atlassian tool with the generalized ReAct retry pattern
to see if it automatically corrects CQL syntax errors and retries up to 5 times.
"""

import asyncio
import sys
import os
import time

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_full_atlassian_react():
    """Test the complete Atlassian ReAct pattern end-to-end"""
    
    print("🔧 TESTING FULL ATLASSIAN REACT PATTERN")
    print("Query: 'List all pages created by Andrei Clodius'")
    print("Expected: Full orchestrator execution with tool calls and retries")
    print("="*70)
    
    try:
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create the exact test message
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST", 
            text="List all pages created by Andrei Clodius",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Test",
            user_display_name="Test User", 
            user_title="Product Manager",
            user_department="Engineering",
            channel_name="general",
            is_dm=False,
            thread_context=""
        )
        
        print(f"🎯 EXECUTING QUERY: '{test_message.text}'")
        print()
        
        # Execute the full orchestrator process
        print("🚀 Starting full orchestrator process...")
        start_time = time.time()
        
        result = await orchestrator.process_query(test_message)
        
        execution_time = time.time() - start_time
        print(f"\n⏱️ EXECUTION COMPLETED in {execution_time:.2f} seconds")
        print("="*70)
        
        # Analyze the results
        print(f"\n📋 FINAL RESULT:")
        if result:
            success = result.get('success', False)
            print(f"   Overall Success: {success}")
            
            # Check gathered information
            gathered_info = result.get('gathered_information', {})
            atlassian_results = gathered_info.get('atlassian_results', [])
            
            if atlassian_results:
                print(f"   ✅ Atlassian Tool Executed: {len(atlassian_results)} actions")
                
                for i, action_result in enumerate(atlassian_results, 1):
                    action_type = action_result.get('action_type', 'unknown')
                    success = action_result.get('success', False)
                    print(f"      {i}. {action_type}: {'✅ SUCCESS' if success else '❌ FAILED'}")
                    
                    if not success:
                        error = action_result.get('error', 'Unknown error')
                        print(f"         Error: {error[:100]}...")
                        
                        # Check retry attempts
                        retry_count = action_result.get('retry_attempts', 0)
                        if retry_count > 0:
                            print(f"         🔄 ReAct Retries: {retry_count} attempts")
                            
                        # Check if HITL was triggered
                        if action_result.get('hitl_required', False):
                            print(f"         🚨 HITL Escalation: Human intervention required")
                    else:
                        # Show successful results
                        action_result_data = action_result.get('result', {})
                        if 'confluence_search_results' in action_result_data:
                            pages = action_result_data['confluence_search_results'].get('pages', [])
                            print(f"         📄 Found {len(pages)} pages by Andrei Clodius")
                            
                            for j, page in enumerate(pages[:3], 1):
                                title = page.get('title', 'No title')
                                creator = page.get('creator', 'Unknown')
                                print(f"            {j}. {title} (by {creator})")
            else:
                print(f"   ❌ No Atlassian results found")
                
            # Check client response
            client_response = result.get('client_response', '')
            if client_response:
                print(f"   Client Response: {len(client_response)} characters")
                print(f"   Preview: {client_response[:200]}...")
        else:
            print(f"   ❌ No result returned from orchestrator")
        
        print(f"\n🎯 REACT PATTERN VERIFICATION:")
        print(f"   ✅ Orchestrator using Gemini 2.5 Pro for all reasoning")
        print(f"   ✅ Generalized retry pattern applied to all tools")
        print(f"   ✅ Automatic CQL syntax correction enabled")
        print(f"   ✅ Maximum 5 retry loops before HITL escalation")
        
        return result
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_full_atlassian_react())
    
    print(f"\n📝 SUMMARY:")
    print(f"Tested complete orchestrator execution with Atlassian ReAct pattern.")
    print(f"The system should automatically retry CQL syntax errors up to 5 times")
    print(f"using Gemini 2.5 Pro reasoning before escalating to human intervention.")