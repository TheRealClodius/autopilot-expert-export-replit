#!/usr/bin/env python3
"""
Test what's available with User.Read permission (not User.Read.All)
"""
import asyncio
import sys
import os
import httpx

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def test_user_read_only():
    """Test User.Read permission capabilities"""
    print("Testing User.Read permission capabilities...")
    
    # Get access token
    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            print(f"Authentication failed: {token_response.text}")
            return
        
        access_token = token_response.json().get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # With User.Read (not All), we can typically only access:
        # - Current application's own profile
        # - Basic organization info (sometimes)
        # - Service account's own information
        
        test_endpoints = [
            ("Current App Profile", "https://graph.microsoft.com/v1.0/me"),
            ("Organization Info", "https://graph.microsoft.com/v1.0/organization"),
            ("Application Info", f"https://graph.microsoft.com/v1.0/applications/{settings.MICROSOFT_CLIENT_ID}"),
            ("Service Principal", f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{settings.MICROSOFT_CLIENT_ID}'"),
            ("Users Endpoint", "https://graph.microsoft.com/v1.0/users?$top=1"),
            ("Directory Roles", "https://graph.microsoft.com/v1.0/directoryRoles"),
        ]
        
        working_endpoints = []
        
        for name, endpoint in test_endpoints:
            try:
                response = await client.get(endpoint, headers=headers)
                status = response.status_code
                
                if status == 200:
                    data = response.json()
                    working_endpoints.append((name, endpoint, data))
                    
                    if 'value' in data:
                        count = len(data['value'])
                        print(f"✅ {name}: Success ({count} items)")
                        
                        # Show sample data for working endpoints
                        if count > 0:
                            sample = data['value'][0]
                            if 'displayName' in sample:
                                print(f"   Sample: {sample.get('displayName')}")
                    else:
                        print(f"✅ {name}: Success (single item)")
                        if 'displayName' in data:
                            print(f"   Name: {data.get('displayName')}")
                        if 'mail' in data:
                            print(f"   Email: {data.get('mail')}")
                            
                elif status == 403:
                    print(f"🔒 {name}: Insufficient privileges")
                elif status == 404:
                    print(f"❓ {name}: Not found")
                else:
                    print(f"❌ {name}: Failed ({status})")
                    
            except Exception as e:
                print(f"❌ {name}: Error - {str(e)}")
        
        # If any endpoints work, let's explore what data we can get
        if working_endpoints:
            print(f"\nFound {len(working_endpoints)} working endpoints. Exploring available data...")
            
            for name, endpoint, data in working_endpoints:
                print(f"\n--- {name} ---")
                if 'value' in data:
                    # Multiple items
                    for item in data['value'][:2]:  # Show first 2 items
                        relevant_fields = {k: v for k, v in item.items() 
                                         if k in ['id', 'displayName', 'mail', 'userPrincipalName', 
                                                'jobTitle', 'department', 'appId', 'servicePrincipalType']}
                        for k, v in relevant_fields.items():
                            print(f"  {k}: {v}")
                        print()
                else:
                    # Single item
                    relevant_fields = {k: v for k, v in data.items() 
                                     if k in ['id', 'displayName', 'mail', 'userPrincipalName', 
                                            'jobTitle', 'department', 'appId', 'servicePrincipalType']}
                    for k, v in relevant_fields.items():
                        print(f"  {k}: {v}")
        
        else:
            print("\nNo working endpoints found with current permissions.")
            print("User.Read permission may only work with delegated (user) authentication,")
            print("not application (service-to-service) authentication.")

if __name__ == "__main__":
    asyncio.run(test_user_read_only())