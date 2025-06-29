#!/usr/bin/env python3
"""
Debug Production MCP Deployment Issues

Comprehensive diagnosis of what's actually happening with MCP in deployment
to identify the specific networking configuration needed.
"""

import asyncio
import os
import httpx
import json
from tools.atlassian_tool import AtlassianTool

async def debug_production_mcp():
    """
    Debug the exact MCP deployment networking issue
    """
    
    print("=" * 80)
    print("🚨 PRODUCTION MCP DEPLOYMENT DIAGNOSIS")
    print("=" * 80)
    
    # 1. Environment Analysis
    print("🌍 Current Environment:")
    print(f"   REPLIT_DEPLOYMENT = {os.getenv('REPLIT_DEPLOYMENT', '<not set>')}")
    print(f"   DEPLOYMENT_ENV = {os.getenv('DEPLOYMENT_ENV', '<not set>')}")
    print(f"   PORT = {os.getenv('PORT', '<not set>')}")
    print(f"   REPLIT_DOMAINS = {os.getenv('REPLIT_DOMAINS', '<not set>')}")
    print(f"   MCP_SERVER_URL = {os.getenv('MCP_SERVER_URL', 'http://localhost:8001')}")
    print(f"   ATLASSIAN_JIRA_URL = {os.getenv('ATLASSIAN_JIRA_URL', '<not set>')}")
    print(f"   ATLASSIAN_CONFLUENCE_URL = {os.getenv('ATLASSIAN_CONFLUENCE_URL', '<not set>')}")
    
    # 2. Deployment Detection
    replit_domains = os.getenv("REPLIT_DOMAINS", "")
    is_deployment = any([
        os.getenv("REPLIT_DEPLOYMENT") == "1",
        os.getenv("DEPLOYMENT_ENV") == "production",
        os.getenv("PORT") and os.getenv("PORT") != "5000",
        "replit.app" in replit_domains,
        "replit.dev" in replit_domains,
        len(replit_domains) > 0 and ("riker." in replit_domains or "wolf." in replit_domains)
    ])
    print(f"\n🔍 Deployment Environment Detection:")
    print(f"   Detected as deployment: {is_deployment}")
    
    # 3. MCP URL Configuration Testing
    print(f"\n🌐 MCP URLs to Test:")
    
    base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
    test_urls = [base_url]
    
    # Add deployment-specific URLs if detected
    if is_deployment:
        deployment_urls = [
            "http://mcp-atlassian-server:8001",
            "http://mcp-server:8001", 
            "http://localhost:8001",
            "http://127.0.0.1:8001"
        ]
        test_urls.extend([url for url in deployment_urls if url not in test_urls])
    else:
        test_urls.extend(["http://127.0.0.1:8001"])
    
    print("   URLs to try (in order):")
    for i, url in enumerate(test_urls, 1):
        print(f"   {i}. {url}")
    
    # 4. Basic HTTP Connectivity Test
    print(f"\n🔗 Testing Basic HTTP Connectivity:")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        working_urls = []
        
        for url in test_urls:
            print(f"\n   Testing {url}...")
            
            try:
                # Test health endpoint
                health_response = await client.get(f"{url}/healthz")
                print(f"   ✅ Health check: {health_response.status_code}")
                
                # Test SSE endpoint  
                sse_response = await client.get(f"{url}/sse")
                print(f"   ✅ SSE endpoint: {sse_response.status_code}")
                
                working_urls.append(url)
                
            except Exception as e:
                print(f"   ❌ Connection failed: {e}")
    
    # 5. AtlassianTool MCP Connection Test
    print(f"\n🛠️ Testing AtlassianTool MCP Connection:")
    
    for url in working_urls[:2]:  # Test top 2 working URLs
        print(f"   Current MCP URL: {url}")
        
        # Temporarily override the URL for testing
        original_url = os.environ.get("MCP_SERVER_URL")
        os.environ["MCP_SERVER_URL"] = url
        
        try:
            atlassian_tool = AtlassianTool()
            
            # Test session establishment
            try:
                session_result = await atlassian_tool._get_session_endpoint()
                print(f"   ✅ Session established: {session_result}")
            except Exception as e:
                print(f"   ❌ Session failed: {e}")
            
            # Test tool execution
            try:
                result = await atlassian_tool.execute_mcp_tool("confluence_search", {
                    "query": "Autopilot test",
                    "limit": 3
                })
                
                if "error" in result:
                    print(f"   ❌ Tool execution failed: {result['error']}")
                else:
                    print(f"   ✅ Tool execution successful")
                    
            except Exception as e:
                print(f"   ❌ Tool execution exception: {e}")
                
        finally:
            # Restore original URL
            if original_url:
                os.environ["MCP_SERVER_URL"] = original_url
            elif "MCP_SERVER_URL" in os.environ:
                del os.environ["MCP_SERVER_URL"]
    
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