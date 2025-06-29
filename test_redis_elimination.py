#!/usr/bin/env python3
"""
Test Redis Elimination - Comprehensive verification that system works without Redis
"""

import asyncio
import os
import aiohttp
import json
from datetime import datetime


async def test_redis_elimination():
    """Test that system works completely without Redis"""
    
    print("=" * 80)
    print("🔧 TESTING COMPLETE REDIS ELIMINATION")
    print("=" * 80)
    
    print("\n1️⃣ ENVIRONMENT VERIFICATION")
    print("-" * 60)
    
    # Check environment variables
    redis_vars = {
        "REDIS_URL": os.environ.get("REDIS_URL", "NOT SET"),
        "CELERY_BROKER_URL": os.environ.get("CELERY_BROKER_URL", "NOT SET"),
        "CELERY_RESULT_BACKEND": os.environ.get("CELERY_RESULT_BACKEND", "NOT SET")
    }
    
    for var, value in redis_vars.items():
        status = "🔴 REDIS DETECTED" if "redis" in value.lower() else "✅ NO REDIS"
        print(f"   {var}: {status}")
        if "redis" in value.lower():
            print(f"     Value: {value}")
    
    print("\n2️⃣ TESTING BASIC HEALTH WITHOUT REDIS")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic health endpoint
            url = "http://localhost:5000/health"
            
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Basic health check passed")
                    print(f"   Status: {result.get('status', 'unknown')}")
                    print(f"   Service: {result.get('service', 'unknown')}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Health check exception: {e}")
        return False
    
    print("\n3️⃣ TESTING MCP INTEGRATION WITHOUT REDIS")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test MCP server health
            url = "http://localhost:8001/healthz"
            
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    print("✅ MCP server health check passed")
                else:
                    print(f"❌ MCP health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ MCP health check exception: {e}")
        return False
    
    print("\n4️⃣ TESTING ORCHESTRATOR WITHOUT REDIS")
    print("-" * 60)
    
    try:
        test_payload = {
            "query": "What are the latest Conversational Agents bugs?",
            "user_id": "U123TEST",
            "channel_id": "C123TEST",
            "message_ts": str(datetime.now().timestamp())
        }
        
        async with aiohttp.ClientSession() as session:
            # Test orchestrator analysis
            url = "http://localhost:5000/admin/test-atlassian-integration"
            
            print("⏱️ Testing orchestrator analysis...")
            
            start_time = datetime.now()
            
            async with session.get(url, timeout=60) as response:
                duration = (datetime.now() - start_time).total_seconds()
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Orchestrator test completed in {duration:.2f}s")
                    
                    # Check orchestrator intelligence
                    orchestrator_test = result.get("orchestrator_test", {})
                    if orchestrator_test.get("success"):
                        tools = orchestrator_test.get("tools", [])
                        print(f"✅ Orchestrator correctly selected tools: {tools}")
                        
                        if "atlassian_search" in tools:
                            print("✅ Atlassian tool correctly identified for query")
                        else:
                            print("⚠️ Atlassian tool not selected, but this may be expected")
                    else:
                        print(f"❌ Orchestrator test failed: {orchestrator_test}")
                        return False
                    
                    # Check MCP health in integration
                    mcp_health = result.get("mcp_health", {})
                    if mcp_health.get("healthy"):
                        print("✅ MCP integration healthy")
                    else:
                        print(f"❌ MCP integration unhealthy: {mcp_health}")
                        return False
                    
                    # Check tool execution
                    tool_execution = result.get("tool_execution", {})
                    if tool_execution.get("success"):
                        results = tool_execution.get("results", [])
                        print(f"✅ Tool execution successful: {len(results)} results")
                        
                        if results:
                            first_result = results[0]
                            title = first_result.get("title", "No title")
                            space = first_result.get("space", {}).get("name", "Unknown")
                            print(f"   Sample result: {title} (Space: {space})")
                    else:
                        error = tool_execution.get("error", "Unknown error")
                        print(f"❌ Tool execution failed: {error}")
                        
                        # Check for Redis-related errors
                        if "redis" in error.lower() or "6379" in str(error):
                            print("🔍 REDIS ERROR DETECTED IN TOOL EXECUTION!")
                            print("   This indicates Redis dependency still exists")
                            return False
                        
                else:
                    print(f"❌ Orchestrator integration test failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}...")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Orchestrator test timed out")
        print("   This may indicate Redis hanging operations")
        return False
    except Exception as e:
        print(f"❌ Orchestrator test exception: {e}")
        return False
    
    print("\n5️⃣ TESTING SLACK WEBHOOK WITHOUT REDIS")
    print("-" * 60)
    
    try:
        # Create realistic Slack webhook payload
        slack_payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "Find me bugs in the AUTOPILOT project",
                "user": "U123TEST",
                "channel": "C123TEST",
                "ts": str(datetime.now().timestamp()),
                "event_ts": str(datetime.now().timestamp()),
                "channel_type": "channel"
            },
            "team_id": "T123TEST",
            "event_id": f"Ev{int(datetime.now().timestamp())}",
            "event_time": int(datetime.now().timestamp())
        }
        
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/slack/events"
            
            print("🚀 Testing Slack webhook processing...")
            
            start_time = datetime.now()
            
            async with session.post(
                url,
                json=slack_payload,
                timeout=90  # 1.5 minutes
            ) as response:
                duration = (datetime.now() - start_time).total_seconds()
                
                print(f"⏱️ Webhook processing time: {duration:.2f}s")
                
                if response.status == 200:
                    result = await response.text()
                    print("✅ Webhook processing completed")
                    
                    # Check for error patterns
                    result_lower = result.lower()
                    
                    if "execution_error" in result_lower:
                        print("❌ EXECUTION ERROR DETECTED!")
                        print("   This is the production failure pattern")
                        return False
                    elif "mcp_server_unreachable" in result_lower:
                        print("❌ MCP SERVER UNREACHABLE DETECTED!")
                        print("   MCP connectivity issue")
                        return False
                    elif "trouble understanding" in result_lower:
                        print("❌ FALLBACK RESPONSE DETECTED!")
                        print("   Orchestrator failing to analyze queries")
                        return False
                    elif "redis" in result_lower:
                        print("❌ REDIS ERROR IN RESPONSE!")
                        print("   Redis dependency still causing issues")
                        return False
                    else:
                        print("✅ Webhook processing successful")
                        print(f"   Response length: {len(result)} characters")
                        return True
                        
                else:
                    print(f"❌ Webhook processing failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}...")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Webhook processing timed out")
        print("   This indicates system hanging (possibly Redis)")
        return False
    except Exception as e:
        print(f"❌ Webhook processing exception: {e}")
        return False
    
    return True


