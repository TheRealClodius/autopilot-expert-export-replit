#!/usr/bin/env python3
"""
Check MCP server credential status
"""
import asyncio
import httpx
import json

async def check_mcp_status():
    """Check if MCP server has proper credentials"""
    
    mcp_url = "https://remote-mcp-server-andreiclodius.replit.app"
    
    print("🔍 CHECKING MCP SERVER CREDENTIAL STATUS")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Check Atlassian status
        try:
            status_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_atlassian_status",
                    "arguments": {}
                }
            }
            
            response = await client.post(
                f"{mcp_url}/mcp",
                json=status_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status check response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Full status response:")
                print(json.dumps(data, indent=2))
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Error checking status: {e}")

if __name__ == "__main__":
    asyncio.run(check_mcp_status())