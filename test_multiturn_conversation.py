#!/usr/bin/env python3
"""
Multi-Turn Conversation Test

Simulates a realistic 10-turn conversation:
1. User greets agent
2. User asks about Autopilot
3. User requests more detail
4. User asks about the Construct
5. Continue conversation naturally...

Tests conversation flow, memory, and prompt effectiveness over multiple turns.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService


class MultiTurnConversationTest:
    """Test multi-turn conversation with realistic user behavior"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.orchestrator = OrchestratorAgent(self.memory_service)
        self.client_agent = ClientAgent()
        self.conversation_history = []
        self.turn_count = 0
        
    def create_test_message(self, text: str) -> ProcessedMessage:
        """Create a test message with proper timestamp"""
        self.turn_count += 1
        message_ts = f"{int(time.time())}.{self.turn_count:06d}"
        
        return ProcessedMessage(
            text=text,
            user_id="U_TESTUSER",
            user_name="TestUser",
            channel_id="C_TESTCHANNEL",
            channel_name="autopilot-design",
            message_ts=message_ts,
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
    
    async def simulate_user_turn(self, user_message: str, turn_number: int) -> Dict[str, Any]:
        """Simulate one turn of user interaction"""
        print(f"\n{'='*60}")
        print(f"TURN {turn_number}: USER")
        print(f"{'='*60}")
        print(f"User: {user_message}")
        
        # Create message
        message = self.create_test_message(user_message)
        
        # Store user message in memory
        conversation_key = f"{message.channel_id}:{message.user_id}"
        message_data = {
            "text": message.text,
            "user_id": message.user_id,
            "user_name": message.user_name,
            "message_ts": message.message_ts,
            "is_bot": False
        }
        await self.memory_service.store_raw_message(conversation_key, message_data)
        
        # Process through agent system
        start_time = time.time()
        
        try:
            # Full agent processing
            response = await self.orchestrator.process_query(message)
            response_time = time.time() - start_time
            
            response_text = response.get("text", "") if response else ""
            suggestions = response.get("suggestions", []) if response else []
            
            print(f"\nAgent Response Time: {response_time:.2f}s")
            print(f"Agent: {response_text}")
            
            if suggestions:
                print(f"\nSuggestions ({len(suggestions)}):")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")
            
            # Store bot response in memory
            if response_text:
                bot_message_ts = f"{int(time.time())}.{self.turn_count + 1000:06d}"
                bot_message_data = {
                    "text": response_text,
                    "user_id": "U_BOT",
                    "user_name": "AutopilotBot",
                    "message_ts": bot_message_ts,
                    "is_bot": True
                }
                await self.memory_service.store_raw_message(conversation_key, bot_message_data)
            
            # Analyze response quality
            quality_metrics = self._analyze_response_quality(
                user_message, response_text, turn_number
            )
            
            turn_result = {
                "turn": turn_number,
                "user_message": user_message,
                "agent_response": response_text,
                "suggestions": suggestions,
                "response_time": round(response_time, 3),
                "quality_metrics": quality_metrics,
                "timestamp": datetime.now().isoformat()
            }
            
            self.conversation_history.append(turn_result)
            return turn_result
            
        except Exception as e:
            print(f"ERROR in turn {turn_number}: {str(e)}")
            error_result = {
                "turn": turn_number,
                "user_message": user_message,
                "error": str(e),
                "response_time": 0,
                "timestamp": datetime.now().isoformat()
            }
            self.conversation_history.append(error_result)
            return error_result
    
    def _analyze_response_quality(self, user_msg: str, response: str, turn: int) -> Dict[str, Any]:
        """Analyze the quality of the agent response"""
        metrics = {
            "has_response": bool(response),
            "response_length": len(response),
            "word_count": len(response.split()) if response else 0,
            "uses_markdown": any(marker in response for marker in ["*", "`", "_", "-"]),
            "mentions_autopilot": "autopilot" in response.lower(),
            "mentions_construct": "construct" in response.lower(),
            "persona_indicators": sum(1 for word in ["design", "experience", "quality", "nerd"] 
                                    if word in response.lower()),
            "contextual_continuity": self._check_contextual_continuity(response, turn),
            "addresses_user_query": self._check_query_relevance(user_msg, response)
        }
        
        # Calculate overall quality score
        quality_score = 0
        quality_score += 20 if metrics["has_response"] else 0
        quality_score += 15 if metrics["word_count"] > 30 else 0
        quality_score += 10 if metrics["uses_markdown"] else 0
        quality_score += 15 if metrics["mentions_autopilot"] else 0
        quality_score += 10 if metrics["persona_indicators"] > 0 else 0
        quality_score += 15 if metrics["contextual_continuity"] else 0
        quality_score += 15 if metrics["addresses_user_query"] else 0
        
        metrics["overall_score"] = quality_score
        return metrics
    
    def _check_contextual_continuity(self, response: str, turn: int) -> bool:
        """Check if response shows awareness of conversation context"""
        if turn <= 1:
            return True  # First turn doesn't need continuity
        
        continuity_indicators = [
            "earlier", "mentioned", "discussed", "talked about", "previous", 
            "continuing", "following up", "as we", "like i said", "building on"
        ]
        
        return any(indicator in response.lower() for indicator in continuity_indicators)
    
    def _check_query_relevance(self, user_msg: str, response: str) -> bool:
        """Check if response addresses the user's query"""
        user_words = set(user_msg.lower().split())
        response_words = set(response.lower().split())
        
        # Remove common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        user_words -= common_words
        response_words -= common_words
        
        if not user_words:
            return True
        
        overlap = len(user_words.intersection(response_words))
        return overlap / len(user_words) > 0.2  # At least 20% word overlap
    
    async def run_10_turn_conversation(self) -> Dict[str, Any]:
        """Run a realistic 10-turn conversation"""
        print("STARTING 10-TURN CONVERSATION TEST")
        print("Simulating realistic user interaction with agent")
        print("Testing conversation flow, memory, and prompt effectiveness\n")
        
        start_time = time.time()
        
        # Define the conversation flow
        conversation_turns = [
            "Hey there! How are you doing today?",
            "I'm working on some Autopilot designs and could use your expertise. What's your background?",
            "That's fascinating! Can you tell me more about the latest Autopilot design patterns?",
            "What about error handling in Autopilot interfaces? Any specific guidelines?",
            "You mentioned the Construct earlier. What exactly is that place like for AI agents?",
            "Interesting! How does your experience in the Construct influence your design recommendations?",
            "I'm struggling with user onboarding flows for AI interactions. Any thoughts?",
            "What's your take on the future of intelligent automation in UX design?",
            "How do you balance cutting-edge AI features with user familiarity?",
            "Thanks for all the insights! Any final thoughts on Autopilot design philosophy?"
        ]
        
        # Execute each turn
        for turn_num, user_message in enumerate(conversation_turns, 1):
            await self.simulate_user_turn(user_message, turn_num)
            
            # Small delay between turns to simulate human thinking time
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        
        # Analyze conversation performance
        performance_analysis = self._analyze_conversation_performance(total_time)
        
        # Print summary
        self._print_conversation_summary(performance_analysis)
        
        return {
            "conversation_history": self.conversation_history,
            "performance_analysis": performance_analysis,
            "total_duration": total_time
        }
    
    def _analyze_conversation_performance(self, total_time: float) -> Dict[str, Any]:
        """Analyze overall conversation performance"""
        successful_turns = [turn for turn in self.conversation_history if 'error' not in turn]
        
        if not successful_turns:
            return {"error": "No successful turns to analyze"}
        
        # Calculate metrics
        response_times = [turn["response_time"] for turn in successful_turns]
        quality_scores = [turn["quality_metrics"]["overall_score"] for turn in successful_turns]
        
        avg_response_time = sum(response_times) / len(response_times)
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        # Check for degradation over time
        early_times = response_times[:3]
        late_times = response_times[-3:]
        early_quality = quality_scores[:3]
        late_quality = quality_scores[-3:]
        
        time_degradation = (sum(late_times) / len(late_times)) - (sum(early_times) / len(early_times))
        quality_degradation = (sum(early_quality) / len(early_quality)) - (sum(late_quality) / len(late_quality))
        
        # Analyze conversation flow
        continuity_count = sum(1 for turn in successful_turns if turn["quality_metrics"]["contextual_continuity"])
        autopilot_mentions = sum(1 for turn in successful_turns if turn["quality_metrics"]["mentions_autopilot"])
        construct_mentions = sum(1 for turn in successful_turns if turn["quality_metrics"]["mentions_construct"])
        
        return {
            "total_turns": len(self.conversation_history),
            "successful_turns": len(successful_turns),
            "success_rate": len(successful_turns) / len(self.conversation_history) * 100,
            "average_response_time": round(avg_response_time, 3),
            "average_quality_score": round(avg_quality, 1),
            "response_time_degradation": round(time_degradation, 3),
            "quality_degradation": round(quality_degradation, 1),
            "conversation_metrics": {
                "contextual_continuity_rate": round(continuity_count / len(successful_turns) * 100, 1),
                "autopilot_engagement": round(autopilot_mentions / len(successful_turns) * 100, 1),
                "construct_mentions": construct_mentions,
                "total_conversation_time": round(total_time, 2)
            },
            "performance_assessment": self._get_performance_assessment(avg_response_time, avg_quality, time_degradation, quality_degradation)
        }
    
    def _get_performance_assessment(self, avg_time: float, avg_quality: float, 
                                  time_degradation: float, quality_degradation: float) -> str:
        """Generate overall performance assessment"""
        if avg_quality >= 80 and avg_time <= 5 and quality_degradation <= 5:
            return "EXCELLENT - Agent maintains high quality throughout conversation"
        elif avg_quality >= 70 and avg_time <= 8 and quality_degradation <= 10:
            return "GOOD - Agent performs well with minor degradation"
        elif avg_quality >= 60 and avg_time <= 12:
            return "FAIR - Agent shows reasonable performance but needs improvement"
        else:
            return "POOR - Agent needs significant optimization for multi-turn conversations"
    
    def _print_conversation_summary(self, analysis: Dict[str, Any]):
        """Print comprehensive conversation summary"""
        print(f"\n{'='*80}")
        print("MULTI-TURN CONVERSATION ANALYSIS")
        print(f"{'='*80}")
        
        print(f"\n📊 OVERALL METRICS:")
        print(f"   Total Turns: {analysis['total_turns']}")
        print(f"   Successful Turns: {analysis['successful_turns']}/{analysis['total_turns']} ({analysis['success_rate']:.1f}%)")
        print(f"   Average Response Time: {analysis['average_response_time']}s")
        print(f"   Average Quality Score: {analysis['average_quality_score']}/100")
        
        print(f"\n📈 PERFORMANCE TRENDS:")
        print(f"   Response Time Change: {analysis['response_time_degradation']:+.3f}s over conversation")
        print(f"   Quality Score Change: {analysis['quality_degradation']:+.1f} over conversation")
        
        print(f"\n🗣️ CONVERSATION FLOW:")
        conv_metrics = analysis['conversation_metrics']
        print(f"   Contextual Continuity: {conv_metrics['contextual_continuity_rate']:.1f}%")
        print(f"   Autopilot Engagement: {conv_metrics['autopilot_engagement']:.1f}%")
        print(f"   Construct Mentions: {conv_metrics['construct_mentions']}")
        print(f"   Total Duration: {conv_metrics['total_conversation_time']}s")
        
        print(f"\n🎯 ASSESSMENT: {analysis['performance_assessment']}")
        print(f"{'='*80}")


async def main():
    """Run the multi-turn conversation test"""
    test = MultiTurnConversationTest()
    results = await test.run_10_turn_conversation()
    
    # Save results
    with open('multiturn_conversation_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Detailed results saved to: multiturn_conversation_results.json")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())