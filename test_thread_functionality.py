#!/usr/bin/env python3
"""
Thread Functionality Test

Tests the exact workflow described by user:
1. User mentions bot in channel → bot should create thread response
2. User continues asking questions in that thread → bot maintains conversation history
3. Memory is preserved within the specific thread context
"""

import asyncio
import json
from typing import Dict, Any
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.slack_gateway import SlackGateway
from services.memory_service import MemoryService

class ThreadFunctionalityTest:
    """Test thread handling functionality"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.orchestrator = OrchestratorAgent(self.memory_service)
        
    def create_channel_mention_message(self, text: str, message_ts: str) -> ProcessedMessage:
        """Create a message simulating user mentioning bot in channel"""
        return ProcessedMessage(
            text=text,
            user_id="U123456789",
            user_name="john.doe", 
            user_email="john.doe@company.com",
            channel_id="C987654321",
            channel_name="general",
            is_dm=False,
            is_mention=True,  # This simulates @botname mention
            thread_ts=None,  # No existing thread - should create new one
            message_ts=message_ts,
            thread_context=None
        )
    
    def create_thread_reply_message(self, text: str, thread_ts: str, message_ts: str) -> ProcessedMessage:
        """Create a message simulating user replying in the thread"""
        return ProcessedMessage(
            text=text,
            user_id="U123456789",
            user_name="john.doe",
            user_email="john.doe@company.com", 
            channel_id="C987654321",
            channel_name="general",
            is_dm=False,
            is_mention=False,  # Not a mention, just thread reply
            thread_ts=thread_ts,  # Existing thread
            message_ts=message_ts,
            thread_context=f"This is a thread reply under {thread_ts}"
        )
    
    async def test_channel_mention_creates_thread(self) -> Dict[str, Any]:
        """Test 1: User mentions bot in channel → should create thread response"""
        print("🧪 Test 1: Channel mention creates thread response")
        
        # Simulate user mentioning bot in channel
        message_ts = "1640995200.001500"
        message = self.create_channel_mention_message(
            "@autopilot what's the latest update on UiPath integration?",
            message_ts
        )
        
        # Process through orchestrator
        response = await self.orchestrator.process_query(message)
        
        # Verify response creates thread
        expected_thread_ts = message_ts  # Should use message_ts as thread_ts for new mentions
        
        result = {
            "message_input": message.text,
            "expected_thread_ts": expected_thread_ts,
            "actual_thread_ts": response.get("thread_ts") if response else None,
            "response_generated": response is not None,
            "thread_created_correctly": response.get("thread_ts") == expected_thread_ts if response else False,
            "response_text": response.get("text", "No response")[:100] + "..." if response else "No response"
        }
        
        print(f"✅ Thread creation test: {'PASS' if result['thread_created_correctly'] else 'FAIL'}")
        return result
    
    async def test_thread_conversation_continuity(self) -> Dict[str, Any]:
        """Test 2: User asks follow-up questions in thread → maintains conversation history"""
        print("🧪 Test 2: Thread conversation maintains history")
        
        # Step 1: Initial mention in channel
        original_ts = "1640995200.001500"
        initial_message = self.create_channel_mention_message(
            "@autopilot tell me about Autopilot's latest features",
            original_ts
        )
        
        initial_response = await self.orchestrator.process_query(initial_message)
        
        # Step 2: Follow-up question in the created thread
        followup_ts = "1640995260.001600"
        followup_message = self.create_thread_reply_message(
            "Can you give me more details about the automation capabilities?",
            original_ts,  # This becomes the thread_ts
            followup_ts
        )
        
        followup_response = await self.orchestrator.process_query(followup_message)
        
        # Step 3: Third message in same thread
        third_ts = "1640995320.001700"
        third_message = self.create_thread_reply_message(
            "How does it compare to the previous version?",
            original_ts,  # Same thread
            third_ts
        )
        
        third_response = await self.orchestrator.process_query(third_message)
        
        # Verify conversation history is maintained
        conversation_key = f"conv:C987654321:{original_ts}"
        recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=5)
        
        result = {
            "initial_response": initial_response is not None,
            "followup_response": followup_response is not None,
            "third_response": third_response is not None,
            "thread_ts_consistent": all([
                initial_response.get("thread_ts") == original_ts,
                followup_response.get("thread_ts") == original_ts,
                third_response.get("thread_ts") == original_ts
            ]) if all([initial_response, followup_response, third_response]) else False,
            "conversation_messages_stored": len(recent_messages),
            "memory_working": len(recent_messages) >= 3,
            "conversation_key": conversation_key,
            "sample_stored_messages": [msg.get("text", "")[:50] + "..." for msg in recent_messages[-3:]]
        }
        
        print(f"✅ Conversation continuity test: {'PASS' if result['memory_working'] and result['thread_ts_consistent'] else 'FAIL'}")
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all thread functionality tests"""
        print("🚀 Starting Thread Functionality Tests")
        print("=" * 50)
        
        test1_result = await self.test_channel_mention_creates_thread()
        print()
        
        test2_result = await self.test_thread_conversation_continuity()
        print()
        
        # Overall assessment
        overall_success = (
            test1_result.get("thread_created_correctly", False) and
            test2_result.get("memory_working", False) and 
            test2_result.get("thread_ts_consistent", False)
        )
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_success": overall_success,
            "test_results": {
                "test1_channel_mention": test1_result,
                "test2_conversation_continuity": test2_result
            },
            "assessment": "PASS - Thread functionality working correctly" if overall_success else "FAIL - Thread functionality needs fixes"
        }
        
        print("📊 FINAL ASSESSMENT")
        print("=" * 50)
        print(f"Thread Creation: {'✅ PASS' if test1_result.get('thread_created_correctly') else '❌ FAIL'}")
        print(f"Memory Continuity: {'✅ PASS' if test2_result.get('memory_working') else '❌ FAIL'}")  
        print(f"Thread Consistency: {'✅ PASS' if test2_result.get('thread_ts_consistent') else '❌ FAIL'}")
        print(f"Overall: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        return summary

async def main():
    """Run the thread functionality tests"""
    test_suite = ThreadFunctionalityTest()
    results = await test_suite.run_all_tests()
    
    # Print detailed results
    print("\n📋 DETAILED RESULTS")
    print("=" * 50)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())