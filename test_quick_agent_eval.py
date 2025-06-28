#!/usr/bin/env python3
"""
Quick Agent Evaluation - Fast test of new prompts

Tests:
1. Simple greeting
2. Joke response  
3. Short conversation (3 messages)

Focused on response time and quality assessment.
"""

import asyncio
import json
import time
from typing import Dict, Any
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService


class QuickAgentEval:
    """Quick evaluation of agent performance with new prompts"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.orchestrator = OrchestratorAgent(self.memory_service)
        self.client_agent = ClientAgent()
        
    def create_test_message(self, text: str, message_ts: str = None) -> ProcessedMessage:
        """Create a test message"""
        if message_ts is None:
            message_ts = f"{int(time.time())}.{int(time.time() * 1000000) % 1000000:06d}"
            
        return ProcessedMessage(
            text=text,
            user_id="U_TEST_USER",
            user_name="TestUser",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=message_ts,
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
    
    async def test_single_message(self, text: str, test_name: str) -> Dict[str, Any]:
        """Test a single message and return metrics"""
        print(f"\n--- {test_name} ---")
        print(f"Input: {text}")
        
        message = self.create_test_message(text)
        start_time = time.time()
        
        try:
            response = await self.orchestrator.process_query(message)
            response_time = time.time() - start_time
            
            # Analyze response quality
            response_text = response.get("text", "")
            suggestions = response.get("suggestions", [])
            
            quality_metrics = {
                "has_response": bool(response_text),
                "response_length": len(response_text),
                "response_word_count": len(response_text.split()),
                "has_suggestions": len(suggestions) > 0,
                "suggestion_count": len(suggestions),
                "uses_markdown": any(marker in response_text for marker in ["*", "`", "_", "-"]),
                "mentions_autopilot": "autopilot" in response_text.lower(),
                "persona_indicators": sum(1 for word in ["design", "experience", "quality", "nerd", "construct"] 
                                        if word in response_text.lower()),
                "creative_elements": sum(1 for phrase in ["interesting", "actually", "fun fact", "by the way"] 
                                       if phrase in response_text.lower())
            }
            
            # Calculate quality score
            quality_score = 0
            quality_score += 20 if quality_metrics["has_response"] else 0
            quality_score += 15 if quality_metrics["response_word_count"] > 20 else 0
            quality_score += 10 if quality_metrics["uses_markdown"] else 0
            quality_score += 15 if quality_metrics["mentions_autopilot"] else 0
            quality_score += 10 if quality_metrics["has_suggestions"] else 0
            quality_score += min(quality_metrics["persona_indicators"] * 5, 15)
            quality_score += min(quality_metrics["creative_elements"] * 5, 15)
            
            quality_metrics["overall_score"] = quality_score
            
            print(f"Response Time: {response_time:.2f}s")
            print(f"Response: {response_text[:150]}{'...' if len(response_text) > 150 else ''}")
            print(f"Suggestions: {len(suggestions)} provided")
            print(f"Quality Score: {quality_score}/100")
            
            return {
                "test_name": test_name,
                "input": text,
                "response_time": round(response_time, 3),
                "response": response_text,
                "suggestions": suggestions,
                "quality_metrics": quality_metrics,
                "success": True
            }
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            return {
                "test_name": test_name,
                "input": text,
                "error": str(e),
                "success": False
            }
    
    async def run_quick_evaluation(self) -> Dict[str, Any]:
        """Run quick evaluation of key scenarios"""
        print("=== QUICK AGENT EVALUATION ===")
        print("Testing new prompts with key scenarios...")
        
        start_time = time.time()
        
        # Test scenarios
        tests = [
            ("Hey buddy", "Simple Greeting"),
            ("Why don't robots ever panic? Because they have great automation!", "Joke Response"),
            ("What's the latest on Autopilot design patterns?", "Autopilot Query"),
            ("I'm struggling with UX for AI interactions", "Design Problem"),
            ("Thanks for the help! Any final thoughts?", "Conversation Ending")
        ]
        
        results = []
        total_response_time = 0
        successful_tests = 0
        quality_scores = []
        
        for text, test_name in tests:
            result = await self.test_single_message(text, test_name)
            results.append(result)
            
            if result.get("success"):
                total_response_time += result["response_time"]
                successful_tests += 1
                quality_scores.append(result["quality_metrics"]["overall_score"])
        
        total_time = time.time() - start_time
        
        # Calculate summary metrics
        avg_response_time = total_response_time / successful_tests if successful_tests > 0 else 0
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": round(total_time, 2),
            "tests_run": len(tests),
            "successful_tests": successful_tests,
            "success_rate": round(successful_tests / len(tests) * 100, 1),
            "average_response_time": round(avg_response_time, 3),
            "average_quality_score": round(avg_quality_score, 1),
            "quality_distribution": {
                "excellent": sum(1 for score in quality_scores if score >= 80),
                "good": sum(1 for score in quality_scores if 60 <= score < 80),
                "needs_improvement": sum(1 for score in quality_scores if score < 60)
            }
        }
        
        # Print summary
        print(f"\n=== EVALUATION SUMMARY ===")
        print(f"Tests Completed: {successful_tests}/{len(tests)} ({summary['success_rate']}%)")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"Average Quality Score: {avg_quality_score:.1f}/100")
        print(f"Quality Distribution:")
        print(f"  Excellent (80+): {summary['quality_distribution']['excellent']}")
        print(f"  Good (60-79): {summary['quality_distribution']['good']}")
        print(f"  Needs Work (<60): {summary['quality_distribution']['needs_improvement']}")
        print(f"Total Evaluation Time: {total_time:.2f}s")
        
        # Assessment
        if avg_quality_score >= 80 and avg_response_time <= 3:
            assessment = "EXCELLENT - Prompts are working very well"
        elif avg_quality_score >= 70 and avg_response_time <= 5:
            assessment = "GOOD - Prompts are effective with minor room for improvement"
        elif avg_quality_score >= 60:
            assessment = "FAIR - Prompts need some refinement"
        else:
            assessment = "NEEDS WORK - Prompts require significant improvement"
        
        print(f"\nOVERALL ASSESSMENT: {assessment}")
        
        return {
            "summary": summary,
            "assessment": assessment,
            "detailed_results": results
        }


async def main():
    """Run the quick evaluation"""
    evaluator = QuickAgentEval()
    results = await evaluator.run_quick_evaluation()
    
    # Save results
    with open('quick_agent_eval_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: quick_agent_eval_results.json")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())