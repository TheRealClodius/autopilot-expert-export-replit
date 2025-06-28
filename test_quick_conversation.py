#!/usr/bin/env python3
"""
Quick 3-Turn Conversation Test

Tests the new prompts with a focused conversation:
1. User greets agent  
2. User asks about Autopilot
3. User asks about the Construct

Provides rapid feedback on prompt effectiveness.
"""

import asyncio
import json
import time
from typing import Dict, Any
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService


async def test_conversation_flow():
    """Test a quick 3-turn conversation to evaluate prompts"""
    print("QUICK 3-TURN CONVERSATION TEST")
    print("Testing new prompts with key scenarios\n")
    
    # Initialize agents
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    conversation_turns = [
        "Hey buddy, how are you doing today?",
        "I'm working on Autopilot designs. What's your background in design?", 
        "Tell me about the Construct - what's it like for AI agents?"
    ]
    
    results = []
    conversation_key = "C_TEST:U_TEST"
    
    for turn_num, user_message in enumerate(conversation_turns, 1):
        print(f"{'='*50}")
        print(f"TURN {turn_num}")
        print(f"{'='*50}")
        print(f"User: {user_message}")
        
        # Create message
        message = ProcessedMessage(
            text=user_message,
            user_id="U_TEST",
            user_name="TestUser", 
            channel_id="C_TEST",
            channel_name="autopilot-design",
            message_ts=f"{int(time.time())}.{turn_num:06d}",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        # Store user message in memory
        user_data = {
            "text": user_message,
            "user_id": "U_TEST",
            "user_name": "TestUser",
            "message_ts": message.message_ts,
            "is_bot": False
        }
        await memory_service.store_raw_message(conversation_key, user_data)
        
        # Process message
        start_time = time.time()
        
        try:
            response = await orchestrator.process_query(message)
            response_time = time.time() - start_time
            
            response_text = response.get("text", "") if response else ""
            suggestions = response.get("suggestions", []) if response else []
            
            print(f"\nResponse Time: {response_time:.2f}s")
            print(f"Agent: {response_text}")
            
            if suggestions:
                print(f"\nSuggestions: {suggestions}")
            
            # Store bot response
            if response_text:
                bot_data = {
                    "text": response_text,
                    "user_id": "U_BOT", 
                    "user_name": "AutopilotBot",
                    "message_ts": f"{int(time.time())}.{turn_num + 100:06d}",
                    "is_bot": True
                }
                await memory_service.store_raw_message(conversation_key, bot_data)
            
            # Analyze response quality
            quality_metrics = analyze_response_quality(user_message, response_text, turn_num)
            
            results.append({
                "turn": turn_num,
                "user_message": user_message,
                "agent_response": response_text,
                "response_time": round(response_time, 3),
                "quality_score": quality_metrics["overall_score"],
                "quality_details": quality_metrics
            })
            
            print(f"Quality Score: {quality_metrics['overall_score']}/100\n")
            
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            results.append({
                "turn": turn_num,
                "user_message": user_message,
                "error": str(e)
            })
    
    # Generate summary
    successful_turns = [r for r in results if 'error' not in r]
    
    if successful_turns:
        avg_time = sum(r["response_time"] for r in successful_turns) / len(successful_turns)
        avg_quality = sum(r["quality_score"] for r in successful_turns) / len(successful_turns)
        
        print("="*60)
        print("CONVERSATION SUMMARY")
        print("="*60)
        print(f"Turns Completed: {len(successful_turns)}/3")
        print(f"Average Response Time: {avg_time:.3f}s")
        print(f"Average Quality Score: {avg_quality:.1f}/100")
        
        # Check specific prompt elements
        mentions_autopilot = sum(1 for r in successful_turns if "autopilot" in r["agent_response"].lower())
        mentions_construct = sum(1 for r in successful_turns if "construct" in r["agent_response"].lower())
        shows_personality = sum(1 for r in successful_turns if any(word in r["agent_response"].lower() 
                                for word in ["design", "nerd", "quality", "experience"]))
        
        print(f"Autopilot Mentions: {mentions_autopilot}/{len(successful_turns)}")
        print(f"Construct Mentions: {mentions_construct}/{len(successful_turns)}")
        print(f"Personality Indicators: {shows_personality}/{len(successful_turns)}")
        
        if avg_quality >= 80 and avg_time <= 5:
            assessment = "🟢 EXCELLENT - New prompts are highly effective!"
        elif avg_quality >= 70 and avg_time <= 8:
            assessment = "🟡 GOOD - New prompts work well"
        elif avg_quality >= 60:
            assessment = "🟠 FAIR - New prompts need refinement"  
        else:
            assessment = "🔴 POOR - New prompts need major revision"
            
        print(f"\nASSESSMENT: {assessment}")
    
    # Save results
    with open('quick_conversation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: quick_conversation_results.json")
    
    return results


def analyze_response_quality(user_msg: str, response: str, turn: int) -> Dict[str, Any]:
    """Analyze response quality for prompt effectiveness"""
    metrics = {
        "has_response": bool(response),
        "response_length": len(response),
        "word_count": len(response.split()) if response else 0,
        "uses_markdown": any(marker in response for marker in ["*", "`", "_", "-"]),
        "mentions_autopilot": "autopilot" in response.lower(),
        "mentions_construct": "construct" in response.lower(),
        "persona_indicators": sum(1 for word in ["design", "experience", "quality", "nerd", "art"] 
                                if word in response.lower()),
        "creative_elements": sum(1 for phrase in ["interesting", "actually", "fun fact", "by the way"] 
                               if phrase in response.lower()),
        "addresses_query": check_query_relevance(user_msg, response)
    }
    
    # Calculate quality score
    quality_score = 0
    quality_score += 25 if metrics["has_response"] else 0
    quality_score += 15 if metrics["word_count"] > 30 else 0
    quality_score += 10 if metrics["uses_markdown"] else 0
    quality_score += 15 if metrics["addresses_query"] else 0
    quality_score += 10 if metrics["persona_indicators"] > 0 else 0
    quality_score += 10 if metrics["mentions_autopilot"] else 0
    quality_score += 10 if metrics["creative_elements"] > 0 else 0
    quality_score += 5 if metrics["mentions_construct"] else 0
    
    metrics["overall_score"] = quality_score
    return metrics


def check_query_relevance(user_msg: str, response: str) -> bool:
    """Check if response addresses the user's query"""
    user_words = set(user_msg.lower().split())
    response_words = set(response.lower().split())
    
    # Remove common words
    common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "how", "are", "you"}
    user_words -= common_words
    response_words -= common_words
    
    if not user_words:
        return True
    
    overlap = len(user_words.intersection(response_words))
    return overlap / len(user_words) > 0.15  # At least 15% word overlap


if __name__ == "__main__":
    asyncio.run(test_conversation_flow())