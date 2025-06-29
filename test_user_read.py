#!/usr/bin/env python3
"""
Test Microsoft Graph User.Read.All capabilities
"""
import asyncio
import sys
import os
import httpx

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.outlook_meeting import OutlookMeetingTool

async def test_user_read_capabilities():
    """Test what we can access with User.Read.All permission"""
    print("🔍 Testing User.Read.All capabilities...")
    
    # Initialize the tool to get access token
    outlook_tool = OutlookMeetingTool()
    
    if not outlook_tool.available:
        print("❌ Outlook tool not available")
        return
    
    # Get access token
    access_token = await outlook_tool._get_access_token()
    if not access_token:
        print("❌ Could not get access token")
        return
    
    print("✅ Access token obtained successfully")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Get current user profile
    print("\n👤 Test 1: Get current user profile")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Current user: {user_data.get('displayName')} ({user_data.get('mail')})")
                print(f"   Job Title: {user_data.get('jobTitle', 'N/A')}")
                print(f"   Department: {user_data.get('department', 'N/A')}")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Search for Liz Holz in directory
    print("\n🔍 Test 2: Search for Liz Holz in directory")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/users?$filter=displayName eq 'Liz Holz'",
                headers=headers
            )
            if response.status_code == 200:
                users_data = response.json()
                users = users_data.get('value', [])
                if users:
                    for user in users:
                        print(f"✅ Found: {user.get('displayName')} ({user.get('mail')})")
                        print(f"   Job Title: {user.get('jobTitle', 'N/A')}")
                        print(f"   Department: {user.get('department', 'N/A')}")
                else:
                    print("ℹ️ No user found with exact name 'Liz Holz'")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Search for users with "Liz" in name
    print("\n🔍 Test 3: Search for users with 'Liz' in name")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/users?$filter=startswith(displayName,'Liz')",
                headers=headers
            )
            if response.status_code == 200:
                users_data = response.json()
                users = users_data.get('value', [])
                if users:
                    print(f"✅ Found {len(users)} user(s) with 'Liz' in name:")
                    for user in users:
                        print(f"   • {user.get('displayName')} ({user.get('mail')})")
                        print(f"     Title: {user.get('jobTitle', 'N/A')}")
                else:
                    print("ℹ️ No users found with 'Liz' in name")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: List first few users in directory
    print("\n📋 Test 4: List first 5 users in directory")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/users?$top=5",
                headers=headers
            )
            if response.status_code == 200:
                users_data = response.json()
                users = users_data.get('value', [])
                print(f"✅ Found {len(users)} users:")
                for user in users:
                    print(f"   • {user.get('displayName')} ({user.get('mail')})")
                    print(f"     Title: {user.get('jobTitle', 'N/A')}")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✨ User.Read.All test completed!")

if __name__ == "__main__":
    asyncio.run(test_user_read_capabilities())