#!/usr/bin/env python3
"""
Debug Production Issue - "I'm having trouble understanding" fallback

This script tests the exact scenario causing production failures
to identify where the orchestrator is failing and returning None.
"""

import asyncio
import os
import sys
import aiohttp
import json
from datetime import datetime


async def debug_orchestrator_failure():
    """Debug the specific failure causing fallback responses in production"""
    
    print("=" * 80)
    print("🔍 DEBUGGING PRODUCTION ORCHESTRATOR FAILURE")
    print("=" * 80)
    
    # Test the exact failure pattern
    test_queries = [
        "Can you find information about UiPath Autopilot features?",
        "What are the latest Conversational Agents bugs?", 
        "Show me open tickets in the AUTOPILOT project",
        "Create a new bug report for login issues"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}️⃣ TESTING QUERY: {query}")
        print("-" * 60)
        
        try:
            # Test the orchestrator analysis endpoint directly
            async with aiohttp.ClientSession() as session:
                test_payload = {
                    "query": query,
                    "user_id": "U123TEST", 
                    "channel_id": "C123TEST",
                    "message_ts": "1234567890.123456"
                }
                
                print(f"⏱️ Testing orchestrator analysis...")
                
                url = "http://localhost:5000/admin/test-orchestrator-analysis"
                
                start_time = datetime.now()
                
                async with session.post(
                    url, 
                    json=test_payload,
                    timeout=120  # 2 minutes
                ) as response:
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Analysis completed in {duration:.2f}s")
                        
                        # Check for orchestrator success
                        if result.get("success"):
                            analysis = result.get("analysis", {})
                            print(f"✅ Orchestrator analysis: {analysis.get('intent', 'Unknown')}")
                            
                            # Check tools used
                            tools_used = analysis.get("tools_used", [])
                            if tools_used:
                                print(f"✅ Tools selected: {', '.join(tools_used)}")
                            else:
                                print("⚠️ No tools selected")
                            
                            # Check execution plan
                            if "execution_plan" in analysis:
                                plan = analysis["execution_plan"]
                                if plan.get("atlassian_actions"):
                                    print(f"✅ Atlassian actions: {len(plan['atlassian_actions'])}")
                                    for action in plan["atlassian_actions"]:
                                        print(f"   - {action.get('mcp_tool', 'Unknown')}: {action.get('arguments', {})}")
                                else:
                                    print("⚠️ No Atlassian actions in plan")
                        else:
                            error = result.get("error", "Unknown error")
                            print(f"❌ Orchestrator failed: {error}")
                            
                            # Check for specific error types
                            if "Redis" in str(error) or "6379" in str(error):
                                print("🔍 REDIS CONNECTION ERROR DETECTED!")
                                print("   This is likely the root cause of production failures")
                            elif "MCP" in str(error):
                                print("🔍 MCP CONNECTION ERROR DETECTED!")
                                print("   MCP server may be unreachable")
                            elif "timeout" in str(error).lower():
                                print("🔍 TIMEOUT ERROR DETECTED!")
                                print("   Operation took too long to complete")
                    else:
                        print(f"❌ Request failed with status: {response.status}")
                        error_text = await response.text()
                        print(f"   Error: {error_text[:300]}...")
                        
        except asyncio.TimeoutError:
            print("❌ Request timed out after 2 minutes")
            print("   This indicates a hanging operation")
        except Exception as e:
            print(f"❌ Exception during test: {e}")
            import traceback
            traceback.print_exc()


async def debug_gemini_api_call(orchestrator, message):
    """Debug the Gemini API call specifically"""
    
    print("\n🧠 DEBUGGING GEMINI API CALL")
    print("-" * 50)
    
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from services.trace_manager import TraceManager
        from services.memory_service import MemoryService
        from models.schemas import ProcessedMessage
        
        # Create test message
        test_message = ProcessedMessage(
            content=message,
            user_id="U123TEST",
            channel_id="C123TEST", 
            message_ts="1234567890.123456",
            thread_ts=None,
            user_name="Test User",
            channel_name="test-channel",
            is_dm=False,
            is_bot_mentioned=True,
            is_thread_reply=False
        )
        
        # Test direct Gemini call
        print("⏱️ Testing direct Gemini API call...")
        
        result = await orchestrator._analyze_query_with_gemini(test_message, [])
        
        if result:
            print("✅ Gemini API call successful")
            print(f"   Intent: {result.get('intent', 'Unknown')}")
            print(f"   Tools: {result.get('tools_used', [])}")
            
            # Check execution plan
            if result.get("execution_plan"):
                plan = result["execution_plan"]
                print(f"   Plan actions: {len(plan.get('atlassian_actions', []))}")
            else:
                print("⚠️ No execution plan generated")
        else:
            print("❌ Gemini API call returned None")
            print("   This is the source of 'I'm having trouble understanding' responses")
            
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_various_queries():
    """Test various query types to see which ones fail"""
    
    print("\n🔬 TESTING QUERY PATTERNS")
    print("-" * 50)
    
    query_types = {
        "Simple greeting": "Hello there",
        "Autopilot question": "What is UiPath Autopilot?",
        "Bug search": "Show me open bugs in AUTOPILOT project", 
        "Jira creation": "Create a task for fixing login issues",
        "Complex technical": "How do I configure Autopilot deployment pipelines?"
    }
    
    for query_type, query in query_types.items():
        print(f"\n📝 {query_type}: '{query}'")
        
        try:
            async with aiohttp.ClientSession() as session:
                test_payload = {
                    "query": query,
                    "user_id": "U123TEST",
                    "channel_id": "C123TEST", 
                    "message_ts": "1234567890.123456"
                }
                
                url = "http://localhost:5000/admin/quick-orchestrator-test"
                
                async with session.post(
                    url,
                    json=test_payload, 
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            print(f"   ✅ Success - Intent: {result.get('intent', 'Unknown')}")
                        else:
                            print(f"   ❌ Failed - Error: {result.get('error', 'Unknown')}")
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        
        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(debug_orchestrator_failure())
    print("\n" + "=" * 80)
    print("🎯 PRODUCTION DEBUG COMPLETE")
    print("=" * 80)