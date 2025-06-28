#!/usr/bin/env python3
"""
Comprehensive Agent Performance Test Suite

Tests the multi-agent system with new prompts for:
1. Simple greeting responses
2. Conversation starting with a joke
3. Long-running 20-message conversation

Metrics tracked:
- Response time
- Response quality (creativity, relevance, adherence to persona)
- Adherence to conversation history
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from agents.observer_agent import ObserverAgent
from services.memory_service import MemoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentPerformanceTest:
    """Test suite for evaluating agent performance with new prompts"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.orchestrator = OrchestratorAgent(self.memory_service)
        self.client_agent = ClientAgent()
        self.observer_agent = ObserverAgent()
        self.test_results = {}
        
    def create_test_message(self, text: str, user_id: str = "U_TEST_USER", 
                           thread_ts: str = None, message_ts: str = None) -> ProcessedMessage:
        """Create a test message with consistent formatting"""
        if message_ts is None:
            message_ts = f"{int(time.time())}.{int(time.time() * 1000000) % 1000000:06d}"
            
        return ProcessedMessage(
            text=text,
            user_id=user_id,
            user_name="TestUser",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=message_ts,
            thread_ts=thread_ts,
            is_dm=False,
            thread_context=None
        )
    
    async def measure_response_time(self, message: ProcessedMessage) -> Tuple[float, Dict[str, Any]]:
        """Measure end-to-end response time and return response"""
        start_time = time.time()
        
        try:
            # Full agent processing pipeline
            response = await self.orchestrator.process_query(message)
            end_time = time.time()
            
            response_time = end_time - start_time
            return response_time, response
            
        except Exception as e:
            logger.error(f"Error in response processing: {e}")
            return 0.0, {"error": str(e)}
    
    def evaluate_response_quality(self, message: ProcessedMessage, response: Dict[str, Any], 
                                conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """Evaluate response quality based on multiple criteria"""
        quality_metrics = {
            "has_response": bool(response.get("text")),
            "response_length": len(response.get("text", "")),
            "mentions_autopilot": "autopilot" in response.get("text", "").lower(),
            "uses_markdown": any(marker in response.get("text", "") for marker in ["*", "`", "_", "-"]),
            "has_suggestions": bool(response.get("suggestions", [])),
            "persona_adherence": self._evaluate_persona_adherence(response.get("text", "")),
            "contextual_relevance": self._evaluate_contextual_relevance(message.text, response.get("text", "")),
            "conversation_coherence": self._evaluate_conversation_coherence(message, response, conversation_context)
        }
        
        # Calculate overall quality score (0-100)
        quality_score = sum([
            20 if quality_metrics["has_response"] else 0,
            10 if quality_metrics["response_length"] > 50 else 0,
            15 if quality_metrics["persona_adherence"] > 0.5 else 0,
            15 if quality_metrics["contextual_relevance"] > 0.5 else 0,
            10 if quality_metrics["uses_markdown"] else 0,
            10 if quality_metrics["has_suggestions"] else 0,
            20 if quality_metrics["conversation_coherence"] > 0.5 else 0
        ])
        
        quality_metrics["overall_score"] = quality_score
        return quality_metrics
    
    def _evaluate_persona_adherence(self, response_text: str) -> float:
        """Evaluate how well response adheres to the design-focused, nerdy Autopilot expert persona"""
        persona_indicators = [
            "design", "experience", "quality", "user", "interaction",
            "autopilot", "automation", "construct", "nerd", "expert"
        ]
        
        text_lower = response_text.lower()
        matches = sum(1 for indicator in persona_indicators if indicator in text_lower)
        return min(matches / len(persona_indicators), 1.0)
    
    def _evaluate_contextual_relevance(self, query: str, response: str) -> float:
        """Evaluate how relevant the response is to the original query"""
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        
        if not query_words:
            return 0.0
            
        # Calculate word overlap (simple but effective for basic relevance)
        overlap = len(query_words.intersection(response_words))
        return min(overlap / len(query_words), 1.0)
    
    def _evaluate_conversation_coherence(self, message: ProcessedMessage, response: Dict[str, Any], 
                                       conversation_context: List[Dict] = None) -> float:
        """Evaluate how well the response maintains conversation coherence"""
        if not conversation_context:
            return 1.0  # No previous context to maintain
            
        # Check if response acknowledges previous messages
        response_text = response.get("text", "").lower()
        
        # Look for conversation continuity indicators
        continuity_indicators = [
            "earlier", "mentioned", "discussed", "talked about", 
            "previous", "before", "continuing", "following up"
        ]
        
        has_continuity = any(indicator in response_text for indicator in continuity_indicators)
        
        # Check if response references recent topics
        recent_topics = []
        for msg in conversation_context[-3:]:  # Last 3 messages
            recent_topics.extend(msg.get("text", "").lower().split())
        
        response_words = response_text.split()
        topic_overlap = len(set(recent_topics).intersection(set(response_words)))
        
        coherence_score = (
            (0.6 if has_continuity else 0.0) +
            (0.4 * min(topic_overlap / 10, 1.0))  # Normalize topic overlap
        )
        
        return coherence_score
    
    async def test_simple_greeting(self) -> Dict[str, Any]:
        """Test 1: Simple greeting response"""
        print("\n" + "="*60)
        print("TEST 1: SIMPLE GREETING")
        print("="*60)
        
        test_message = self.create_test_message("Hey buddy")
        
        # Measure response
        response_time, response = await self.measure_response_time(test_message)
        
        # Evaluate quality
        quality_metrics = self.evaluate_response_quality(test_message, response)
        
        result = {
            "test_type": "simple_greeting",
            "query": test_message.text,
            "response_time_seconds": round(response_time, 3),
            "response": response.get("text", ""),
            "suggestions": response.get("suggestions", []),
            "quality_metrics": quality_metrics
        }
        
        print(f"Query: {test_message.text}")
        print(f"Response Time: {response_time:.3f}s")
        print(f"Response: {response.get('text', 'No response')}")
        print(f"Quality Score: {quality_metrics['overall_score']}/100")
        
        return result
    
    async def test_joke_conversation(self) -> Dict[str, Any]:
        """Test 2: Conversation starting with a joke"""
        print("\n" + "="*60)
        print("TEST 2: JOKE CONVERSATION")
        print("="*60)
        
        messages = [
            "Why don't robots ever panic? Because they have great automation!",
            "That's actually pretty funny! Speaking of automation, what's new with Autopilot?",
            "I'm curious about the latest design patterns for AI interactions"
        ]
        
        conversation_results = []
        conversation_context = []
        
        for i, msg_text in enumerate(messages):
            test_message = self.create_test_message(msg_text)
            
            # Store message in memory for context
            await self.memory_service.store_raw_message(
                test_message.channel_id, test_message.user_id, 
                test_message.text, test_message.message_ts
            )
            conversation_context.append({"text": msg_text, "timestamp": test_message.message_ts})
            
            # Measure response
            response_time, response = await self.measure_response_time(test_message)
            
            # Evaluate quality with conversation context
            quality_metrics = self.evaluate_response_quality(
                test_message, response, conversation_context[:-1]  # Previous messages only
            )
            
            result = {
                "message_number": i + 1,
                "query": msg_text,
                "response_time_seconds": round(response_time, 3),
                "response": response.get("text", ""),
                "quality_metrics": quality_metrics
            }
            
            conversation_results.append(result)
            
            print(f"\nMessage {i+1}: {msg_text}")
            print(f"Response Time: {response_time:.3f}s")
            print(f"Response: {response.get('text', 'No response')[:100]}...")
            print(f"Quality Score: {quality_metrics['overall_score']}/100")
            
            # Add bot response to context
            if response.get("text"):
                conversation_context.append({
                    "text": response["text"], 
                    "timestamp": test_message.message_ts,
                    "is_bot": True
                })
        
        # Calculate conversation-level metrics
        avg_response_time = sum(r["response_time_seconds"] for r in conversation_results) / len(conversation_results)
        avg_quality_score = sum(r["quality_metrics"]["overall_score"] for r in conversation_results) / len(conversation_results)
        
        return {
            "test_type": "joke_conversation",
            "total_messages": len(messages),
            "average_response_time": round(avg_response_time, 3),
            "average_quality_score": round(avg_quality_score, 1),
            "conversation_results": conversation_results
        }
    
    async def test_long_conversation(self) -> Dict[str, Any]:
        """Test 3: Long-running 20-message conversation"""
        print("\n" + "="*60)
        print("TEST 3: LONG CONVERSATION (20 MESSAGES)")
        print("="*60)
        
        # Simulate a realistic conversation about Autopilot
        messages = [
            "Hi there! I'm new to Autopilot and need some guidance",
            "What's the best way to get started with Autopilot design patterns?",
            "I'm working on a dashboard design. Any specific guidelines?",
            "What about color schemes and typography for Autopilot interfaces?",
            "How do you handle error states in Autopilot designs?",
            "Are there any accessibility considerations I should know about?",
            "What's the difference between Autopilot and traditional UiPath Studio?",
            "Can you show me some examples of good Autopilot workflows?",
            "I'm struggling with user onboarding flows. Any tips?",
            "What's coming next in Autopilot development?",
            "How do you approach responsive design for Autopilot?",
            "Are there any design system components I should use?",
            "What about animation and micro-interactions?",
            "How do you test Autopilot designs with users?",
            "What's the best practice for form design in Autopilot?",
            "Can you explain the concept of 'intelligent automation' in design?",
            "How do you handle complex data visualization in Autopilot?",
            "What about mobile considerations for Autopilot interfaces?",
            "Are there any performance considerations for Autopilot designs?",
            "Thanks for all the help! Any final thoughts on Autopilot design?"
        ]
        
        conversation_results = []
        conversation_context = []
        response_times = []
        quality_scores = []
        
        for i, msg_text in enumerate(messages):
            test_message = self.create_test_message(msg_text)
            
            # Store message in memory for context
            await self.memory_service.store_raw_message(
                test_message.channel_id, test_message.user_id, 
                test_message.text, test_message.message_ts
            )
            conversation_context.append({"text": msg_text, "timestamp": test_message.message_ts})
            
            # Measure response
            response_time, response = await self.measure_response_time(test_message)
            response_times.append(response_time)
            
            # Evaluate quality with full conversation context
            quality_metrics = self.evaluate_response_quality(
                test_message, response, conversation_context[:-1]
            )
            quality_scores.append(quality_metrics['overall_score'])
            
            result = {
                "message_number": i + 1,
                "query": msg_text,
                "response_time_seconds": round(response_time, 3),
                "response": response.get("text", ""),
                "quality_metrics": quality_metrics
            }
            
            conversation_results.append(result)
            
            # Progress indicator
            if (i + 1) % 5 == 0:
                print(f"Completed {i + 1}/20 messages...")
            
            # Add bot response to context
            if response.get("text"):
                conversation_context.append({
                    "text": response["text"], 
                    "timestamp": test_message.message_ts,
                    "is_bot": True
                })
        
        # Calculate comprehensive metrics
        avg_response_time = sum(response_times) / len(response_times)
        avg_quality_score = sum(quality_scores) / len(quality_scores)
        
        # Performance trends
        early_avg_time = sum(response_times[:5]) / 5
        late_avg_time = sum(response_times[-5:]) / 5
        time_degradation = late_avg_time - early_avg_time
        
        early_avg_quality = sum(quality_scores[:5]) / 5
        late_avg_quality = sum(quality_scores[-5:]) / 5
        quality_degradation = early_avg_quality - late_avg_quality
        
        print(f"\nLong Conversation Complete!")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"Average Quality Score: {avg_quality_score:.1f}/100")
        print(f"Response Time Change: {time_degradation:+.3f}s (early vs late)")
        print(f"Quality Score Change: {quality_degradation:+.1f} (early vs late)")
        
        return {
            "test_type": "long_conversation",
            "total_messages": 20,
            "average_response_time": round(avg_response_time, 3),
            "average_quality_score": round(avg_quality_score, 1),
            "response_time_degradation": round(time_degradation, 3),
            "quality_degradation": round(quality_degradation, 1),
            "early_performance": {
                "avg_time": round(early_avg_time, 3),
                "avg_quality": round(early_avg_quality, 1)
            },
            "late_performance": {
                "avg_time": round(late_avg_time, 3),
                "avg_quality": round(late_avg_quality, 1)
            },
            "conversation_results": conversation_results
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests and generate comprehensive report"""
        print("Starting Agent Performance Test Suite...")
        print("Testing system with new prompts from prompts.yaml")
        start_time = time.time()
        
        # Run all tests
        test1_result = await self.test_simple_greeting()
        test2_result = await self.test_joke_conversation()
        test3_result = await self.test_long_conversation()
        
        total_time = time.time() - start_time
        
        # Generate summary report
        summary = {
            "test_suite_duration": round(total_time, 2),
            "timestamp": datetime.now().isoformat(),
            "simple_greeting": {
                "response_time": test1_result["response_time_seconds"],
                "quality_score": test1_result["quality_metrics"]["overall_score"]
            },
            "joke_conversation": {
                "avg_response_time": test2_result["average_response_time"],
                "avg_quality_score": test2_result["average_quality_score"]
            },
            "long_conversation": {
                "avg_response_time": test3_result["average_response_time"],
                "avg_quality_score": test3_result["average_quality_score"],
                "performance_degradation": {
                    "time": test3_result["response_time_degradation"],
                    "quality": test3_result["quality_degradation"]
                }
            },
            "overall_assessment": self._generate_overall_assessment(test1_result, test2_result, test3_result)
        }
        
        # Print final report
        self._print_final_report(summary)
        
        return {
            "summary": summary,
            "detailed_results": {
                "simple_greeting": test1_result,
                "joke_conversation": test2_result,
                "long_conversation": test3_result
            }
        }
    
    def _generate_overall_assessment(self, test1, test2, test3) -> Dict[str, Any]:
        """Generate overall assessment of agent performance"""
        avg_response_time = (
            test1["response_time_seconds"] + 
            test2["average_response_time"] + 
            test3["average_response_time"]
        ) / 3
        
        avg_quality_score = (
            test1["quality_metrics"]["overall_score"] + 
            test2["average_quality_score"] + 
            test3["average_quality_score"]
        ) / 3
        
        # Performance categories
        time_rating = "excellent" if avg_response_time < 2 else "good" if avg_response_time < 5 else "needs_improvement"
        quality_rating = "excellent" if avg_quality_score > 80 else "good" if avg_quality_score > 60 else "needs_improvement"
        
        return {
            "average_response_time": round(avg_response_time, 3),
            "average_quality_score": round(avg_quality_score, 1),
            "time_performance": time_rating,
            "quality_performance": quality_rating,
            "conversation_coherence": "good" if test3["quality_degradation"] < 10 else "needs_improvement",
            "prompt_effectiveness": "high" if avg_quality_score > 70 and avg_response_time < 5 else "medium"
        }
    
    def _print_final_report(self, summary: Dict[str, Any]):
        """Print a comprehensive final report"""
        print("\n" + "="*80)
        print("AGENT PERFORMANCE TEST REPORT")
        print("="*80)
        
        assessment = summary["overall_assessment"]
        
        print(f"\n📊 OVERALL PERFORMANCE:")
        print(f"   Average Response Time: {assessment['average_response_time']}s ({assessment['time_performance']})")
        print(f"   Average Quality Score: {assessment['average_quality_score']}/100 ({assessment['quality_performance']})")
        print(f"   Conversation Coherence: {assessment['conversation_coherence']}")
        print(f"   Prompt Effectiveness: {assessment['prompt_effectiveness']}")
        
        print(f"\n🧪 TEST RESULTS:")
        print(f"   Simple Greeting: {summary['simple_greeting']['response_time']}s, {summary['simple_greeting']['quality_score']}/100")
        print(f"   Joke Conversation: {summary['joke_conversation']['avg_response_time']}s, {summary['joke_conversation']['avg_quality_score']}/100")
        print(f"   Long Conversation: {summary['long_conversation']['avg_response_time']}s, {summary['long_conversation']['avg_quality_score']}/100")
        
        print(f"\n📈 PERFORMANCE TRENDS:")
        degradation = summary['long_conversation']['performance_degradation']
        print(f"   Response Time Change: {degradation['time']:+.3f}s over 20 messages")
        print(f"   Quality Score Change: {degradation['quality']:+.1f} over 20 messages")
        
        print(f"\n⏱️  Total Test Duration: {summary['test_suite_duration']}s")
        print("="*80)


async def main():
    """Main function to run the performance tests"""
    test_suite = AgentPerformanceTest()
    results = await test_suite.run_all_tests()
    
    # Save results to file
    with open('agent_performance_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Test results saved to: agent_performance_results.json")


if __name__ == "__main__":
    asyncio.run(main())