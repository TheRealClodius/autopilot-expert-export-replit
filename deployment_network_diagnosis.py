#!/usr/bin/env python3
"""
Deployment Network Diagnosis

Comprehensive diagnosis of MCP server connectivity in deployment environments
to identify the exact networking configuration needed.
"""

import asyncio
import httpx
import os
import subprocess
import socket
from config import settings

async def diagnose_deployment_network():
    """Comprehensive network diagnosis for deployment environments"""
    
    print("🌐 DEPLOYMENT NETWORK DIAGNOSIS")
    print("=" * 60)
    
    results = {
        "mcp_server_reachable": False,
        "port_accessible": False,
        "process_running": False,
        "recommended_url": None
    }
    
    # 1. Check current MCP_SERVER_URL configuration
    print(f"\n1. Current Configuration:")
    print(f"   MCP_SERVER_URL: {settings.MCP_SERVER_URL}")
    
    # 2. Test localhost connectivity
    print(f"\n2. Testing localhost connectivity...")
    localhost_urls = [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://0.0.0.0:8001"
    ]
    
    for url in localhost_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/healthz")
                if response.status_code == 200:
                    print(f"   ✅ {url} - REACHABLE")
                    results["mcp_server_reachable"] = True
                    results["recommended_url"] = url
                else:
                    print(f"   ❌ {url} - Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {url} - Error: {type(e).__name__}")
    
    # 3. Check if port 8001 is listening
    print(f"\n3. Checking port 8001 status...")
    try:
        # Try to connect to port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 8001))
        sock.close()
        
        if result == 0:
            print(f"   ✅ Port 8001 is open and listening")
            results["port_accessible"] = True
        else:
            print(f"   ❌ Port 8001 is not accessible (error code: {result})")
    except Exception as e:
        print(f"   ❌ Port check failed: {e}")
    
    # 4. Check for MCP server process
    print(f"\n4. Checking MCP server process...")
    try:
        # Check for python process with MCP-related keywords
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=10)
        processes = result.stdout
        
        mcp_processes = []
        for line in processes.split('\n'):
            if any(keyword in line.lower() for keyword in ['mcp', 'atlassian', '8001']):
                mcp_processes.append(line.strip())
        
        if mcp_processes:
            print(f"   ✅ Found {len(mcp_processes)} related processes:")
            for proc in mcp_processes[:3]:  # Show first 3
                print(f"     {proc}")
            results["process_running"] = True
        else:
            print(f"   ❌ No MCP server processes found")
            
    except Exception as e:
        print(f"   ❌ Process check failed: {e}")
    
    # 5. Network interface check
    print(f"\n5. Network interface diagnosis...")
    try:
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=10)
        netstat_output = result.stdout
        
        port_8001_lines = [line for line in netstat_output.split('\n') if '8001' in line]
        
        if port_8001_lines:
            print(f"   ✅ Port 8001 network binding found:")
            for line in port_8001_lines:
                print(f"     {line.strip()}")
        else:
            print(f"   ❌ Port 8001 not found in network bindings")
            
    except Exception as e:
        print(f"   ❌ Network interface check failed: {e}")
    
    # 6. Environment-specific recommendations
    print(f"\n6. Deployment Recommendations:")
    
    if results["mcp_server_reachable"]:
        print(f"   ✅ MCP server is reachable at: {results['recommended_url']}")
        print(f"   📝 Use: export MCP_SERVER_URL='{results['recommended_url']}'")
    else:
        print(f"   ❌ MCP server not reachable via localhost")
        print(f"   🔧 Deployment fixes needed:")
        
        # Check if we're in a container environment
        if os.path.exists('/.dockerenv'):
            print(f"     - Detected Docker environment")
            print(f"     - Try: export MCP_SERVER_URL='http://mcp-atlassian:8001'")
            print(f"     - Or:  export MCP_SERVER_URL='http://host.docker.internal:8001'")
        
        # Check for common cloud deployment indicators
        if any(key in os.environ for key in ['REPLIT_CLUSTER', 'RAILWAY_ENVIRONMENT', 'HEROKU_APP_NAME']):
            print(f"     - Detected cloud deployment environment")
            print(f"     - MCP server may need to run as separate service")
            print(f"     - Check service mesh/networking configuration")
        
        print(f"     - Ensure MCP server is running and accessible")
        print(f"     - Check firewall/security group settings")
        print(f"     - Verify container networking configuration")
    
    return results

async def test_mcp_url_options():
    """Test various MCP URL options for deployment"""
    
    print(f"\n🧪 TESTING MCP URL OPTIONS")
    print("=" * 60)
    
    # Common deployment URL patterns
    test_urls = [
        "http://localhost:8001",
        "http://127.0.0.1:8001", 
        "http://0.0.0.0:8001",
        "http://mcp-atlassian:8001",
        "http://mcp-server:8001",
        "http://host.docker.internal:8001"
    ]
    
    working_urls = []
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{url}/healthz")
                if response.status_code == 200:
                    print(f"   ✅ SUCCESS - {response.text}")
                    working_urls.append(url)
                else:
                    print(f"   ❌ HTTP {response.status_code}")
        except httpx.ConnectError:
            print(f"   ❌ Connection failed")
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}")
    
    if working_urls:
        print(f"\n✅ WORKING URLs FOUND:")
        for url in working_urls:
            print(f"   {url}")
        print(f"\n📝 Recommended environment variable:")
        print(f"   export MCP_SERVER_URL='{working_urls[0]}'")
    else:
        print(f"\n❌ NO WORKING URLs FOUND")
        print(f"   MCP server is not accessible from this environment")
    
    return working_urls

if __name__ == "__main__":
    async def main():
        results = await diagnose_deployment_network()
        working_urls = await test_mcp_url_options()
        
        print(f"\n" + "=" * 60)
        print(f"DEPLOYMENT DIAGNOSIS COMPLETE")
        print(f"=" * 60)
        
        if working_urls:
            print(f"✅ MCP server connectivity: WORKING")
            print(f"📝 Set: export MCP_SERVER_URL='{working_urls[0]}'")
        else:
            print(f"❌ MCP server connectivity: FAILED")
            print(f"🔧 Deployment networking configuration required")
    
    asyncio.run(main())