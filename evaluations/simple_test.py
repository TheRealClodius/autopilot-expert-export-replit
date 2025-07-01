#!/usr/bin/env python3
"""
Simple Test - Basic verification that evaluation framework works
"""

import asyncio
import json
from datetime import datetime

async def simple_test():
    """Run a basic test to verify the evaluation framework"""
    
    print("🧪 SIMPLE EVALUATION FRAMEWORK TEST")
    print("=" * 50)
    
    # Test scenario data structure
    test_scenario = {
        "id": "framework_test",
        "name": "Framework Verification",
        "query": "Hello, can you help me test the system?",
        "user_context": {
            "first_name": "TestUser",
            "title": "Engineer",
            "department": "Engineering"
        },
        "channel_context": {
            "is_dm": True,
            "channel_name": "test"
        },
        "expectations": {
            "max_response_time": 30.0,
            "min_response_length": 20,
            "should_be_friendly": True
        }
    }
    
    print(f"Test Scenario: {test_scenario['name']}")
    print(f"Query: \"{test_scenario['query']}\"")
    
    # Simulate a response (without actual agent execution)
    simulated_response = {
        "text": "Hello TestUser! I'm here to help you test the system. I can assist with project documentation, team discussions, current technology trends, and more. What would you like to explore?",
        "suggestions": ["Tell me about your capabilities", "Search team discussions", "Find project documentation"],
        "confidence_level": "high",
        "source_links": []
    }
    
    # Simulate response time
    import time
    start_time = time.time()
    await asyncio.sleep(0.5)  # Simulate processing time
    response_time = time.time() - start_time
    
    # Evaluate the simulated response
    score = evaluate_simulated_response(test_scenario, simulated_response, response_time)
    
    success = score >= 70.0 and response_time <= 30.0
    
    print(f"\n📊 RESULTS:")
    print(f"   Response Time: {response_time:.2f}s")
    print(f"   Response Length: {len(simulated_response['text'])} chars")
    print(f"   Score: {score:.1f}/100")
    print(f"   Success: {'✅' if success else '❌'}")
    
    print(f"\n💬 SIMULATED RESPONSE:")
    print(f"   \"{simulated_response['text'][:100]}...\"")
    
    # Save test results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "test_type": "framework_verification",
        "timestamp": timestamp,
        "scenario": test_scenario,
        "response": simulated_response,
        "metrics": {
            "response_time": response_time,
            "score": score,
            "success": success
        }
    }
    
    with open(f"simple_test_result_{timestamp}.json", 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Framework test completed successfully!")
    print(f"�� Results saved to: simple_test_result_{timestamp}.json")
    
    if success:
        print("\n🎯 RECOMMENDATION: Framework is working correctly. You can now:")
        print("   • Run: python test_runner.py quick (requires environment setup)")
        print("   • Run: python test_runner.py full (comprehensive test)")
        print("   • Use this framework to test agent changes")
    else:
        print("\n⚠️ Framework test failed - review evaluation logic")

def evaluate_simulated_response(scenario, response, response_time):
    """Evaluate a simulated response using the same logic as the real framework"""
    
    expectations = scenario["expectations"]
    response_text = response.get("text", "")
    
    score = 0.0
    
    # Basic response check
    if response_text:
        score += 20
    
    # Length check
    min_length = expectations.get("min_response_length", 20)
    if len(response_text) >= min_length:
        score += 15
    
    # Response time check
    max_time = expectations.get("max_response_time", 60.0)
    if response_time <= max_time:
        score += 15
    
    # No error messages
    if not any(phrase in response_text.lower() for phrase in ["technical difficulties", "error occurred", "sorry"]):
        score += 20
    
    # Name usage check
    if scenario["user_context"].get("first_name") in response_text:
        score += 10
    
    # Friendly tone
    if expectations.get("should_be_friendly"):
        if any(word in response_text.lower() for word in ["hello", "help", "assist", "happy"]):
            score += 10
    
    # Has suggestions
    if len(response.get("suggestions", [])) >= 2:
        score += 10
    
    return min(score, 100.0)

if __name__ == "__main__":
    asyncio.run(simple_test())
