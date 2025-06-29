#!/usr/bin/env python3
"""
Test MCP with SSE Transport Mode
"""

import asyncio
import logging
import sys
import subprocess
import time
import httpx
from tools.atlassian_tool import AtlassianTool

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_mcp_sse():
    """Test MCP using SSE transport mode"""
    print("🔧 TESTING MCP WITH SSE TRANSPORT")
    print("=" * 50)
    
    import os
    
    # Start MCP server with SSE transport using environment variables
    env_vars = {
        "JIRA_URL": os.getenv("ATLASSIAN_JIRA_URL", ""),
        "JIRA_USERNAME": os.getenv("ATLASSIAN_JIRA_USERNAME", ""),
        "JIRA_API_TOKEN": os.getenv("ATLASSIAN_JIRA_TOKEN", ""),
        "CONFLUENCE_URL": os.getenv("ATLASSIAN_CONFLUENCE_URL", ""),
        "CONFLUENCE_USERNAME": os.getenv("ATLASSIAN_CONFLUENCE_USERNAME", ""), 
        "CONFLUENCE_API_TOKEN": os.getenv("ATLASSIAN_CONFLUENCE_TOKEN", ""),
        "TRANSPORT": "sse",
        "PORT": "8000",
        "HOST": "0.0.0.0",
        "MCP_VERBOSE": "true"
    }
    
    if not all([env_vars["JIRA_URL"], env_vars["JIRA_USERNAME"], env_vars["JIRA_API_TOKEN"]]):
        print("❌ Missing Atlassian credentials in environment variables")
        return {"error": "missing_credentials"}
    
    print("🚀 Starting MCP server with SSE transport...")
    
    # Start the server in background
    server_process = subprocess.Popen(
        ["uvx", "mcp-atlassian"],
        env=env_vars,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server to start
        await asyncio.sleep(10)
        
        print("📡 Testing SSE endpoint...")
        
        # Test connection to SSE endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get("http://localhost:8000/health")
                print(f"Health check: {response.status_code}")
                
                # Try to make a simple API call
                search_payload = {
                    "method": "tools/call",
                    "params": {
                        "name": "confluence_search",
                        "arguments": {"query": "template", "limit": 1}
                    }
                }
                
                response = await client.post(
                    "http://localhost:8000/mcp",
                    json=search_payload
                )
                
                print(f"Search response: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ SSE Result: {result}")
                    return result
                else:
                    print(f"❌ Error: {response.text}")
                    return {"error": f"HTTP {response.status_code}"}
                    
            except Exception as e:
                print(f"❌ SSE connection error: {e}")
                return {"error": str(e)}
    
    finally:
        # Cleanup server
        print("🧹 Cleaning up server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

if __name__ == "__main__":
    result = asyncio.run(test_mcp_sse())
    print(f"\nFinal result: {result}")