#!/usr/bin/env python3
"""
Debug Production MCP Deployment Issues

Comprehensive diagnosis of what's actually happening with MCP in deployment
to identify the specific networking configuration needed.
"""

import asyncio
import os
import httpx
from tools.atlassian_tool import AtlassianTool

async def debug_production_mcp():
    """
    Debug the exact MCP deployment networking issue
    """
    
    print("=" * 80)
    print("🚨 PRODUCTION MCP DEPLOYMENT DIAGNOSIS")
    print("=" * 80)
    
    # Check current environment variables
    print("🌍 Current Environment:")
    env_vars = [
        "REPLIT_DEPLOYMENT", "DEPLOYMENT_ENV", "PORT", "REPLIT_DOMAINS",
        "MCP_SERVER_URL", "ATLASSIAN_JIRA_URL", "ATLASSIAN_CONFLUENCE_URL"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"   {var} = {value}")
        else:
            print(f"   {var} = <not set>")
    
    # Test actual deployment environment detection
    print("\n🔍 Deployment Environment Detection:")
    is_deployment = any([
        os.getenv("REPLIT_DEPLOYMENT") == "1",
        os.getenv("DEPLOYMENT_ENV") == "production",
        os.getenv("PORT") and os.getenv("PORT") != "5000",
        "replit.app" in os.getenv("REPLIT_DOMAINS", "")
    ])
    print(f"   Detected as deployment: {is_deployment}")
    
    # Test MCP URLs that would be tried
    print("\n🌐 MCP URLs to Test:")
    deployment_urls = []
    
    if is_deployment:
        deployment_urls = [
            "http://mcp-atlassian-server:8001",
            "http://mcp-server:8001", 
            "http://0.0.0.0:8001",
            "http://127.0.0.1:8001",
        ]
    
    test_urls = [
        os.getenv("MCP_SERVER_URL", "http://localhost:8001"),
        *deployment_urls,
        "http://localhost:8001",
        "http://127.0.0.1:8001"
    ]
    
    # Remove duplicates while preserving order
    unique_urls = []
    for url in test_urls:
        if url not in unique_urls:
            unique_urls.append(url)
    
    print(f"   URLs to try (in order):")
    for i, url in enumerate(unique_urls, 1):
        print(f"   {i}. {url}")
    
    # Test each URL for basic connectivity
    print("\n🔗 Testing Basic HTTP Connectivity:")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in unique_urls:
            try:
                print(f"\n   Testing {url}...")
                
                # Test basic health endpoint
                health_url = f"{url}/healthz"
                try:
                    response = await client.get(health_url)
                    print(f"   ✅ Health check: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ Health check failed: {e}")
                
                # Test MCP SSE endpoint
                sse_url = f"{url}/mcp/sse"
                try:
                    response = await client.get(sse_url)
                    print(f"   ✅ SSE endpoint: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ SSE endpoint failed: {e}")
                
            except Exception as e:
                print(f"   ❌ Connection to {url} failed: {e}")
    
    # Test actual AtlassianTool connectivity
    print("\n🛠️ Testing AtlassianTool MCP Connection:")
    try:
        atlassian_tool = AtlassianTool()
        print(f"   Current MCP URL: {atlassian_tool.mcp_server_url}")
        
        # Test session establishment
        try:
            session_endpoint = await atlassian_tool._get_session_endpoint()
            print(f"   ✅ Session established: {session_endpoint}")
        except Exception as e:
            print(f"   ❌ Session failed: {e}")
        
        # Test tool execution
        try:
            result = await atlassian_tool.execute_mcp_tool("jira_search", {
                "query": "test",
                "limit": 1
            })
            
            if "error" in result:
                print(f"   ❌ Tool execution error: {result['error']}")
                print(f"      Message: {result.get('message', 'No message')}")
            else:
                print(f"   ✅ Tool execution successful")
                
        except Exception as e:
            print(f"   ❌ Tool execution exception: {e}")
            
    except Exception as e:
        print(f"   ❌ AtlassianTool initialization failed: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 DIAGNOSIS COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Check which URLs are actually reachable")
    print("2. Verify MCP server is accessible from main application") 
    print("3. Identify correct container networking configuration")
    print("4. Update deployment URL configuration accordingly")

if __name__ == "__main__":
    asyncio.run(debug_production_mcp())