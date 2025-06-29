#!/usr/bin/env python3

"""
Test Deployment Environment Differences

This script tests the exact production deployment scenario
to identify differences between local testing and deployed environment.
"""

import asyncio
import os
import httpx
import json

async def test_deployment_environment():
    """Test deployment environment issues"""
    print("🔍 Testing Deployment Environment Differences...")
    
    # Test 1: Environment variables
    print("\n📋 Environment Configuration:")
    atlassian_vars = [
        "ATLASSIAN_JIRA_URL", "ATLASSIAN_JIRA_USERNAME", "ATLASSIAN_JIRA_TOKEN",
        "ATLASSIAN_CONFLUENCE_URL", "ATLASSIAN_CONFLUENCE_USERNAME", "ATLASSIAN_CONFLUENCE_TOKEN"
    ]
    
    env_status = {}
    for var in atlassian_vars:
        value = os.getenv(var)
        if value:
            env_status[var] = f"✅ Set ({len(value)} chars)"
        else:
            env_status[var] = "❌ Missing"
    
    for var, status in env_status.items():
        print(f"   {var}: {status}")
    
    # Test 2: MCP Server Direct Connection
    print("\n🔗 MCP Server Direct Connection Test:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health endpoint
            health_response = await client.get("http://localhost:8001/healthz")
            print(f"   Health check: {health_response.status_code} - {health_response.text}")
            
            # Test MCP initialization
            init_request = {
                "jsonrpc": "2.0",
                "id": "test-deployment",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "deployment-test",
                        "version": "1.0.0"
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            print(f"   Testing MCP initialization...")
            init_response = await client.post("http://localhost:8001/mcp", json=init_request, headers=headers)
            print(f"   Init response: {init_response.status_code}")
            
            if init_response.status_code == 307:
                redirect_url = init_response.headers.get("location")
                print(f"   Redirect URL: {redirect_url}")
                
                if redirect_url:
                    # Follow redirect
                    redirect_response = await client.post(redirect_url, json=init_request, headers=headers)
                    print(f"   Redirect response: {redirect_response.status_code}")
                    print(f"   Response content: {redirect_response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ MCP Connection Error: {e}")
    
    # Test 3: Check if there are missing credentials
    print("\n🔑 Credentials Analysis:")
    missing_creds = [var for var, status in env_status.items() if status == "❌ Missing"]
    if missing_creds:
        print(f"   ❌ Missing credentials may cause deployment failures:")
        for var in missing_creds:
            print(f"      - {var}")
    else:
        print("   ✅ All required Atlassian credentials are present")
    
    # Test 4: Check for deployment-specific issues
    print("\n🚀 Deployment Environment Analysis:")
    
    # Check if running in containerized environment
    if os.path.exists("/.dockerenv"):
        print("   📦 Running in Docker container")
    else:
        print("   💻 Running in standard environment")
    
    # Check network accessibility
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test external connectivity
            test_response = await client.get("https://httpbin.org/get")
            print(f"   🌐 External connectivity: ✅ ({test_response.status_code})")
    except Exception as e:
        print(f"   🌐 External connectivity: ❌ ({e})")
    
    print("\n🎯 RECOMMENDATION:")
    if missing_creds:
        print("   The deployment environment is missing Atlassian credentials.")
        print("   This would cause MCP authentication failures in production.")
        print("   Solution: Provide the missing environment variables to the deployment.")
    else:
        print("   Credentials are present. The issue may be:")
        print("   1. Network connectivity between services in deployment")
        print("   2. MCP session timeout under production load")
        print("   3. Different service startup timing in deployment environment")

if __name__ == "__main__":
    asyncio.run(test_deployment_environment())