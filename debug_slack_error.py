#!/usr/bin/env python3
"""
Debug the exact Slack error scenario where user gets "cannot access that information" response.
"""

import asyncio
import json
from services.memory_service import MemoryService
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from models.schemas import ProcessedMessage
from datetime import datetime

async def debug_slack_error():
    """Debug the exact error scenario from Slack screenshot"""
    print("🚨 DEBUGGING SLACK ERROR: 'Cannot access that information'")
    print("=" * 60)
    
    # Create exact message from screenshot
    test_message = ProcessedMessage(
        text="Hello. Can you help me retrieve the roadmap for Autopilot for Everyone? Either Jira or confluence. Don't really know where it is.",
        user_id="U123456",
        user_name="Andrei Clodius", 
        user_first_name="Andrei",
        user_display_name="Andrei Clodius",
        user_title=None,
        user_department=None,
        channel_id="C123456",
        channel_name="general",
        thread_ts=None,
        timestamp=datetime.now(),
        is_direct_message=True,
        is_mention=False,
        is_thread_reply=False
    )
    
    # Initialize services like in production
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    print("Step 1: Running full orchestrator process_query (like Slack does)")
    print("-" * 50)
    
    try:
        # This is what actually gets called in production
        result = await orchestrator.process_query(test_message)
        
        print(f"Process query result: {result is not None}")
        
        if result:
            print(f"Result keys: {list(result.keys())}")
            
            # Check for the exact error message from screenshot
            response_text = result.get('text', '')
            
            if 'cannot access that information' in response_text.lower():
                print("❌ FOUND THE ERROR MESSAGE!")
                print(f"Full response: {response_text}")
                
                # Look for clues in the result data
                if 'state_stack' in result:
                    state_stack = result['state_stack']
                    analysis = state_stack.get('orchestrator_analysis', {})
                    search_results = analysis.get('search_results', [])
                    
                    print(f"\nDEBUG INFO:")
                    print(f"- Search results count: {len(search_results)}")
                    
                    for i, search_result in enumerate(search_results):
                        if isinstance(search_result, dict):
                            success = search_result.get('success', False)
                            error = search_result.get('error', 'No error details')
                            tool_type = search_result.get('type', 'unknown')
                            
                            print(f"- Search {i+1}: {tool_type} - Success: {success}")
                            if not success:
                                print(f"  Error: {error}")
            else:
                print("✅ No error message found")
                print(f"Response preview: {response_text[:200]}...")
                
        else:
            print("❌ No result returned from orchestrator")
            
    except Exception as e:
        print(f"❌ Exception during process_query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_slack_error())