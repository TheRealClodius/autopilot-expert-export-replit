#!/usr/bin/env python3
"""
Test basic Microsoft Graph access to see what's available without admin consent
"""
import asyncio
import sys
import os
import httpx

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def test_basic_access():
    """Test what we can access without admin consent"""
    print("Testing basic Microsoft Graph access...")
    
    # Get access token
    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    async with httpx.AsyncClient() as client:
        # Get token
        token_response = await client.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            print(f"Authentication failed: {token_response.text}")
            return
        
        access_token = token_response.json().get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Test different endpoints to see what works
        endpoints_to_test = [
            ("Application Info", "https://graph.microsoft.com/v1.0/applications"),
            ("Service Principals", "https://graph.microsoft.com/v1.0/servicePrincipals"),
            ("Organization Info", "https://graph.microsoft.com/v1.0/organization"),
            ("Directory Objects", "https://graph.microsoft.com/v1.0/directoryObjects"),
            ("Users (limited)", "https://graph.microsoft.com/v1.0/users?$top=1"),
            ("Current App", f"https://graph.microsoft.com/v1.0/applications/{settings.MICROSOFT_CLIENT_ID}"),
        ]
        
        for name, endpoint in endpoints_to_test:
            try:
                response = await client.get(endpoint, headers=headers)
                status = response.status_code
                
                if status == 200:
                    data = response.json()
                    if 'value' in data:
                        count = len(data['value'])
                        print(f"✅ {name}: Success ({count} items)")
                    else:
                        print(f"✅ {name}: Success (single item)")
                elif status == 403:
                    print(f"🔒 {name}: Insufficient privileges")
                elif status == 404:
                    print(f"❓ {name}: Not found")
                else:
                    print(f"❌ {name}: Failed ({status})")
                    
            except Exception as e:
                print(f"❌ {name}: Error - {e}")
        
        # Test what current application permissions are
        print("\nTesting current application permissions...")
        try:
            # Get service principal for our app
            sp_response = await client.get(
                f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{settings.MICROSOFT_CLIENT_ID}'",
                headers=headers
            )
            
            if sp_response.status_code == 200:
                sp_data = sp_response.json()
                if sp_data.get('value'):
                    sp = sp_data['value'][0]
                    print(f"✅ Found service principal: {sp.get('displayName')}")
                    
                    # Get app role assignments
                    sp_id = sp.get('id')
                    roles_response = await client.get(
                        f"https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/appRoleAssignments",
                        headers=headers
                    )
                    
                    if roles_response.status_code == 200:
                        roles_data = roles_response.json()
                        assignments = roles_data.get('value', [])
                        print(f"Current permissions ({len(assignments)}):")
                        for assignment in assignments:
                            print(f"  - {assignment.get('principalDisplayName', 'Unknown')}")
                    else:
                        print(f"Could not get permissions: {roles_response.status_code}")
                else:
                    print("Service principal not found")
            else:
                print(f"Could not get service principal: {sp_response.status_code}")
                
        except Exception as e:
            print(f"Error checking permissions: {e}")

if __name__ == "__main__":
    asyncio.run(test_basic_access())