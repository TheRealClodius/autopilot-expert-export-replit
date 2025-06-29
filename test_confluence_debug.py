#!/usr/bin/env python3
"""
Debug Confluence Page Access Issues
"""
import asyncio
import httpx
import time
from config import settings

async def debug_confluence_access():
    """Debug specific Confluence access issues"""
    
    print("🔍 DEBUGGING CONFLUENCE PAGE ACCESS")
    print("="*50)
    
    # Get credentials
    confluence_url = settings.ATLASSIAN_CONFLUENCE_URL
    confluence_username = settings.ATLASSIAN_CONFLUENCE_USERNAME  
    confluence_token = settings.ATLASSIAN_CONFLUENCE_TOKEN
    
    print(f"Confluence URL: {confluence_url}")
    print(f"Username: {confluence_username}")
    print(f"Token: {'*' * 20}...{confluence_token[-4:] if confluence_token else 'NOT SET'}")
    
    if not all([confluence_url, confluence_username, confluence_token]):
        print("❌ Missing credentials - cannot test")
        return
    
    # Test 1: Basic connection test
    print("\n🧪 TEST 1: Basic API Connection")
    try:
        base_url = confluence_url.rstrip('/wiki')
        auth = (confluence_username, confluence_token)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Test basic connection
        test_url = f"{base_url}/wiki/rest/api/space"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(test_url, headers=headers, auth=auth)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("✅ Basic connection successful")
            else:
                print(f"❌ Connection failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    # Test 2: Simple search test
    print("\n🧪 TEST 2: Simple Search Test")
    try:
        search_url = f"{base_url}/wiki/rest/api/content/search"
        
        # Simple CQL query
        params = {
            "cql": "type=page",
            "limit": 1,
            "expand": "space,version"
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                search_url,
                params=params,
                headers=headers,
                auth=auth
            )
            
            elapsed = time.time() - start_time
            
            print(f"Status: {response.status_code}")
            print(f"Time: {elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Search successful - found {data.get('totalSize', 0)} results")
                if data.get('results'):
                    first_result = data['results'][0]
                    print(f"First result: {first_result.get('title', 'No title')}")
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Search error: {e}")
    
    # Test 3: Complex CQL query (what might be failing)
    print("\n🧪 TEST 3: Complex CQL Query Test")
    try:
        # Test the type of query that might be causing issues
        params = {
            "cql": "title ~ 'template'",
            "limit": 5,
            "expand": "space,version,history"
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                search_url,
                params=params,
                headers=headers,
                auth=auth
            )
            
            elapsed = time.time() - start_time
            
            print(f"Status: {response.status_code}")
            print(f"Time: {elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Complex search successful - found {data.get('totalSize', 0)} results")
            else:
                print(f"❌ Complex search failed: {response.status_code}")
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Complex search error: {e}")
    
    # Test 4: Get specific page (if we have one)
    print("\n🧪 TEST 4: Get Specific Page Test")
    try:
        # Try to get any page by ID
        page_url = f"{base_url}/wiki/rest/api/content"
        
        params = {
            "limit": 1,
            "expand": "space,version,body.storage"
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                page_url,
                params=params,
                headers=headers,
                auth=auth
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    page = data['results'][0]
                    page_id = page.get('id')
                    
                    # Now try to get this specific page
                    specific_url = f"{base_url}/wiki/rest/api/content/{page_id}"
                    specific_params = {"expand": "space,version,body.storage,history"}
                    
                    response2 = await client.get(
                        specific_url,
                        params=specific_params,
                        headers=headers,
                        auth=auth
                    )
                    
                    print(f"Specific page status: {response2.status_code}")
                    
                    if response2.status_code == 200:
                        print("✅ Specific page access successful")
                    else:
                        print(f"❌ Specific page access failed: {response2.status_code}")
                        print(f"Error: {response2.text}")
                        
            else:
                print(f"❌ Page listing failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Page access error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_confluence_access())