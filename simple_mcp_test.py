import httpx
import asyncio

async def test():
    url = "https://dcbe13eb4daf-5000.proxy.replit.dev"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test root endpoint
            response = await client.get(url)
            print(f"Root: {response.status_code}")
            
            # Test health endpoint
            response = await client.get(f"{url}/healthz")
            print(f"Health: {response.status_code}")
            print(f"Text: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())