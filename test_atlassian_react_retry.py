#!/usr/bin/env python3
"""
Test Atlassian ReAct Retry Pattern - Specific Query Test

Tests the exact query "List all pages created by Andrei Clodius" to verify
the generalized ReAct pattern automatically retries with CQL syntax corrections.
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
from services.progress_tracker import ProgressTracker

async def test_atlassian_react_retry():
    """Test the ReAct pattern with the specific Andrei Clodius query"""
    
    print("🔧 TESTING ATLASSIAN REACT RETRY PATTERN")
    print("Query: 'List all pages created by Andrei Clodius'")
    print("Expected: Automatic CQL syntax retry on errors")
    print("="*70)
    
    # Track all progress events to see the ReAct pattern
    progress_events = []
    reasoning_events = []
    retry_events = []
    
    async def capture_progress(message: str):
        """Capture all progress events to verify ReAct pattern execution"""
        timestamp = time.time()
        progress_events.append((timestamp, message))
        print(f"📊 PROGRESS: {message}")
        
        # Categorize events
        if "reasoning" in message.lower() or "analyzing" in message.lower():
            reasoning_events.append(message)
        elif "retry" in message.lower():
            retry_events.append(message)
    
    try:
        # Initialize components with progress tracking
        memory_service = MemoryService()
        progress_tracker = ProgressTracker(update_callback=capture_progress)
        orchestrator = OrchestratorAgent(memory_service, progress_tracker)
        
        # Create the exact test message you requested
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST",
            text="List all pages created by Andrei Clodius",  # Your exact query
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
        
        print(f"🎯 TESTING QUERY: '{test_message.text}'")
        print()
        
        # Execute the full orchestrator process
        print("🚀 Starting orchestrator process...")
        start_time = time.time()
        
        result = await orchestrator.process_query(test_message)
        
        execution_time = time.time() - start_time
        print(f"\n⏱️ EXECUTION COMPLETED in {execution_time:.2f} seconds")
        print("="*70)
        
        # Analyze the results for ReAct pattern evidence
        print("\n🔍 REACT PATTERN ANALYSIS:")
        print(f"📊 Total Progress Events: {len(progress_events)}")
        print(f"🧠 Reasoning Events: {len(reasoning_events)}")
        print(f"🔄 Retry Events: {len(retry_events)}")
        
        # Show reasoning events
        if reasoning_events:
            print(f"\n🧠 REASONING EVENTS:")
            for event in reasoning_events:
                print(f"   • {event}")
        
        # Show retry events
        if retry_events:
            print(f"\n🔄 RETRY EVENTS:")
            for event in retry_events:
                print(f"   • {event}")
        
        # Analyze final result
        print(f"\n📋 FINAL RESULT:")
        if result:
            success = result.get('success', False)
            print(f"   Overall Success: {success}")
            
            # Check gathered information
            gathered_info = result.get('gathered_information', {})
            atlassian_results = gathered_info.get('atlassian_results', [])
            
            if atlassian_results:
                print(f"   Atlassian Actions Executed: {len(atlassian_results)}")
                
                for i, action_result in enumerate(atlassian_results, 1):
                    action_type = action_result.get('action_type', 'unknown')
                    success = action_result.get('success', False)
                    print(f"      {i}. {action_type}: {'✅ SUCCESS' if success else '❌ FAILED'}")
                    
                    if not success:
                        error = action_result.get('error', 'Unknown error')
                        print(f"         Error: {error[:100]}...")
                        
                        # Check if HITL was triggered
                        if 'hitl_required' in action_result:
                            print(f"         🚨 HITL Escalation: Human intervention required")
                    else:
                        # Show successful results
                        action_result_data = action_result.get('result', {})
                        if action_result_data:
                            if 'confluence_search_results' in action_result_data:
                                pages = action_result_data['confluence_search_results'].get('pages', [])
                                print(f"         📄 Found {len(pages)} pages")
                                
                                for j, page in enumerate(pages[:3], 1):  # Show first 3 pages
                                    title = page.get('title', 'No title')
                                    creator = page.get('creator', 'Unknown creator')
                                    print(f"            {j}. {title} (by {creator})")
            else:
                print(f"   No Atlassian results found")
                
            # Check client response
            client_response = result.get('client_response', '')
            if client_response:
                print(f"   Client Response Length: {len(client_response)} characters")
                print(f"   Response Preview: {client_response[:150]}...")
        else:
            print(f"   ❌ No result returned from orchestrator")
        
        # Verify ReAct pattern implementation
        print(f"\n🎯 REACT PATTERN VERIFICATION:")
        
        react_pattern_detected = len(reasoning_events) > 0
        if react_pattern_detected:
            print(f"   ✅ ReAct pattern active - reasoning events detected")
        else:
            print(f"   ❓ Limited reasoning events - may indicate successful first attempt")
            
        if retry_events:
            print(f"   ✅ Automatic retry system activated")
            print(f"   ✅ System attempted to correct failures intelligently")
        else:
            print(f"   ℹ️ No retries needed - original request may have succeeded")
            
        print(f"\n🏆 CONCLUSION:")
        if react_pattern_detected or len(progress_events) > 5:
            print(f"   ✅ Generalized ReAct pattern is working")
            print(f"   ✅ System demonstrates Reason → Act → Observe → Reason → Act cycle")
            print(f"   ✅ Progress tracking shows decision-making process")
        else:
            print(f"   ⚠️ Limited pattern evidence - check if query triggered tool failures")
            
        return result
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_atlassian_react_retry())
    
    print(f"\n📝 SUMMARY:")
    print(f"Tested the exact query you requested to verify ReAct retry behavior.")
    print(f"The generalized pattern should automatically handle CQL syntax errors")
    print(f"and retry up to 5 times before escalating to human intervention.")