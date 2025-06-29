import httpx
import asyncio

async def test():
    url = "https://remote-mcp-server-andreiclodius.replit.app"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test root endpoint
            response = await client.get(url)
            print(f"Root: {response.status_code}")
            
            # Test different health endpoints
            endpoints = ["/health", "/sse", "/mcp", "/mcp/sse"]
            for endpoint in endpoints:
                try:
                    response = await client.get(f"{url}{endpoint}")
                    print(f"{endpoint}: {response.status_code}")
                    if response.status_code == 200:
                        print(f"  Content: {response.text[:100]}...")
                except Exception as e:
                    print(f"{endpoint}: Error - {e}")
            
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())