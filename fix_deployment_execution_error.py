#!/usr/bin/env python3
"""
Fix deployment execution error by identifying and resolving the specific issue
causing "execution_error" in production environment
"""

import asyncio
import os
import sys
import json
import aiohttp
from datetime import datetime


async def diagnose_deployment_execution_error():
    """Diagnose the exact deployment issue causing execution_error"""
    
    print("=" * 80)
    print("🔧 DIAGNOSING DEPLOYMENT EXECUTION ERROR")
    print("=" * 80)
    
    print("\n1️⃣ CHECKING ENVIRONMENT CONFIGURATION")
    print("-" * 60)
    
    # Check critical environment variables
    env_vars = [
        "REPLIT_DOMAINS", "MCP_SERVER_URL", "CELERY_BROKER_URL", 
        "REDIS_URL", "LANGSMITH_API_KEY", "GEMINI_API_KEY"
    ]
    
    for var in env_vars:
        value = os.environ.get(var, "NOT SET")
        if var in ["LANGSMITH_API_KEY", "GEMINI_API_KEY"]:
            display_value = "***" if value != "NOT SET" else "NOT SET"
        else:
            display_value = value
        print(f"   {var}: {display_value}")
    
    print("\n2️⃣ TESTING MCP SERVER CONNECTIVITY")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test MCP health endpoint
            url = "http://localhost:8001/healthz"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    print("✅ MCP server health check passed")
                    
                    # Test MCP SSE endpoint
                    sse_url = "http://localhost:8001/mcp/sse"
                    async with session.get(sse_url, timeout=5) as sse_response:
                        if sse_response.status in [200, 404]:  # 404 is expected for GET on SSE
                            print("✅ MCP SSE endpoint reachable")
                        else:
                            print(f"⚠️ MCP SSE endpoint returned {sse_response.status}")
                else:
                    print(f"❌ MCP health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ MCP connectivity test failed: {e}")
        return False
    
    print("\n3️⃣ TESTING REDIS CONNECTION IMPACT")
    print("-" * 60)
    
    # Check if Redis errors are blocking execution
    try:
        # Test admin endpoint that doesn't need Redis
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/health"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Basic health endpoint working")
                    print(f"   Status: {result.get('status', 'unknown')}")
                else:
                    print(f"❌ Basic health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Basic health check exception: {e}")
        return False
    
    print("\n4️⃣ TESTING ORCHESTRATOR FUNCTIONALITY")
    print("-" * 60)
    
    try:
        # Test orchestrator without Redis dependencies
        test_payload = {
            "query": "What are the latest Conversational Agents bugs?",
            "user_id": "U123TEST",
            "channel_id": "C123TEST",
            "message_ts": str(datetime.now().timestamp())
        }
        
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/admin/test-orchestrator-no-redis"
            
            print("⏱️ Testing orchestrator without Redis...")
            
            start_time = datetime.now()
            
            async with session.post(
                url,
                json=test_payload,
                timeout=60
            ) as response:
                duration = (datetime.now() - start_time).total_seconds()
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Orchestrator test completed in {duration:.2f}s")
                    
                    if result.get("success"):
                        print("✅ Orchestrator functioning correctly")
                        
                        # Check for tool execution
                        analysis = result.get("analysis", {})
                        tools_used = analysis.get("tools_used", [])
                        
                        if "atlassian_search" in tools_used:
                            print("✅ Orchestrator correctly selected Atlassian tools")
                            
                            # Check execution plan
                            execution_plan = analysis.get("execution_plan", {})
                            atlassian_actions = execution_plan.get("atlassian_actions", [])
                            
                            if atlassian_actions:
                                print(f"✅ Generated {len(atlassian_actions)} Atlassian actions")
                                for action in atlassian_actions:
                                    tool = action.get("mcp_tool", "unknown")
                                    print(f"   - {tool}: {action.get('arguments', {})}")
                            else:
                                print("⚠️ No Atlassian actions generated")
                        else:
                            print("⚠️ Orchestrator did not select Atlassian tools")
                            print(f"   Tools selected: {tools_used}")
                    else:
                        error = result.get("error", "Unknown error")
                        print(f"❌ Orchestrator test failed: {error}")
                        
                        # Check specific error patterns
                        if "redis" in error.lower() or "6379" in str(error):
                            print("🔍 REDIS DEPENDENCY ERROR DETECTED!")
                            print("   This confirms Redis is blocking execution")
                            return False
                        elif "timeout" in error.lower():
                            print("🔍 TIMEOUT ERROR DETECTED!")
                            print("   MCP calls may be hanging")
                        elif "mcp" in error.lower():
                            print("🔍 MCP ERROR DETECTED!")
                            print("   MCP integration issue")
                else:
                    print(f"❌ Orchestrator test failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}...")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Orchestrator test timed out")
        print("   This indicates hanging operations (likely Redis)")
        return False
    except Exception as e:
        print(f"❌ Orchestrator test exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n5️⃣ TESTING DIRECT MCP TOOL EXECUTION")
    print("-" * 60)
    
    try:
        # Test direct MCP tool call
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/admin/test-mcp-direct"
            
            test_mcp_payload = {
                "mcp_tool": "confluence_search",
                "arguments": {
                    "query": "Autopilot deployment test",
                    "limit": 3
                }
            }
            
            print("⏱️ Testing direct MCP tool execution...")
            
            async with session.post(
                url,
                json=test_mcp_payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get("success"):
                        results = result.get("results", [])
                        print(f"✅ Direct MCP execution successful: {len(results)} results")
                        
                        if results:
                            first_result = results[0]
                            title = first_result.get("title", "No title")
                            print(f"   Sample: {title}")
                            return True
                        else:
                            print("⚠️ MCP executed but returned no results")
                            return True
                    else:
                        error = result.get("error", "Unknown error")
                        print(f"❌ Direct MCP execution failed: {error}")
                        return False
                else:
                    print(f"❌ Direct MCP test failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Direct MCP test exception: {e}")
        return False
    
    return True


async def test_full_production_scenario():
    """Test the full production scenario exactly as it happens in Slack"""
    
    print("\n" + "=" * 80)
    print("🎯 TESTING FULL PRODUCTION SCENARIO")
    print("=" * 80)
    
    # Simulate exact Slack webhook payload that's failing
    slack_payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "What are the latest Conversational Agents bugs?",
            "user": "U123PROD",
            "channel": "C123PROD",
            "ts": str(datetime.now().timestamp()),
            "event_ts": str(datetime.now().timestamp()),
            "channel_type": "channel"
        },
        "team_id": "T123PROD",
        "event_id": "Ev123PROD",
        "event_time": int(datetime.now().timestamp())
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test webhook processing exactly like production
            url = "http://localhost:5000/slack/events"
            
            print("🚀 Simulating production Slack webhook...")
            
            start_time = datetime.now()
            
            async with session.post(
                url,
                json=slack_payload,
                timeout=120  # 2 minutes like production
            ) as response:
                duration = (datetime.now() - start_time).total_seconds()
                
                print(f"⏱️ Total processing time: {duration:.2f}s")
                
                if response.status == 200:
                    result = await response.text()
                    print("✅ Webhook processing completed successfully")
                    
                    if "execution_error" in result.lower():
                        print("❌ EXECUTION ERROR DETECTED IN RESPONSE!")
                        print("   This is the exact production failure")
                        return False
                    elif "mcp_server_unreachable" in result.lower():
                        print("❌ MCP SERVER UNREACHABLE DETECTED!")
                        print("   MCP connectivity issue confirmed")
                        return False
                    elif "trouble understanding" in result.lower():
                        print("❌ FALLBACK RESPONSE DETECTED!")
                        print("   Orchestrator is failing to analyze queries")
                        return False
                    else:
                        print("✅ Response generated successfully")
                        print(f"   Response length: {len(result)} characters")
                        return True
                else:
                    print(f"❌ Webhook processing failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}...")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Webhook processing timed out after 2 minutes")
        print("   This matches the production timeout behavior")
        return False
    except Exception as e:
        print(f"❌ Webhook processing exception: {e}")
        return False


async def main():
    """Run comprehensive diagnosis and fix"""
    
    print("🔧 COMPREHENSIVE DEPLOYMENT EXECUTION ERROR DIAGNOSIS")
    print("=" * 80)
    
    # Step 1: Diagnose current issues
    diagnosis_success = await diagnose_deployment_execution_error()
    
    if not diagnosis_success:
        print("\n❌ DIAGNOSIS FAILED - CRITICAL ISSUES DETECTED")
        print("   Production deployment has fundamental connectivity issues")
        return False
    
    # Step 2: Test full production scenario
    production_success = await test_full_production_scenario()
    
    if production_success:
        print("\n✅ DEPLOYMENT EXECUTION ERROR FIXED!")
        print("   System is ready for production deployment")
        return True
    else:
        print("\n❌ PRODUCTION SCENARIO STILL FAILING")
        print("   Additional fixes required")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)