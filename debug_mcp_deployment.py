#!/usr/bin/env python3
"""
Debug MCP Deployment Issues

This script diagnoses what's actually happening with the MCP server in deployment
to identify the root cause beyond URL configuration.
"""

import os
import sys
import asyncio
import aiohttp
import subprocess
import psutil
from datetime import datetime

async def debug_mcp_deployment():
    """
    Comprehensive debugging of MCP server deployment issues
    """
    print("🔍 MCP Deployment Diagnosis")
    print("=" * 50)
    
    # 1. Check if MCP server process is actually running
    print("\n1. Process Analysis:")
    mcp_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'mcp' in cmdline.lower() or 'run_mcp_server' in cmdline:
                mcp_processes.append({
                    'pid': proc.info['pid'], 
                    'name': proc.info['name'],
                    'cmdline': cmdline
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if mcp_processes:
        print("✅ MCP processes found:")
        for proc in mcp_processes:
            print(f"   PID {proc['pid']}: {proc['cmdline']}")
    else:
        print("❌ No MCP server processes found!")
        return
    
    # 2. Check port availability
    print("\n2. Port Analysis:")
    port_8001_in_use = False
    for conn in psutil.net_connections():
        if conn.laddr.port == 8001:
            port_8001_in_use = True
            print(f"✅ Port 8001 is bound by PID {conn.pid}")
            break
    
    if not port_8001_in_use:
        print("❌ Port 8001 is not bound by any process!")
        return
    
    # 3. Test HTTP connectivity to MCP server
    print("\n3. HTTP Connectivity Tests:")
    test_urls = [
        "http://localhost:8001",
        "http://0.0.0.0:8001", 
        "http://127.0.0.1:8001"
    ]
    
    for url in test_urls:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{url}/health") as response:
                    status = response.status
                    text = await response.text()
                    print(f"✅ {url}/health: {status} - {text[:100]}")
        except Exception as e:
            print(f"❌ {url}/health: {type(e).__name__}: {e}")
    
    # 4. Test SSE endpoint specifically
    print("\n4. SSE Endpoint Tests:")
    for url in test_urls:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{url}/sse") as response:
                    status = response.status
                    content_type = response.headers.get('content-type', '')
                    print(f"✅ {url}/sse: {status} - Content-Type: {content_type}")
        except Exception as e:
            print(f"❌ {url}/sse: {type(e).__name__}: {e}")
    
    # 5. Check environment variables
    print("\n5. Environment Analysis:")
    env_vars = [
        "ATLASSIAN_JIRA_URL", "ATLASSIAN_JIRA_USERNAME", "ATLASSIAN_JIRA_TOKEN",
        "ATLASSIAN_CONFLUENCE_URL", "ATLASSIAN_CONFLUENCE_USERNAME", "ATLASSIAN_CONFLUENCE_TOKEN",
        "MCP_SERVER_URL"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "")
        if value:
            # Mask sensitive values
            if "TOKEN" in var or "PASSWORD" in var:
                masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
    
    # 6. Test direct MCP protocol handshake
    print("\n6. MCP Protocol Handshake Test:")
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
    
    try:
        # Test initialize request
        async with aiohttp.ClientSession() as session:
            initialize_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0.0",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            async with session.post(f"{mcp_url}/message", json=initialize_data) as response:
                status = response.status
                text = await response.text()
                print(f"✅ MCP Initialize: {status}")
                print(f"   Response: {text[:200]}...")
                
    except Exception as e:
        print(f"❌ MCP Initialize: {type(e).__name__}: {e}")
    
    # 7. Check MCP server logs if accessible
    print("\n7. MCP Server Log Analysis:")
    try:
        # Try to get recent logs from the MCP server process
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'run_mcp_server' in result.stdout:
            print("✅ MCP server process visible in ps output")
        else:
            print("❌ MCP server process not visible in ps output")
    except Exception as e:
        print(f"❌ Unable to check process list: {e}")

if __name__ == "__main__":
    asyncio.run(debug_mcp_deployment())