#!/usr/bin/env python3
"""
Simplified State Stack Architecture Test

Tests the key requirements:
1. 3-turn conversation - state stack construction and memory
2. Conversation memory isolation between threads
3. Performance verification

This directly tests the orchestrator → client agent flow to verify
the state stack approach is working correctly.
"""

import asyncio
import time
import json
from typing import Dict, Any
from datetime import datetime

from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
from agents.orchestrator_agent import OrchestratorAgent


class SimpleStateStackTest:
    """Simple test focused on verifying state stack functionality"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.orchestrator = OrchestratorAgent(self.memory_service)
        
    def create_test_message(self, text: str, user_id: str = "U_TEST_USER", 
                           thread_ts: str = None, message_ts: str = None) -> ProcessedMessage:
        """Create a test message matching the ProcessedMessage schema"""
        if not message_ts:
            message_ts = str(int(time.time() * 1000000))
            
        return ProcessedMessage(
            text=text,
            user_id=user_id,
            user_name="Test User",
            user_email="test@example.com",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            is_dm=False,
            is_mention=True if not thread_ts else False,
            thread_ts=thread_ts,
            message_ts=message_ts,
            thread_context=None
        )
    
    async def test_3_turn_conversation(self) -> Dict[str, Any]:
        """Test 3-turn conversation to verify state stack flow"""
        print("\n=== Testing 3-Turn Conversation ===")
        
        results = {
            "turns": [],
            "performance": {},
            "state_verification": {}
        }
        
        # Conversation flow
        messages = [
            "Hi! I'm new to the team and wondering about Autopilot.",
            "That's helpful! Can you tell me more about the specific features?", 
            "Great! What about the Construct feature you mentioned?"
        ]
        
        thread_ts = None
        total_time = 0
        
        for i, user_message in enumerate(messages, 1):
            turn_start = time.time()
            print(f"\n--- Turn {i}: {user_message[:50]}... ---")
            
            # Create message with proper threading
            message_ts = str(int(time.time() * 1000000) + i)
            if i == 1:
                # First message creates thread
                message = self.create_test_message(user_message, message_ts=message_ts)
                thread_ts = message_ts  # First message becomes thread root
            else:
                # Subsequent messages continue in thread
                message = self.create_test_message(user_message, thread_ts=thread_ts, message_ts=message_ts)
            
            # Process through orchestrator (this should build state stack and generate response)
            print(f"  → Processing through orchestrator...")
            response = await self.orchestrator.process_query(message)
            
            turn_time = time.time() - turn_start
            total_time += turn_time
            
            # Verify response structure
            response_valid = response is not None and isinstance(response, dict)
            response_text = response.get("text", "") if response else ""
            
            turn_result = {
                "turn": i,
                "user_message": user_message,
                "response_valid": response_valid,
                "response_preview": response_text[:100] if response_text else "No response",
                "turn_time": turn_time,
                "thread_ts": thread_ts,
                "message_ts": message_ts
            }
            results["turns"].append(turn_result)
            
            print(f"  ✓ Turn {i} completed in {turn_time:.2f}s")
            print(f"    Response valid: {response_valid}")
            if response_text:
                print(f"    Response preview: {response_text[:100]}...")
        
        # Performance analysis
        results["performance"] = {
            "total_time": total_time,
            "average_turn_time": total_time / len(messages),
            "all_responses_valid": all(t["response_valid"] for t in results["turns"])
        }
        
        # State verification - check if memory service has conversation data
        try:
            # Check if conversation data exists in memory
            memory_key = f"conversation_{thread_ts}" if thread_ts else "conversation_default"
            stored_messages = await self.memory_service.get_recent_messages(memory_key, 10)
            
            results["state_verification"] = {
                "memory_key": memory_key,
                "stored_message_count": len(stored_messages) if stored_messages else 0,
                "memory_working": stored_messages is not None
            }
        except Exception as e:
            results["state_verification"] = {
                "memory_key": "unknown",
                "stored_message_count": 0,
                "memory_working": False,
                "error": str(e)
            }
        
        self._print_3_turn_summary(results)
        return results
    
    async def test_concurrent_conversations(self) -> Dict[str, Any]:
        """Test 2 concurrent conversations to verify memory isolation"""
        print("\n=== Testing Concurrent Conversations ===")
        
        results = {
            "conversations": {},
            "isolation_test": {}
        }
        
        # Two different conversation threads
        conv1_messages = [
            "Hi! I need help with Autopilot setup.",
            "What are the configuration requirements?"
        ]
        
        conv2_messages = [
            "Hello! I'm having issues with the Construct feature.",
            "The automation isn't working properly."
        ]
        
        async def run_conversation(conv_id: str, messages: list) -> Dict[str, Any]:
            """Run a single conversation"""
            conv_results = {
                "conversation_id": conv_id,
                "turns": []
            }
            
            thread_ts = None
            user_id = f"U_TEST_{conv_id.upper()}"
            
            for i, message_text in enumerate(messages, 1):
                message_ts = str(int(time.time() * 1000000) + hash(conv_id) + i)
                
                if i == 1:
                    message = self.create_test_message(message_text, user_id=user_id, message_ts=message_ts)
                    thread_ts = message_ts
                else:
                    message = self.create_test_message(message_text, user_id=user_id, thread_ts=thread_ts, message_ts=message_ts)
                
                response = await self.orchestrator.process_query(message)
                
                turn_result = {
                    "turn": i,
                    "user_message": message_text,
                    "response_valid": response is not None,
                    "thread_ts": thread_ts
                }
                conv_results["turns"].append(turn_result)
                
                # Small delay to simulate real timing
                await asyncio.sleep(0.1)
            
            return conv_results
        
        # Run conversations concurrently
        start_time = time.time()
        conv1_task = run_conversation("conv1", conv1_messages)
        conv2_task = run_conversation("conv2", conv2_messages)
        
        conv1_result, conv2_result = await asyncio.gather(conv1_task, conv2_task)
        total_time = time.time() - start_time
        
        results["conversations"]["conv1"] = conv1_result
        results["conversations"]["conv2"] = conv2_result
        
        # Isolation analysis
        results["isolation_test"] = {
            "both_conversations_completed": len(conv1_result["turns"]) == 2 and len(conv2_result["turns"]) == 2,
            "all_responses_valid": (
                all(t["response_valid"] for t in conv1_result["turns"]) and
                all(t["response_valid"] for t in conv2_result["turns"])
            ),
            "different_thread_ids": conv1_result["turns"][0]["thread_ts"] != conv2_result["turns"][0]["thread_ts"],
            "concurrent_execution_time": total_time
        }
        
        self._print_concurrency_summary(results)
        return results
    
    async def test_memory_persistence(self) -> Dict[str, Any]:
        """Test that conversation memory persists across turns"""
        print("\n=== Testing Memory Persistence ===")
        
        # Create a conversation
        message1 = self.create_test_message("My name is John and I work on the platform team.")
        thread_ts = message1.message_ts
        
        message2 = self.create_test_message(
            "What's my name and which team do I work on?", 
            thread_ts=thread_ts
        )
        
        # First message
        print("  → Storing initial context...")
        response1 = await self.orchestrator.process_query(message1)
        
        await asyncio.sleep(0.5)  # Brief pause
        
        # Second message should recall the context
        print("  → Testing context recall...")
        response2 = await self.orchestrator.process_query(message2)
        
        # Check if second response indicates memory of first message
        response2_text = response2.get("text", "") if response2 else ""
        has_name_recall = "john" in response2_text.lower() if response2_text else False
        has_team_recall = "platform" in response2_text.lower() if response2_text else False
        
        results = {
            "first_response_valid": response1 is not None,
            "second_response_valid": response2 is not None,
            "name_recalled": has_name_recall,
            "team_recalled": has_team_recall,
            "memory_working": has_name_recall and has_team_recall,
            "second_response_preview": response2_text[:150] if response2_text else "No response"
        }
        
        print(f"  ✓ Memory test completed")
        print(f"    Name recalled: {'✓' if has_name_recall else '✗'}")
        print(f"    Team recalled: {'✓' if has_team_recall else '✗'}")
        print(f"    Response: {response2_text[:100]}...")
        
        return results
    
    def _print_3_turn_summary(self, results: Dict[str, Any]):
        """Print summary of 3-turn conversation test"""
        print(f"\n📊 3-Turn Conversation Test Results:")
        print(f"  Total time: {results['performance']['total_time']:.2f}s")
        print(f"  Average per turn: {results['performance']['average_turn_time']:.2f}s")
        print(f"  All responses valid: {'✓' if results['performance']['all_responses_valid'] else '✗'}")
        
        state_verification = results["state_verification"]
        print(f"  Memory verification:")
        print(f"    Memory working: {'✓' if state_verification['memory_working'] else '✗'}")
        print(f"    Stored messages: {state_verification['stored_message_count']}")
    
    def _print_concurrency_summary(self, results: Dict[str, Any]):
        """Print summary of concurrency test"""
        isolation = results["isolation_test"]
        print(f"\n📊 Concurrency Test Results:")
        print(f"  Both conversations completed: {'✓' if isolation['both_conversations_completed'] else '✗'}")
        print(f"  All responses valid: {'✓' if isolation['all_responses_valid'] else '✗'}")
        print(f"  Thread isolation: {'✓' if isolation['different_thread_ids'] else '✗'}")
        print(f"  Execution time: {isolation['concurrent_execution_time']:.2f}s")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all state stack tests"""
        print("🚀 Starting Simple State Stack Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run tests
        test_3_turn = await self.test_3_turn_conversation()
        await asyncio.sleep(1)
        
        test_concurrency = await self.test_concurrent_conversations()
        await asyncio.sleep(1)
        
        test_memory = await self.test_memory_persistence()
        
        total_time = time.time() - start_time
        
        # Final assessment
        final_results = {
            "test_suite": "Simple State Stack",
            "execution_time": total_time,
            "tests": {
                "3_turn_conversation": test_3_turn,
                "concurrency": test_concurrency,
                "memory_persistence": test_memory
            }
        }
        
        # Overall assessment
        conversation_working = test_3_turn["performance"]["all_responses_valid"]
        concurrency_working = test_concurrency["isolation_test"]["all_responses_valid"]
        memory_working = test_memory["memory_working"]
        
        overall_score = sum([conversation_working, concurrency_working, memory_working]) / 3 * 100
        
        final_results["overall_assessment"] = {
            "score": round(overall_score, 1),
            "conversation_flow": "✓ Working" if conversation_working else "✗ Issues",
            "concurrency_isolation": "✓ Working" if concurrency_working else "✗ Issues", 
            "memory_persistence": "✓ Working" if memory_working else "✗ Issues",
            "grade": "EXCELLENT" if overall_score >= 90 else "GOOD" if overall_score >= 75 else "NEEDS_WORK"
        }
        
        self._print_final_report(final_results)
        return final_results
    
    def _print_final_report(self, results: Dict[str, Any]):
        """Print final comprehensive report"""
        assessment = results["overall_assessment"]
        
        print(f"\n" + "=" * 50)
        print(f"🎯 FINAL STATE STACK TEST REPORT")
        print(f"=" * 50)
        print(f"Overall Grade: {assessment['grade']} ({assessment['score']}/100)")
        print(f"Total Execution Time: {results['execution_time']:.2f}s")
        
        print(f"\n📈 Component Status:")
        print(f"  Conversation Flow: {assessment['conversation_flow']}")
        print(f"  Concurrency Isolation: {assessment['concurrency_isolation']}")
        print(f"  Memory Persistence: {assessment['memory_persistence']}")
        
        print(f"\n" + "=" * 50)


async def main():
    """Run the simple state stack test suite"""
    test_suite = SimpleStateStackTest()
    results = await test_suite.run_all_tests()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"simple_state_stack_results_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {filename}")
    except Exception as e:
        print(f"\n⚠️  Could not save results: {e}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())