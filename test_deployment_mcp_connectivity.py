#!/usr/bin/env python3
"""
Test MCP Connectivity in Deployment Environment

Diagnose the specific networking issue causing "mcp_server_unreachable" in deployment
"""

import asyncio
import httpx
import os
from config import settings

async def test_deployment_mcp():
    """Test MCP connectivity in deployment environment"""
    print("🔍 Deployment MCP Connectivity Test")
    print("=" * 50)
    
    mcp_url = settings.MCP_SERVER_URL
    print(f"Testing MCP URL: {mcp_url}")
    
    # Test 1: Basic HTTP connectivity
    print("\n1. Basic HTTP Connectivity:")
    test_endpoints = [
        "/",
        "/health", 
        "/healthz",
        "/mcp",
        "/mcp/sse"
    ]
    
    for endpoint in test_endpoints:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{mcp_url}{endpoint}")
                print(f"✅ {endpoint}: {response.status_code}")
        except httpx.ConnectError as e:
            print(f"❌ {endpoint}: Connection Error - {e}")
        except httpx.TimeoutException:
            print(f"❌ {endpoint}: Timeout")
        except Exception as e:
            print(f"❌ {endpoint}: {type(e).__name__}: {e}")
    
    # Test 2: Alternative URLs
    print("\n2. Alternative URL Tests:")
    alternative_urls = [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://0.0.0.0:8001"
    ]
    
    for alt_url in alternative_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{alt_url}/mcp/sse", headers={'Accept': 'text/event-stream'})
                print(f"✅ {alt_url}: {response.status_code}")
                if response.status_code == 200:
                    print(f"   SUCCESS: {alt_url} is reachable!")
                    return alt_url
        except Exception as e:
            print(f"❌ {alt_url}: {type(e).__name__}: {e}")
    
    # Test 3: Check if MCP server process is actually responding
    print("\n3. Process and Port Analysis:")
    import subprocess
    try:
        # Check processes
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        mcp_processes = [line for line in result.stdout.split('\n') if 'run_mcp_server' in line]
        if mcp_processes:
            print("✅ MCP server process found:")
            for proc in mcp_processes:
                print(f"   {proc}")
        else:
            print("❌ No MCP server process found")
        
        # Check port binding
        result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True)
        port_8001 = [line for line in result.stdout.split('\n') if ':8001' in line]
        if port_8001:
            print("✅ Port 8001 binding found:")
            for binding in port_8001:
                print(f"   {binding}")
        else:
            print("❌ No process bound to port 8001")
            
    except Exception as e:
        print(f"❌ Process check failed: {e}")
    
    return None

async def main():
    working_url = await test_deployment_mcp()
    
    if working_url:
        print(f"\n🎉 SOLUTION FOUND:")
        print(f"Update MCP_SERVER_URL to: {working_url}")
    else:
        print(f"\n❌ MCP server connectivity issue detected")
        print("Check if MCP Atlassian Server workflow is running properly")

if __name__ == "__main__":
    asyncio.run(main())