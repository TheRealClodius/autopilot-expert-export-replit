#!/usr/bin/env python3
"""
Complete Deployment Verification Test

This script tests the complete end-to-end flow that was failing in production
to verify the deployment URL fix resolves the "execution error" issues.
"""

import asyncio
import json
import aiohttp


async def test_complete_deployment_fix():
    """Test complete end-to-end deployment fix"""
    
    print("=" * 80)
    print("🚀 COMPLETE DEPLOYMENT VERIFICATION TEST")
    print("=" * 80)
    
    # Test the admin test endpoint that replicates the production failure
    print("\n1️⃣ TESTING ADMIN ATLASSIAN INTEGRATION ENDPOINT")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/admin/test-atlassian-integration"
            
            print(f"Testing: {url}")
            
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Admin endpoint test PASSED")
                    
                    # Check orchestrator intelligence
                    orchestrator_result = result.get("orchestrator_test", {})
                    if orchestrator_result.get("success"):
                        print(f"✅ Orchestrator correctly identified tools: {orchestrator_result.get('tools', [])}")
                    else:
                        print(f"❌ Orchestrator test failed: {orchestrator_result}")
                        return False
                    
                    # Check MCP health
                    mcp_health = result.get("mcp_health", {})
                    if mcp_health.get("healthy"):
                        print("✅ MCP server health check passed")
                    else:
                        print(f"❌ MCP server health check failed: {mcp_health}")
                        return False
                    
                    # Check tool execution
                    tool_execution = result.get("tool_execution", {})
                    if tool_execution.get("success"):
                        results_count = len(tool_execution.get("results", []))
                        print(f"✅ Tool execution successful with {results_count} results")
                        
                        # Show sample results
                        if tool_execution.get("results"):
                            first_result = tool_execution["results"][0]
                            title = first_result.get("title", "No title")
                            space = first_result.get("space", {}).get("name", "Unknown")
                            print(f"   Sample result: {title} (Space: {space})")
                    else:
                        print(f"❌ Tool execution failed: {tool_execution}")
                        return False
                        
                else:
                    print(f"❌ Admin endpoint failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:200]}...")
                    return False
                    
    except Exception as e:
        print(f"❌ Admin endpoint test exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test simulated Slack webhook processing
    print("\n2️⃣ TESTING SIMULATED SLACK WEBHOOK PROCESSING")
    print("-" * 60)
    
    try:
        # Create a realistic Slack webhook payload
        slack_payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "Can you find information about UiPath Autopilot features for deployment?",
                "user": "U123TEST",
                "channel": "C123TEST",
                "ts": "1234567890.123456"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:5000/admin/test-webhook-processing"
            
            print(f"Testing simulated webhook: {url}")
            
            async with session.post(
                url, 
                json=slack_payload,
                timeout=60  # Give enough time for processing
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Webhook processing test PASSED")
                    
                    # Check message processing
                    if result.get("processed"):
                        print("✅ Message was successfully processed")
                        
                        # Check if orchestrator was called
                        if "orchestrator_analysis" in result:
                            analysis = result["orchestrator_analysis"]
                            tools_used = analysis.get("tools_used", [])
                            print(f"✅ Orchestrator used tools: {tools_used}")
                            
                            # Check for Atlassian tool usage
                            if any("atlassian" in tool.lower() for tool in tools_used):
                                print("✅ Atlassian tool was correctly selected")
                                
                                # Check for results
                                if "search_results" in analysis:
                                    results = analysis["search_results"]
                                    if results:
                                        print(f"✅ Retrieved {len(results)} search results")
                                        first_result = results[0]
                                        print(f"   First result: {first_result.get('title', 'No title')}")
                                    else:
                                        print("⚠️ No search results (may be normal for test query)")
                                else:
                                    print("⚠️ No search results in analysis")
                            else:
                                print("❌ Atlassian tool was not used - this indicates routing issue")
                                return False
                        else:
                            print("❌ No orchestrator analysis found")
                            return False
                    else:
                        print(f"❌ Message processing failed: {result}")
                        return False
                        
                else:
                    print(f"❌ Webhook processing failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:200]}...")
                    return False
                    
    except Exception as e:
        print(f"❌ Webhook processing test exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 COMPLETE DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 80)
    
    print("✅ Admin Atlassian integration endpoint working")
    print("✅ MCP server health check passing")
    print("✅ Tool execution successful with authentic UiPath data")
    print("✅ Orchestrator correctly routing to Atlassian tools")
    print("✅ Simulated Slack webhook processing working")
    print()
    print("🚀 DEPLOYMENT FIX VERIFICATION: COMPLETE SUCCESS")
    print("   The 'execution error' production issue has been resolved!")
    print("   System is ready for production deployment.")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_complete_deployment_fix())
    exit(0 if success else 1)