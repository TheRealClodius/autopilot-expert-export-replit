#!/usr/bin/env python3
"""
Test deployment fix verification - Comprehensive testing that both servers start correctly
"""

import asyncio
import aiohttp
import subprocess
import time
import os
import sys
from datetime import datetime


async def test_deployment_startup():
    """Test the new deployment startup script"""
    
    print("=" * 80)
    print("🔧 TESTING DEPLOYMENT STARTUP FIX")
    print("=" * 80)
    
    print("\n1️⃣ TESTING DUAL SERVER STARTUP")
    print("-" * 60)
    
    # Test the new deployment startup script
    try:
        print("🚀 Testing start_deployment.py...")
        
        # Start the deployment script as a subprocess
        process = subprocess.Popen(
            [sys.executable, "start_deployment.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        print(f"Deployment script started with PID: {process.pid}")
        
        # Give it time to start both servers
        print("⏳ Waiting for servers to initialize...")
        await asyncio.sleep(15)
        
        # Test both servers are running
        print("\n2️⃣ VERIFYING SERVER AVAILABILITY")
        print("-" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Test MCP server
            try:
                async with session.get("http://localhost:8001/healthz", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        print("✅ MCP server is running and responding")
                        mcp_ready = True
                    else:
                        print(f"❌ MCP server returned status: {response.status}")
                        mcp_ready = False
            except Exception as e:
                print(f"❌ MCP server not reachable: {e}")
                mcp_ready = False
            
            # Test FastAPI server
            try:
                async with session.get("http://localhost:5000/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("✅ FastAPI server is running and responding")
                        print(f"   Status: {result.get('status', 'unknown')}")
                        fastapi_ready = True
                    else:
                        print(f"❌ FastAPI server returned status: {response.status}")
                        fastapi_ready = False
            except Exception as e:
                print(f"❌ FastAPI server not reachable: {e}")
                fastapi_ready = False
        
        # Test MCP integration
        if mcp_ready and fastapi_ready:
            print("\n3️⃣ TESTING MCP INTEGRATION")
            print("-" * 60)
            
            try:
                async with aiohttp.ClientSession() as session:
                    url = "http://localhost:5000/admin/test-atlassian-integration"
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # Check MCP health
                            mcp_health = result.get("mcp_health", {})
                            if mcp_health.get("healthy"):
                                print("✅ MCP integration working correctly")
                                
                                # Check tool execution
                                tool_execution = result.get("tool_execution", {})
                                if tool_execution.get("success"):
                                    results = tool_execution.get("results", [])
                                    print(f"✅ MCP tool execution successful: {len(results)} results")
                                    
                                    if results:
                                        sample = results[0]
                                        title = sample.get("title", "No title")
                                        print(f"   Sample result: {title}")
                                        
                                        integration_success = True
                                    else:
                                        print("⚠️ MCP executed but no results returned")
                                        integration_success = True  # Still working
                                else:
                                    error = tool_execution.get("error", "Unknown error")
                                    print(f"❌ MCP tool execution failed: {error}")
                                    integration_success = False
                            else:
                                print(f"❌ MCP integration failed: {mcp_health}")
                                integration_success = False
                        else:
                            print(f"❌ Integration test failed: {response.status}")
                            integration_success = False
            except Exception as e:
                print(f"❌ Integration test exception: {e}")
                integration_success = False
        else:
            print("\n⏸️ Skipping integration test - servers not ready")
            integration_success = False
        
        # Test production scenario
        if mcp_ready and fastapi_ready and integration_success:
            print("\n4️⃣ TESTING PRODUCTION SCENARIO")
            print("-" * 60)
            
            # Simulate the exact failing Slack webhook
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
                "event_id": f"Ev{int(datetime.now().timestamp())}TEST",
                "event_time": int(datetime.now().timestamp())
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    url = "http://localhost:5000/slack/events"
                    
                    print("🔍 Testing production query...")
                    
                    start_time = datetime.now()
                    
                    async with session.post(
                        url,
                        json=slack_payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        duration = (datetime.now() - start_time).total_seconds()
                        
                        print(f"⏱️ Processing time: {duration:.2f}s")
                        
                        if response.status == 200:
                            result = await response.text()
                            
                            # Check for failure patterns
                            result_lower = result.lower()
                            
                            if "mcp_server_unreachable" in result_lower:
                                print("❌ STILL GETTING MCP_SERVER_UNREACHABLE!")
                                print("   This means the deployment fix didn't work")
                                production_success = False
                            elif "execution_error" in result_lower:
                                print("❌ STILL GETTING EXECUTION_ERROR!")
                                print("   The core issue persists")
                                production_success = False
                            elif any(error in result_lower for error in ["trouble understanding", "couldn't process"]):
                                print("❌ Getting fallback error responses")
                                production_success = False
                            else:
                                print("✅ PRODUCTION SCENARIO FIXED!")
                                print("   No more mcp_server_unreachable errors")
                                production_success = True
                        else:
                            print(f"❌ Production test failed: {response.status}")
                            production_success = False
                            
            except Exception as e:
                print(f"❌ Production test exception: {e}")
                production_success = False
        else:
            print("\n⏸️ Skipping production test - integration not working")
            production_success = False
        
        # Cleanup - terminate the deployment process
        print("\n5️⃣ CLEANUP")
        print("-" * 60)
        
        print("Terminating deployment test process...")
        process.terminate()
        
        # Wait for clean shutdown
        try:
            process.wait(timeout=10)
            print("✅ Deployment process terminated cleanly")
        except subprocess.TimeoutExpired:
            print("⚠️ Force killing deployment process")
            process.kill()
        
        # Final assessment
        print("\n" + "=" * 80)
        print("📊 DEPLOYMENT FIX ASSESSMENT")
        print("=" * 80)
        
        if mcp_ready and fastapi_ready:
            print("✅ Both servers start correctly with new deployment script")
        else:
            print("❌ Server startup issues remain")
        
        if integration_success:
            print("✅ MCP integration working")
        else:
            print("❌ MCP integration still has issues")
        
        if production_success:
            print("✅ PRODUCTION DEPLOYMENT ISSUE RESOLVED!")
            print("   Ready to deploy with start_deployment.py")
            return True
        else:
            print("❌ Production scenario still failing")
            print("   Additional fixes needed")
            return False
            
    except Exception as e:
        print(f"❌ Deployment test failed: {e}")
        return False


async def main():
    """Run deployment fix verification"""
    
    print("🔧 DEPLOYMENT FIX VERIFICATION")
    print("Testing the solution to missing MCP server in deployment")
    print("=" * 80)
    
    success = await test_deployment_startup()
    
    if success:
        print("\n🎉 DEPLOYMENT FIX VERIFIED!")
        print("The start_deployment.py script successfully resolves the MCP server issue")
    else:
        print("\n❌ DEPLOYMENT FIX INCOMPLETE")
        print("Additional work needed to resolve the production issues")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)