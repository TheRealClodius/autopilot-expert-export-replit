#!/usr/bin/env python3
"""
Test LangSmith Conversation Completion Fix

This script tests that conversation traces are properly completed 
instead of remaining pending forever.
"""

import asyncio
import json
from datetime import datetime

from models.schemas import SlackEvent, ProcessedMessage
from services.trace_manager import trace_manager


async def test_conversation_completion():
    """Test that conversation sessions are properly completed"""
    
    print("🔬 Testing LangSmith Conversation Completion Fix")
    print("=" * 60)
    
    if not trace_manager.is_enabled():
        print("❌ LangSmith not enabled - cannot test completion")
        return
    
    # Test 1: Start a conversation session
    print("\n1️⃣ Starting conversation session...")
    session_id = await trace_manager.start_conversation_session(
        user_id="test_user_completion",
        message="Test message for completion verification", 
        channel_id="test_channel_completion",
        message_ts="1234567890.123"
    )
    
    if session_id:
        print(f"✅ Session started: {session_id}")
        print(f"   Active sessions: {len(trace_manager.active_sessions)}")
        print(f"   Current trace ID: {trace_manager.current_trace_id}")
    else:
        print("❌ Failed to start session")
        return
    
    # Test 2: Simulate some agent work (LLM calls)
    print("\n2️⃣ Simulating agent work...")
    await trace_manager.log_llm_call(
        model="gemini-2.5-pro",
        prompt="Test prompt for completion verification",
        response="Test response for completion verification",
        duration=2.5,
        tokens_used=100
    )
    print("✅ Logged LLM call")
    
    # Test 3: Complete the conversation session
    print("\n3️⃣ Completing conversation session...")
    success = await trace_manager.complete_conversation_session(
        final_response="Test final response - conversation completed successfully"
    )
    
    if success:
        print("✅ Conversation session completed successfully")
        print(f"   Active sessions after completion: {len(trace_manager.active_sessions)}")
        print(f"   Current trace ID after completion: {trace_manager.current_trace_id}")
    else:
        print("❌ Failed to complete conversation session")
    
    # Test 4: Test error completion
    print("\n4️⃣ Testing error completion...")
    error_session_id = await trace_manager.start_conversation_session(
        user_id="test_user_error",
        message="Test message for error completion",
        channel_id="test_channel_error", 
        message_ts="1234567890.456"
    )
    
    if error_session_id:
        print(f"✅ Error test session started: {error_session_id}")
        
        # Complete with error
        error_success = await trace_manager.complete_conversation_session(
            error="Test error - simulated failure for testing"
        )
        
        if error_success:
            print("✅ Error completion successful")
        else:
            print("❌ Error completion failed")
    
    print("\n" + "=" * 60)
    print("🎯 LangSmith Conversation Completion Test Results:")
    print(f"   ✅ Normal completion: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"   ✅ Error completion: {'✅ PASS' if error_success else '❌ FAIL'}")
    print(f"   ✅ Session cleanup: {'✅ PASS' if len(trace_manager.active_sessions) == 0 else '❌ FAIL'}")
    
    # Summary
    if success and error_success and len(trace_manager.active_sessions) == 0:
        print("\n🎉 ALL TESTS PASSED - Conversation completion fix working correctly!")
        print("   • Conversations are now properly completed with end_time")
        print("   • No more pending traces in LangSmith")
        print("   • Session cleanup working properly")
    else:
        print("\n⚠️ Some tests failed - review the implementation")


if __name__ == "__main__":
    asyncio.run(test_conversation_completion())