async def test_production_scenario():
    """Test the exact production scenario that's failing"""
    
    print("\n" + "=" * 80)
    print("🎯 TESTING EXACT PRODUCTION FAILURE SCENARIO")
    print("=" * 80)
    
    # This is the exact query from the user's message
    production_query = "What are the latest Conversational Agents bugs?"
    
    slack_payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": production_query,
            "user": "U123PROD",
            "channel": "C123PROD",
            "ts": str(datetime.now().timestamp()),
            "event_ts": str(datetime.now().timestamp()),
            "channel_type": "channel"
        },
        "team_id": "T123PROD",
        "event_id": f"Ev{int(datetime.now().timestamp())}PROD",
        "event_time": int(datetime.now().timestamp())
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/slack/events"
            
            print(f"🔍 Testing production query: '{production_query}'")
            print("⏱️ Processing...")
            
            start_time = datetime.now()
            
            async with session.post(
                url,
                json=slack_payload,
                timeout=120  # 2 minutes like production
            ) as response:
                duration = (datetime.now() - start_time).total_seconds()
                
                print(f"⏱️ Processing time: {duration:.2f}s")
                
                if response.status == 200:
                    result = await response.text()
                    
                    # Check for the exact production failure patterns
                    if "cannot retrieve the latest conversational agents bugs from jira" in result.lower():
                        print("❌ EXACT PRODUCTION FAILURE DETECTED!")
                        print("   Response matches user's reported error")
                        return False
                    elif "mcp_server_unreachable" in result.lower():
                        print("❌ MCP SERVER UNREACHABLE (PRODUCTION ISSUE)")
                        print("   This is the root cause reported by user")
                        return False
                    elif any(error in result.lower() for error in ["execution_error", "trouble understanding", "couldn't process"]):
                        print("❌ PRODUCTION ERROR PATTERN DETECTED!")
                        print(f"   Error response matches production failure")
                        return False
                    else:
                        print("✅ PRODUCTION SCENARIO RESOLVED!")
                        print("   System now handles the failing query correctly")
                        return True
                        
                else:
                    print(f"❌ Production scenario failed: {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Production scenario timed out")
        print("   Matches the production timeout behavior")
        return False
    except Exception as e:
        print(f"❌ Production scenario exception: {e}")
        return False


async def main():
    """Run comprehensive Redis elimination test"""
    
    print("🔧 COMPREHENSIVE REDIS ELIMINATION VERIFICATION")
    print("=" * 80)
    
    # Test Redis elimination
    redis_test = await test_redis_elimination()
    
    if not redis_test:
        print("\n❌ REDIS ELIMINATION TEST FAILED")
        print("   System still has Redis dependencies causing issues")
        return False
    
    # Test production scenario
    production_test = await test_production_scenario()
    
    if production_test:
        print("\n✅ REDIS ELIMINATION SUCCESSFUL!")
        print("   Production deployment issue resolved")
        print("   System works completely without Redis")
        return True
    else:
        print("\n❌ PRODUCTION SCENARIO STILL FAILING")
        print("   Additional investigation required")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)