#!/usr/bin/env python3
"""
Debug Microsoft Graph authentication
"""
import asyncio
import sys
import os
import httpx

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def debug_authentication():
    """Debug the authentication flow step by step"""
    print("🔍 Debugging Microsoft Graph authentication...")
    
    # Check credentials
    print(f"Client ID: {settings.MICROSOFT_CLIENT_ID[:8]}..." if settings.MICROSOFT_CLIENT_ID else "❌ Missing")
    print(f"Tenant ID: {settings.MICROSOFT_TENANT_ID[:8]}..." if settings.MICROSOFT_TENANT_ID else "❌ Missing")
    print(f"Client Secret: {'✅ Present' if settings.MICROSOFT_CLIENT_SECRET else '❌ Missing'}")
    
    if not all([settings.MICROSOFT_CLIENT_ID, settings.MICROSOFT_CLIENT_SECRET, settings.MICROSOFT_TENANT_ID]):
        print("❌ Missing required credentials")
        return
    
    # Test OAuth endpoint
    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    print(f"\n🔗 Token URL: {token_url}")
    
    # Prepare OAuth request
    token_data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    print("\n📡 Making OAuth request...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                token_response = response.json()
                print("✅ Authentication successful!")
                print(f"Token Type: {token_response.get('token_type')}")
                print(f"Expires In: {token_response.get('expires_in')} seconds")
                print(f"Scope: {token_response.get('scope')}")
                
                # Test a simple API call
                access_token = token_response.get('access_token')
                if access_token:
                    print("\n🧪 Testing API call...")
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                    
                    # Try the simplest possible call
                    api_response = await client.get(
                        "https://graph.microsoft.com/v1.0/users?$top=1",
                        headers=headers
                    )
                    
                    print(f"API Status: {api_response.status_code}")
                    if api_response.status_code == 200:
                        print("✅ API call successful!")
                        users = api_response.json().get('value', [])
                        if users:
                            user = users[0]
                            print(f"Sample user: {user.get('displayName')} ({user.get('mail')})")
                    else:
                        print(f"❌ API call failed: {api_response.text}")
                        
            else:
                print(f"❌ Authentication failed: {response.text}")
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                print(f"Error: {error_data.get('error', 'Unknown')}")
                print(f"Description: {error_data.get('error_description', 'No description')}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print("\n✨ Authentication debug completed!")

if __name__ == "__main__":
    asyncio.run(debug_authentication())