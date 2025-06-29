#!/usr/bin/env python3
"""
Simple test to verify Confluence API connection works with provided credentials
"""

import asyncio
import httpx
import os
from config import settings

async def test_confluence_connection():
    """Test direct connection to Confluence API"""
    
    print("🔗 Testing Confluence API connection...")
    
    # Get credentials
    confluence_url = settings.ATLASSIAN_CONFLUENCE_URL
    confluence_username = settings.ATLASSIAN_CONFLUENCE_USERNAME  
    confluence_token = settings.ATLASSIAN_CONFLUENCE_TOKEN
    
    print(f"   Confluence URL: {confluence_url}")
    print(f"   Username: {confluence_username}")
    print(f"   Token: {'*' * 20}...{confluence_token[-4:] if confluence_token else 'NOT SET'}")
    
    if not all([confluence_url, confluence_username, confluence_token]):
        print("❌ Missing credentials")
        return
    
    try:
        # Build API URL for search
        base_url = confluence_url.rstrip('/wiki')
        search_url = f"{base_url}/wiki/rest/api/content/search"
        
        # Search parameters
        params = {
            "cql": "title ~ 'UX Audit Evaluation Template'",
            "limit": 5,
            "expand": "version,space,history"
        }
        
        # Authentication
        auth = (confluence_username, confluence_token)
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        print(f"🔍 Searching for 'UX Audit Evaluation Template'...")
        print(f"   URL: {search_url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                search_url,
                params=params,
                headers=headers,
                auth=auth
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])
                
                print(f"✅ Search successful! Found {len(results)} results")
                
                for i, page in enumerate(results, 1):
                    print(f"\n   Result {i}:")
                    print(f"      Title: {page.get('title', 'N/A')}")
                    print(f"      Type: {page.get('type', 'N/A')}")
                    print(f"      Space: {page.get('space', {}).get('name', 'N/A')}")
                    
                    # Check version/history for author info
                    version = page.get('version', {})
                    history = page.get('history', {})
                    
                    if version:
                        author = version.get('by', {}).get('displayName', 'Unknown')
                        print(f"      Last modified by: {author}")
                    
                    if history:
                        creator = history.get('createdBy', {}).get('displayName', 'Unknown')
                        print(f"      Created by: {creator}")
                    
                    # Check if this is the UX Audit template
                    title = page.get('title', '').lower()
                    if 'ux audit' in title and ('template' in title or 'evaluation' in title):
                        print(f"🎯 FOUND TARGET DOCUMENT!")
                        
                        owner = author if version else creator if history else 'Unknown'
                        print(f"      Document owner: {owner}")
                        
                        if 'mausam' in owner.lower():
                            print("🎉 SUCCESS: Found Mausam Jain as expected!")
                        else:
                            print(f"⚠️  Expected Mausam Jain, found: {owner}")
                            
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_confluence_connection())