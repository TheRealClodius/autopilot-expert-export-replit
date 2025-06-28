#!/usr/bin/env python3
"""
Test Production Fix - Verify the "trouble understanding" issue is resolved

Tests the exact production scenario to confirm the fix works.
"""

import asyncio
import json
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService


async def test_production_scenario():
    """Test the exact production scenario that was failing"""
    print("TESTING PRODUCTION FIX")
    print("="*50)
    
    # The exact query that was causing issues in production
    test_query = "i wanna know about Autopilot a little bit more"
    
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    message = ProcessedMessage(
        text=test_query,
        user_id="U_PROD_USER",
        user_name="ProductionUser",
        channel_id="C_PROD_CHANNEL",
        channel_name="general",
        message_ts="1735000000.000001",
        thread_ts=None,
        is_dm=False,
        thread_context=None
    )
    
    print(f"Testing query: '{test_query}'")
    print("-" * 50)
    
    try:
        response = await orchestrator.process_query(message)
        response_text = response.get("text", "")
        
        print(f"Response: {response_text}")
        
        # Check if we still get the fallback
        if "having trouble understanding" in response_text.lower():
            print("\n❌ ISSUE PERSISTS: Still getting fallback response")
            return False
        elif response_text:
            print("\n✅ SUCCESS: Generated proper response instead of fallback")
            return True
        else:
            print("\n❓ UNCLEAR: Empty response received")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


async def test_multiple_scenarios():
    """Test multiple scenarios to ensure robust fix"""
    test_queries = [
        "i wanna know about Autopilot a little bit more",
        "tell me about autopilot features",
        "what's new in automation",
        "how do I use design patterns",
        "help with workflows"
    ]
    
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{query}'")
        print("-" * 30)
        
        message = ProcessedMessage(
            text=query,
            user_id="U_TEST",
            user_name="TestUser",
            channel_id="C_TEST",
            channel_name="test",
            message_ts=f"1735000000.{i:06d}",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        try:
            response = await orchestrator.process_query(message)
            response_text = response.get("text", "")
            
            is_fallback = "having trouble understanding" in response_text.lower()
            
            result = {
                "query": query,
                "has_response": bool(response_text),
                "is_fallback": is_fallback,
                "response_preview": response_text[:100] + "..." if len(response_text) > 100 else response_text
            }
            
            results.append(result)
            
            if is_fallback:
                print("❌ FALLBACK")
            elif response_text:
                print("✅ SUCCESS")
            else:
                print("❓ EMPTY")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                "query": query,
                "error": str(e)
            })
    
    # Summary
    successful_responses = sum(1 for r in results if r.get("has_response") and not r.get("is_fallback"))
    fallback_responses = sum(1 for r in results if r.get("is_fallback"))
    
    print(f"\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Tests: {len(test_queries)}")
    print(f"Successful Responses: {successful_responses}")
    print(f"Fallback Responses: {fallback_responses}")
    print(f"Success Rate: {successful_responses/len(test_queries)*100:.1f}%")
    
    if fallback_responses == 0:
        print("\n🎉 SUCCESS: No more fallback responses!")
    else:
        print(f"\n⚠️  WARNING: Still {fallback_responses} fallback responses")
    
    return results


if __name__ == "__main__":
    print("Testing production fix for 'trouble understanding' issue...")
    asyncio.run(test_production_scenario())
    print("\n" + "="*60)
    asyncio.run(test_multiple_scenarios())