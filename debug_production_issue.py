#!/usr/bin/env python3
"""
Debug Production Issue - "I'm having trouble understanding" fallback

This script tests the exact scenario causing production failures
to identify where the orchestrator is failing and returning None.
"""

import asyncio
import json
import traceback
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from utils.prompt_loader import get_orchestrator_prompt


async def debug_orchestrator_failure():
    """Debug the specific failure causing fallback responses in production"""
    print("DEBUGGING PRODUCTION ISSUE: 'I'm having trouble understanding' fallback")
    print("="*70)
    
    # Test with the exact query mentioned in production
    test_query = "i wanna know about Autopilot a little bit more"
    
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Create test message
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
    
    print(f"Testing Query: '{test_query}'")
    print("-" * 70)
    
    # Step 1: Test prompt loading
    print("Step 1: Testing Prompt Loading...")
    try:
        system_prompt = get_orchestrator_prompt()
        print(f"✅ Prompt loaded successfully: {len(system_prompt)} characters")
        print(f"Prompt preview: {system_prompt[:200]}...")
    except Exception as e:
        print(f"❌ Prompt loading failed: {e}")
        return
    
    # Step 2: Test query analysis directly
    print("\nStep 2: Testing Query Analysis...")
    try:
        execution_plan = await orchestrator._analyze_query_and_plan(message)
        
        if execution_plan:
            print("✅ Query analysis successful!")
            print(f"Execution Plan: {json.dumps(execution_plan, indent=2)}")
        else:
            print("❌ Query analysis returned None - THIS IS THE PROBLEM!")
            print("Investigating why...")
            
            # Let's test the Gemini API call manually
            await debug_gemini_api_call(orchestrator, message)
            
    except Exception as e:
        print(f"❌ Query analysis failed with exception: {e}")
        traceback.print_exc()
    
    # Step 3: Test full process
    print("\nStep 3: Testing Full Process...")
    try:
        response = await orchestrator.process_query(message)
        
        response_text = response.get("text", "")
        print(f"Final Response: {response_text}")
        
        if "having trouble understanding" in response_text.lower():
            print("❌ CONFIRMED: Production issue reproduced - hitting fallback response")
        else:
            print("✅ SUCCESS: Query processed normally")
            
    except Exception as e:
        print(f"❌ Full process failed: {e}")
        traceback.print_exc()


async def debug_gemini_api_call(orchestrator, message):
    """Debug the Gemini API call specifically"""
    print("\n--- GEMINI API DEBUG ---")
    
    try:
        # Get conversation context
        conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
        recent_messages = await orchestrator.memory_service.get_recent_messages(conversation_key, limit=10)
        conversation_history = await orchestrator.memory_service.get_conversation_context(conversation_key)
        
        context = {
            "query": message.text,
            "user": message.user_name,
            "channel": message.channel_name,
            "is_dm": message.is_dm,
            "thread_context": message.thread_context,
            "recent_messages": recent_messages,
            "conversation_history": conversation_history
        }
        
        system_prompt = get_orchestrator_prompt()
        user_prompt = f"""
Context: {json.dumps(context, indent=2)}

Create an execution plan to answer this query effectively.

Current Query: "{message.text}"
"""
        
        print(f"System Prompt Length: {len(system_prompt)}")
        print(f"User Prompt Length: {len(user_prompt)}")
        print(f"User Prompt Preview: {user_prompt[:300]}...")
        
        # Test Gemini API call
        print("\nCalling Gemini API...")
        
        response = await orchestrator.gemini_client.generate_structured_response(
            system_prompt,
            user_prompt,
            response_format="json",
            model=orchestrator.gemini_client.pro_model
        )
        
        print(f"Gemini Response: {response}")
        
        if response:
            try:
                plan = json.loads(response)
                print("✅ JSON parsing successful!")
                print(f"Parsed Plan: {json.dumps(plan, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Raw response: {response}")
        else:
            print("❌ Gemini returned empty/None response")
            
    except Exception as e:
        print(f"❌ Gemini API call failed: {e}")
        traceback.print_exc()


async def test_various_queries():
    """Test various query types to see which ones fail"""
    print("\n" + "="*70)
    print("TESTING VARIOUS QUERY TYPES")
    print("="*70)
    
    test_queries = [
        "i wanna know about Autopilot a little bit more",
        "What is Autopilot?",
        "Tell me about Autopilot design patterns",
        "How do I use Autopilot?",
        "Hey buddy",
        "Can you help me with automation?"
    ]
    
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{query}'")
        print("-" * 40)
        
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
            plan = await orchestrator._analyze_query_and_plan(message)
            if plan:
                print(f"✅ SUCCESS: {plan.get('analysis', 'No analysis')[:100]}...")
            else:
                print("❌ FAILED: Returned None")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(debug_orchestrator_failure())
    asyncio.run(test_various_queries())