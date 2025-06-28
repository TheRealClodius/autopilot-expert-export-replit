#!/usr/bin/env python3
"""
Manual State Stack Test

Instead of testing the full orchestrator pipeline (which seems to hang on complex Gemini calls),
this test manually constructs state stacks and tests the client agent's ability to process them.

This tests the core state stack architecture without the complexity of the orchestrator's
query analysis, which may be hanging due to complex prompts or timeouts.
"""

import asyncio
import time
import json
from typing import Dict, Any
from datetime import datetime

from agents.client_agent import ClientAgent
from services.memory_service import MemoryService


class ManualStateStackTest:
    """Test state stack architecture by manually constructing state stacks"""
    
    def __init__(self):
        self.client_agent = ClientAgent()
        self.memory_service = MemoryService()
        
    def create_state_stack(self, query: str, conversation_history: list = None, 
                          conversation_summary: str = "", orchestrator_insights: str = "") -> Dict[str, Any]:
        """Manually create a state stack similar to what orchestrator would build"""
        return {
            "query": query,
            "conversation_history": conversation_history or [],
            "conversation_summary": conversation_summary,
            "orchestrator_insights": orchestrator_insights,
            "gathered_information": {
                "vector_search_results": [],
                "relevant_context": "Test context for state stack verification"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "test_mode": True
            }
        }
    
    async def test_simple_state_stack(self) -> Dict[str, Any]:
        """Test 1: Simple greeting with minimal state stack"""
        print("\n=== Test 1: Simple State Stack ===")
        
        state_stack = self.create_state_stack(
            query="Hi! I'm new to the team and wondering about Autopilot.",
            orchestrator_insights="User is greeting and asking about Autopilot - respond with helpful introduction"
        )
        
        print(f"State stack size: {len(str(state_stack))} characters")
        print(f"Query: {state_stack['query']}")
        
        start_time = time.time()
        response = await self.client_agent.generate_response(state_stack)
        response_time = time.time() - start_time
        
        result = {
            "test": "simple_state_stack",
            "response_time": response_time,
            "response_valid": response is not None and isinstance(response, dict),
            "response_preview": response.get("text", "")[:150] if response else "No response",
            "state_stack_size": len(str(state_stack))
        }
        
        print(f"Response time: {response_time:.2f}s")
        print(f"Response valid: {result['response_valid']}")
        print(f"Response preview: {result['response_preview']}")
        
        return result
    
    async def test_conversation_state_stack(self) -> Dict[str, Any]:
        """Test 2: State stack with conversation history"""
        print("\n=== Test 2: Conversation State Stack ===")
        
        conversation_history = [
            {"role": "user", "text": "Hi! I'm new to the team.", "timestamp": "2025-06-28T09:00:00"},
            {"role": "assistant", "text": "Welcome to the team! I'm your Autopilot expert.", "timestamp": "2025-06-28T09:00:01"},
            {"role": "user", "text": "What exactly does Autopilot do?", "timestamp": "2025-06-28T09:00:30"}
        ]
        
        state_stack = self.create_state_stack(
            query="Can you tell me more about the specific features?",
            conversation_history=conversation_history,
            orchestrator_insights="User wants more detail about Autopilot features - build on previous context"
        )
        
        print(f"Conversation history: {len(conversation_history)} messages")
        print(f"Current query: {state_stack['query']}")
        
        start_time = time.time()
        response = await self.client_agent.generate_response(state_stack)
        response_time = time.time() - start_time
        
        result = {
            "test": "conversation_state_stack",
            "response_time": response_time,
            "response_valid": response is not None and isinstance(response, dict),
            "response_preview": response.get("text", "")[:150] if response else "No response",
            "conversation_context_used": len(conversation_history),
            "maintains_context": "autopilot" in response.get("text", "").lower() if response else False
        }
        
        print(f"Response time: {response_time:.2f}s")
        print(f"Response valid: {result['response_valid']}")
        print(f"Maintains context: {result['maintains_context']}")
        print(f"Response preview: {result['response_preview']}")
        
        return result
    
    async def test_long_conversation_state_stack(self) -> Dict[str, Any]:
        """Test 3: State stack with summarization (10+ messages)"""
        print("\n=== Test 3: Long Conversation State Stack (10+ messages) ===")
        
        # Simulate conversation history with 12 messages
        conversation_history = []
        for i in range(1, 11):  # 10 recent messages
            if i % 2 == 1:  # User messages
                conversation_history.append({
                    "role": "user", 
                    "text": f"User message {i} about Autopilot features", 
                    "timestamp": f"2025-06-28T09:{i:02d}:00"
                })
            else:  # Assistant messages
                conversation_history.append({
                    "role": "assistant", 
                    "text": f"Assistant response {i} explaining Autopilot", 
                    "timestamp": f"2025-06-28T09:{i:02d}:01"
                })
        
        # Conversation summary (would be auto-generated by orchestrator)
        conversation_summary = """
        Conversation Summary: User (John from platform team) has been learning about Autopilot. 
        We've discussed basic features, integration options, and automation capabilities. 
        User is particularly interested in design patterns and error handling approaches.
        """
        
        state_stack = self.create_state_stack(
            query="What are the best practices for error handling in Autopilot?",
            conversation_history=conversation_history,
            conversation_summary=conversation_summary,
            orchestrator_insights="User wants specific technical guidance on error handling - provide detailed best practices"
        )
        
        print(f"Conversation history: {len(conversation_history)} messages")
        print(f"Summary present: {bool(conversation_summary.strip())}")
        print(f"Current query: {state_stack['query']}")
        
        start_time = time.time()
        response = await self.client_agent.generate_response(state_stack)
        response_time = time.time() - start_time
        
        result = {
            "test": "long_conversation_state_stack",
            "response_time": response_time,
            "response_valid": response is not None and isinstance(response, dict),
            "response_preview": response.get("text", "")[:150] if response else "No response",
            "uses_summary": bool(conversation_summary.strip()),
            "uses_recent_history": len(conversation_history) == 10,
            "addresses_error_handling": "error" in response.get("text", "").lower() if response else False
        }
        
        print(f"Response time: {response_time:.2f}s")
        print(f"Response valid: {result['response_valid']}")
        print(f"Addresses error handling: {result['addresses_error_handling']}")
        print(f"Response preview: {result['response_preview']}")
        
        return result
    
    async def test_concurrent_state_stacks(self) -> Dict[str, Any]:
        """Test 4: Concurrent state stack processing (memory isolation)"""
        print("\n=== Test 4: Concurrent State Stack Processing ===")
        
        # Two different conversation contexts
        state_stack_1 = self.create_state_stack(
            query="I need help with Autopilot setup for e-commerce",
            conversation_history=[
                {"role": "user", "text": "Working on e-commerce platform", "timestamp": "2025-06-28T09:00:00"}
            ],
            orchestrator_insights="User needs e-commerce specific Autopilot guidance"
        )
        
        state_stack_2 = self.create_state_stack(
            query="How do I debug Construct automation issues?",
            conversation_history=[
                {"role": "user", "text": "Having trouble with Construct debugging", "timestamp": "2025-06-28T09:00:00"}
            ],
            orchestrator_insights="User needs Construct debugging help"
        )
        
        # Process both state stacks concurrently
        print("Processing two different state stacks concurrently...")
        
        start_time = time.time()
        response_1_task = self.client_agent.generate_response(state_stack_1)
        response_2_task = self.client_agent.generate_response(state_stack_2)
        
        response_1, response_2 = await asyncio.gather(response_1_task, response_2_task)
        total_time = time.time() - start_time
        
        # Analyze responses for cross-contamination
        response_1_text = response_1.get("text", "").lower() if response_1 else ""
        response_2_text = response_2.get("text", "").lower() if response_2 else ""
        
        # Check if responses stayed focused on their respective topics
        resp_1_on_topic = "e-commerce" in response_1_text or "setup" in response_1_text
        resp_2_on_topic = "debug" in response_2_text or "construct" in response_2_text
        
        # Check for inappropriate cross-contamination
        resp_1_contaminated = "debug" in response_1_text or "construct" in response_1_text
        resp_2_contaminated = "e-commerce" in response_2_text or "setup" in response_2_text
        
        result = {
            "test": "concurrent_state_stacks",
            "total_time": total_time,
            "both_responses_valid": response_1 is not None and response_2 is not None,
            "response_1_on_topic": resp_1_on_topic,
            "response_2_on_topic": resp_2_on_topic,
            "no_contamination": not resp_1_contaminated and not resp_2_contaminated,
            "memory_isolation": not resp_1_contaminated and not resp_2_contaminated,
            "response_1_preview": response_1_text[:100],
            "response_2_preview": response_2_text[:100]
        }
        
        print(f"Total concurrent time: {total_time:.2f}s")
        print(f"Both responses valid: {result['both_responses_valid']}")
        print(f"Memory isolation: {result['memory_isolation']}")
        print(f"Response 1 on topic: {result['response_1_on_topic']}")
        print(f"Response 2 on topic: {result['response_2_on_topic']}")
        
        return result
    
    async def test_performance_under_load(self) -> Dict[str, Any]:
        """Test 5: Performance with multiple rapid state stack requests"""
        print("\n=== Test 5: Performance Under Load ===")
        
        # Create 5 different state stacks for rapid processing
        state_stacks = []
        for i in range(5):
            state_stack = self.create_state_stack(
                query=f"Test query {i+1} about Autopilot performance",
                conversation_history=[
                    {"role": "user", "text": f"Context message {i+1}", "timestamp": f"2025-06-28T09:0{i}:00"}
                ],
                orchestrator_insights=f"Performance test query {i+1}"
            )
            state_stacks.append(state_stack)
        
        print(f"Processing {len(state_stacks)} state stacks rapidly...")
        
        start_time = time.time()
        
        # Process all state stacks concurrently
        tasks = [self.client_agent.generate_response(stack) for stack in state_stacks]
        responses = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze performance
        valid_responses = sum(1 for r in responses if r is not None)
        average_time = total_time / len(state_stacks)
        
        result = {
            "test": "performance_under_load",
            "total_requests": len(state_stacks),
            "valid_responses": valid_responses,
            "success_rate": valid_responses / len(state_stacks),
            "total_time": total_time,
            "average_response_time": average_time,
            "requests_per_second": len(state_stacks) / total_time,
            "system_responsive": average_time < 3.0  # Response under 3 seconds
        }
        
        print(f"Success rate: {result['success_rate']:.1%}")
        print(f"Average response time: {result['average_response_time']:.2f}s")
        print(f"Requests per second: {result['requests_per_second']:.1f}")
        print(f"System responsive: {result['system_responsive']}")
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all manual state stack tests"""
        print("🚀 Starting Manual State Stack Test Suite")
        print("=" * 60)
        print("Testing state stack architecture without orchestrator complexity")
        
        start_time = time.time()
        
        # Run all tests
        test_1 = await self.test_simple_state_stack()
        await asyncio.sleep(0.5)
        
        test_2 = await self.test_conversation_state_stack()
        await asyncio.sleep(0.5)
        
        test_3 = await self.test_long_conversation_state_stack()
        await asyncio.sleep(0.5)
        
        test_4 = await self.test_concurrent_state_stacks()
        await asyncio.sleep(0.5)
        
        test_5 = await self.test_performance_under_load()
        
        total_time = time.time() - start_time
        
        # Compile results
        results = {
            "test_suite": "Manual State Stack Architecture",
            "execution_time": total_time,
            "tests": {
                "simple_state_stack": test_1,
                "conversation_state_stack": test_2,
                "long_conversation_state_stack": test_3,
                "concurrent_state_stacks": test_4,
                "performance_under_load": test_5
            }
        }
        
        # Overall assessment
        all_tests = [test_1, test_2, test_3, test_4, test_5]
        valid_responses = sum(1 for test in all_tests if test.get("response_valid", False))
        
        results["overall_assessment"] = {
            "tests_passed": valid_responses,
            "total_tests": len(all_tests),
            "success_rate": valid_responses / len(all_tests),
            "state_stack_working": valid_responses >= 4,  # At least 4/5 tests pass
            "client_agent_responsive": all(test.get("response_time", 10) < 5.0 for test in all_tests if "response_time" in test),
            "memory_isolation": test_4.get("memory_isolation", False),
            "performance_acceptable": test_5.get("system_responsive", False)
        }
        
        self._print_final_report(results)
        return results
    
    def _print_final_report(self, results: Dict[str, Any]):
        """Print comprehensive final report"""
        assessment = results["overall_assessment"]
        
        print(f"\n" + "=" * 60)
        print(f"🎯 MANUAL STATE STACK TEST REPORT")
        print(f"=" * 60)
        print(f"Success Rate: {assessment['success_rate']:.1%} ({assessment['tests_passed']}/{assessment['total_tests']} tests passed)")
        print(f"Total Execution Time: {results['execution_time']:.2f}s")
        
        print(f"\n📈 Key Findings:")
        print(f"  ✓ State Stack Working: {'Yes' if assessment['state_stack_working'] else 'No'}")
        print(f"  ✓ Client Agent Responsive: {'Yes' if assessment['client_agent_responsive'] else 'No'}")
        print(f"  ✓ Memory Isolation: {'Yes' if assessment['memory_isolation'] else 'No'}")
        print(f"  ✓ Performance Acceptable: {'Yes' if assessment['performance_acceptable'] else 'No'}")
        
        print(f"\n🔍 Test Details:")
        for test_name, test_result in results["tests"].items():
            status = "✓" if test_result.get("response_valid", False) else "✗"
            time_taken = test_result.get("response_time", test_result.get("total_time", 0))
            print(f"  {status} {test_name}: {time_taken:.2f}s")
        
        grade = "EXCELLENT" if assessment['success_rate'] >= 0.9 else "GOOD" if assessment['success_rate'] >= 0.8 else "NEEDS_WORK"
        print(f"\nOverall Grade: {grade}")
        print(f"=" * 60)


async def main():
    """Run the manual state stack test suite"""
    test_suite = ManualStateStackTest()
    results = await test_suite.run_all_tests()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"manual_state_stack_results_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {filename}")
    except Exception as e:
        print(f"\n⚠️  Could not save results: {e}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())