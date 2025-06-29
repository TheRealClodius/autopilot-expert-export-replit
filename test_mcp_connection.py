#!/usr/bin/env python3
"""
Test MCP server connection with the updated URL
"""

import asyncio
import httpx
import sys

# Add project root to path
sys.path.append('.')

from config import Settings

async def test_mcp_connection():
    """Test connection to the updated MCP server"""
    
    settings = Settings()
    mcp_url = settings.DEPLOYMENT_AWARE_MCP_URL
    
    print(f"Testing MCP server connection...")
    print(f"MCP Server URL: {mcp_url}")
    print("-" * 50)
    
    # Test different endpoints
    endpoints_to_test = [
        "/healthz",
        "/health", 
        "/",
        "/mcp",
        "/mcp/sse"
    ]
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for endpoint in endpoints_to_test:
            url = f"{mcp_url}{endpoint}"
            try:
                print(f"Testing: {url}")
                response = await client.get(url)
                print(f"  Status: {response.status_code}")
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        data = response.json()
                        print(f"  JSON: {data}")
                    except:
                        print(f"  Text: {response.text[:100]}...")
                else:
                    print(f"  Text: {response.text[:100]}...")
                print()
            except Exception as e:
                print(f"  Error: {e}")
                print()

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())