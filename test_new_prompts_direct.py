#!/usr/bin/env python3
"""
Direct Prompt Testing - Test new prompts without full API pipeline

This tests the prompt effectiveness by directly calling the agents
and measuring their responses to key scenarios.
"""

import asyncio
import time
import json
from typing import Dict, Any

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService


async def test_orchestrator_analysis_only():
    """Test just the orchestrator's query analysis capability"""
    print("=== TESTING ORCHESTRATOR PROMPT EFFECTIVENESS ===\n")
    
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    test_queries = [
        "Hey buddy",
        "Why don't robots ever panic? Because they have great automation!",
        "What are the latest Autopilot design patterns?",
        "I'm struggling with UX for AI interactions",
        "How do you handle error states in Autopilot designs?"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}: {query}")
        print("-" * 50)
        
        # Create test message
        message = ProcessedMessage(
            text=query,
            user_id="U_TEST",
            user_name="TestUser",
            channel_id="C_TEST",
            channel_name="test",
            message_ts=f"{int(time.time())}.000001",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        start_time = time.time()
        
        try:
            # Test orchestrator analysis
            plan = await orchestrator._analyze_query_and_plan(message)
            analysis_time = time.time() - start_time
            
            print(f"Analysis Time: {analysis_time:.2f}s")
            print(f"Analysis: {plan.get('analysis', 'No analysis')}")
            print(f"Intent: {plan.get('context', {}).get('intent', 'No intent')}")
            print(f"Tools Needed: {plan.get('tools_needed', [])}")
            print(f"Response Approach: {plan.get('context', {}).get('response_approach', 'No approach')}")
            print(f"Tone Guidance: {plan.get('context', {}).get('tone_guidance', 'No tone')}")
            
            # Evaluate plan quality
            quality_score = 0
            quality_score += 20 if plan.get('analysis') else 0
            quality_score += 20 if plan.get('context', {}).get('intent') else 0
            quality_score += 20 if plan.get('context', {}).get('response_approach') else 0
            quality_score += 20 if plan.get('context', {}).get('tone_guidance') else 0
            quality_score += 20 if plan.get('tools_needed') is not None else 0
            
            print(f"Plan Quality Score: {quality_score}/100")
            
            results.append({
                "query": query,
                "analysis_time": round(analysis_time, 3),
                "plan": plan,
                "quality_score": quality_score
            })
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append({
                "query": query,
                "error": str(e),
                "quality_score": 0
            })
        
        print("\n")
    
    # Summary
    successful_tests = [r for r in results if 'error' not in r]
    avg_time = sum(r['analysis_time'] for r in successful_tests) / len(successful_tests) if successful_tests else 0
    avg_quality = sum(r['quality_score'] for r in results) / len(results) if results else 0
    
    print("=== ORCHESTRATOR PROMPT EVALUATION SUMMARY ===")
    print(f"Tests Completed: {len(successful_tests)}/{len(results)}")
    print(f"Average Analysis Time: {avg_time:.3f}s")
    print(f"Average Quality Score: {avg_quality:.1f}/100")
    
    if avg_quality >= 80:
        assessment = "EXCELLENT - Orchestrator prompts are highly effective"
    elif avg_quality >= 70:
        assessment = "GOOD - Orchestrator prompts work well"
    elif avg_quality >= 60:
        assessment = "FAIR - Orchestrator prompts need refinement"
    else:
        assessment = "POOR - Orchestrator prompts need major revision"
    
    print(f"Assessment: {assessment}")
    
    return {
        "orchestrator_results": results,
        "summary": {
            "avg_time": avg_time,
            "avg_quality": avg_quality,
            "assessment": assessment
        }
    }


async def test_client_agent_responses():
    """Test client agent response generation with mock gathered info"""
    print("\n=== TESTING CLIENT AGENT PROMPT EFFECTIVENESS ===\n")
    
    client_agent = ClientAgent()
    
    test_scenarios = [
        {
            "query": "Hey buddy",
            "gathered_info": {"vector_results": [], "graph_results": []},
            "context": {"intent": "social_greeting", "response_approach": "friendly_and_helpful", "tone_guidance": "warm"}
        },
        {
            "query": "What are the latest Autopilot design patterns?",
            "gathered_info": {"vector_results": ["Design patterns document chunk"], "graph_results": []},
            "context": {"intent": "information_request", "response_approach": "expert_knowledge", "tone_guidance": "professional"}
        },
        {
            "query": "I'm struggling with UX for AI interactions",
            "gathered_info": {"vector_results": [], "graph_results": []},
            "context": {"intent": "help_request", "response_approach": "supportive_guidance", "tone_guidance": "helpful"}
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"Test {i}: {scenario['query']}")
        print("-" * 50)
        
        # Create test message
        message = ProcessedMessage(
            text=scenario['query'],
            user_id="U_TEST",
            user_name="TestUser",
            channel_id="C_TEST",
            channel_name="test",
            message_ts=f"{int(time.time())}.000001",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        start_time = time.time()
        
        try:
            # Test client agent response
            response = await client_agent.generate_response(
                message, 
                scenario['gathered_info'], 
                scenario['context']
            )
            response_time = time.time() - start_time
            
            response_text = response.get('text', '') if response else ''
            suggestions = response.get('suggestions', []) if response else []
            
            print(f"Response Time: {response_time:.2f}s")
            print(f"Response Length: {len(response_text)} characters")
            print(f"Response: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
            print(f"Suggestions: {len(suggestions)} provided")
            
            # Evaluate response quality
            quality_score = 0
            quality_score += 25 if response_text else 0
            quality_score += 15 if len(response_text) > 100 else 0
            quality_score += 15 if any(marker in response_text for marker in ["*", "`", "_", "-"]) else 0
            quality_score += 15 if "autopilot" in response_text.lower() else 0
            quality_score += 10 if suggestions else 0
            quality_score += 20 if any(word in response_text.lower() for word in ["design", "experience", "quality"]) else 0
            
            print(f"Response Quality Score: {quality_score}/100")
            
            results.append({
                "query": scenario['query'],
                "response_time": round(response_time, 3),
                "response": response,
                "quality_score": quality_score
            })
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append({
                "query": scenario['query'],
                "error": str(e),
                "quality_score": 0
            })
        
        print("\n")
    
    # Summary
    successful_tests = [r for r in results if 'error' not in r]
    avg_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests) if successful_tests else 0
    avg_quality = sum(r['quality_score'] for r in results) / len(results) if results else 0
    
    print("=== CLIENT AGENT PROMPT EVALUATION SUMMARY ===")
    print(f"Tests Completed: {len(successful_tests)}/{len(results)}")
    print(f"Average Response Time: {avg_time:.3f}s")
    print(f"Average Quality Score: {avg_quality:.1f}/100")
    
    if avg_quality >= 80:
        assessment = "EXCELLENT - Client agent prompts are highly effective"
    elif avg_quality >= 70:
        assessment = "GOOD - Client agent prompts work well"
    elif avg_quality >= 60:
        assessment = "FAIR - Client agent prompts need refinement"
    else:
        assessment = "POOR - Client agent prompts need major revision"
    
    print(f"Assessment: {assessment}")
    
    return {
        "client_results": results,
        "summary": {
            "avg_time": avg_time,
            "avg_quality": avg_quality,
            "assessment": assessment
        }
    }


async def main():
    """Run direct prompt testing"""
    print("DIRECT PROMPT EFFECTIVENESS TEST")
    print("="*50)
    print("Testing new prompts from prompts.yaml")
    print("This tests prompts directly without full API pipeline\n")
    
    start_time = time.time()
    
    # Test orchestrator
    orchestrator_results = await test_orchestrator_analysis_only()
    
    # Test client agent  
    client_results = await test_client_agent_responses()
    
    total_time = time.time() - start_time
    
    # Overall assessment
    overall_score = (
        orchestrator_results['summary']['avg_quality'] + 
        client_results['summary']['avg_quality']
    ) / 2
    
    print("\n" + "="*60)
    print("OVERALL PROMPT ASSESSMENT")
    print("="*60)
    print(f"Total Test Duration: {total_time:.2f}s")
    print(f"Orchestrator Quality: {orchestrator_results['summary']['avg_quality']:.1f}/100")
    print(f"Client Agent Quality: {client_results['summary']['avg_quality']:.1f}/100")
    print(f"Overall Quality Score: {overall_score:.1f}/100")
    
    if overall_score >= 80:
        final_assessment = "🟢 EXCELLENT - New prompts are highly effective!"
    elif overall_score >= 70:
        final_assessment = "🟡 GOOD - New prompts work well with minor improvements possible"
    elif overall_score >= 60:
        final_assessment = "🟠 FAIR - New prompts need some refinement"
    else:
        final_assessment = "🔴 POOR - New prompts need significant revision"
    
    print(f"\nFINAL ASSESSMENT: {final_assessment}")
    
    # Save detailed results
    full_results = {
        "timestamp": time.time(),
        "total_duration": total_time,
        "overall_score": overall_score,
        "final_assessment": final_assessment,
        "orchestrator": orchestrator_results,
        "client_agent": client_results
    }
    
    with open('prompt_test_results.json', 'w') as f:
        json.dump(full_results, f, indent=2)
    
    print(f"\n✅ Detailed results saved to: prompt_test_results.json")
    
    return full_results


if __name__ == "__main__":
    asyncio.run(main())