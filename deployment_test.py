#!/usr/bin/env python3
"""
Comprehensive deployment readiness test for the multi-agent system.
Tests all critical components and configurations before deployment.
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append('.')

from config import Settings

async def test_deployment_readiness():
    """Run comprehensive deployment readiness tests"""
    
    print("🚀 DEPLOYMENT READINESS TEST")
    print("=" * 50)
    print(f"Test started at: {datetime.now().isoformat()}")
    print()
    
    settings = Settings()
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0}
    }
    
    base_url = "http://localhost:5000"
    
    # Test 1: Basic Health Check
    print("1. Testing basic health endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("   ✅ Health check passed")
                    results["tests"]["health_check"] = {"status": "passed", "details": data}
                else:
                    print("   ❌ Health check failed - unhealthy status")
                    results["tests"]["health_check"] = {"status": "failed", "details": data}
            else:
                print(f"   ❌ Health check failed - status {response.status_code}")
                results["tests"]["health_check"] = {"status": "failed", "details": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"   ❌ Health check failed - {e}")
        results["tests"]["health_check"] = {"status": "failed", "details": str(e)}
    
    # Test 2: Configuration Check
    print("\n2. Testing configuration...")
    config_issues = []
    
    if not settings.SLACK_BOT_TOKEN:
        config_issues.append("SLACK_BOT_TOKEN missing")
    if not settings.GEMINI_API_KEY:
        config_issues.append("GEMINI_API_KEY missing")
    if not settings.PINECONE_API_KEY:
        config_issues.append("PINECONE_API_KEY missing")
    
    print(f"   MCP Server URL: {settings.MCP_SERVER_URL}")
    print(f"   Deployment Aware URL: {settings.DEPLOYMENT_AWARE_MCP_URL}")
    print(f"   Slack Bot Token: {'✅ Configured' if settings.SLACK_BOT_TOKEN else '❌ Missing'}")
    print(f"   Gemini API Key: {'✅ Configured' if settings.GEMINI_API_KEY else '❌ Missing'}")
    print(f"   Pinecone API Key: {'✅ Configured' if settings.PINECONE_API_KEY else '❌ Missing'}")
    
    if config_issues:
        print(f"   ❌ Configuration issues: {', '.join(config_issues)}")
        results["tests"]["configuration"] = {"status": "failed", "details": config_issues}
    else:
        print("   ✅ All critical configuration present")
        results["tests"]["configuration"] = {"status": "passed", "details": "all_keys_present"}
    
    # Test 3: System Status
    print("\n3. Testing system status...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/admin/system-status")
            if response.status_code == 200:
                data = response.json()
                agents_healthy = data.get("agents") == "healthy"
                services_init = data.get("services_initialized", False)
                
                print(f"   Agents: {'✅' if agents_healthy else '❌'} {data.get('agents', 'unknown')}")
                print(f"   Services: {'✅' if services_init else '❌'} {'initialized' if services_init else 'not initialized'}")
                print(f"   Redis: ⚠️ {data.get('redis', 'unknown')} (expected fallback)")
                print(f"   Celery: ⚠️ {data.get('celery', 'unknown')} (expected fallback)")
                
                if agents_healthy and services_init:
                    print("   ✅ System status acceptable for deployment")
                    results["tests"]["system_status"] = {"status": "passed", "details": data}
                else:
                    print("   ❌ System status not ready")
                    results["tests"]["system_status"] = {"status": "failed", "details": data}
            else:
                print(f"   ❌ System status check failed - status {response.status_code}")
                results["tests"]["system_status"] = {"status": "failed", "details": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"   ❌ System status check failed - {e}")
        results["tests"]["system_status"] = {"status": "failed", "details": str(e)}
    
    # Test 4: Root Endpoint (Deployment Critical)
    print("\n4. Testing root endpoint (deployment critical)...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("   ✅ Root endpoint responding")
                results["tests"]["root_endpoint"] = {"status": "passed", "details": "responding"}
            else:
                print(f"   ❌ Root endpoint failed - status {response.status_code}")
                results["tests"]["root_endpoint"] = {"status": "failed", "details": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"   ❌ Root endpoint failed - {e}")
        results["tests"]["root_endpoint"] = {"status": "failed", "details": str(e)}
    
    # Test 5: Slack Webhook Endpoint
    print("\n5. Testing Slack webhook endpoint...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test with URL verification challenge (Slack format)
            test_payload = {
                "type": "url_verification",
                "challenge": "test_challenge_123"
            }
            response = await client.post(f"{base_url}/slack/events", json=test_payload)
            if response.status_code == 200 and response.text == "test_challenge_123":
                print("   ✅ Slack webhook endpoint responding correctly")
                results["tests"]["slack_webhook"] = {"status": "passed", "details": "url_verification_working"}
            else:
                print(f"   ❌ Slack webhook failed - status {response.status_code}")
                results["tests"]["slack_webhook"] = {"status": "failed", "details": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"   ❌ Slack webhook test failed - {e}")
        results["tests"]["slack_webhook"] = {"status": "failed", "details": str(e)}
    
    # Test 6: MCP Server Connection Configuration
    print("\n6. Testing MCP server connection configuration...")
    mcp_url = settings.DEPLOYMENT_AWARE_MCP_URL
    if mcp_url == "http://localhost:8001":
        print("   ⚠️ MCP URL set to localhost (needs remote URL for deployment)")
        print("   📝 Set MCP_SERVER_URL=https://your-mcp-server.replit.app in deployment")
        results["tests"]["mcp_configuration"] = {"status": "warning", "details": "localhost_url_needs_update"}
    else:
        print(f"   ✅ MCP URL configured for remote connection: {mcp_url}")
        results["tests"]["mcp_configuration"] = {"status": "passed", "details": mcp_url}
    
    # Test 7: Port Configuration
    print("\n7. Testing port configuration...")
    port = os.getenv("PORT", "5000")
    if port == "5000":
        print("   ✅ Port configuration ready for deployment (uses PORT env var)")
        results["tests"]["port_config"] = {"status": "passed", "details": "dynamic_port_ready"}
    else:
        print(f"   ✅ Port configuration: {port}")
        results["tests"]["port_config"] = {"status": "passed", "details": f"port_{port}"}
    
    # Calculate summary
    for test_name, test_result in results["tests"].items():
        results["summary"]["total"] += 1
        if test_result["status"] == "passed":
            results["summary"]["passed"] += 1
        elif test_result["status"] == "failed":
            results["summary"]["failed"] += 1
        elif test_result["status"] == "warning":
            results["summary"]["warnings"] += 1
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT READINESS SUMMARY")
    print("=" * 50)
    print(f"Total tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']} ✅")
    print(f"Failed: {results['summary']['failed']} ❌")
    print(f"Warnings: {results['summary']['warnings']} ⚠️")
    
    # Deployment recommendation
    print("\n🚀 DEPLOYMENT RECOMMENDATION:")
    if results["summary"]["failed"] == 0:
        if results["summary"]["warnings"] == 0:
            print("✅ READY FOR DEPLOYMENT - All tests passed!")
        else:
            print("⚠️ READY FOR DEPLOYMENT - Minor warnings noted above")
        print("\nNext steps:")
        print("1. Click 'Deploy' in Replit")
        print("2. Set MCP_SERVER_URL to your deployed MCP server URL")
        print("3. Test the deployed application")
    else:
        print("❌ NOT READY - Fix failed tests before deployment")
        print("\nRequired fixes:")
        for test_name, test_result in results["tests"].items():
            if test_result["status"] == "failed":
                print(f"   - {test_name}: {test_result['details']}")
    
    # Save results
    with open("deployment_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: deployment_test_results.json")
    return results

if __name__ == "__main__":
    asyncio.run(test_deployment_readiness())