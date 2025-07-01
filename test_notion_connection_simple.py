#!/usr/bin/env python3
"""
Simple Notion connection test to diagnose the issue.
"""
import os
from notion_client import Client
from notion_client.errors import APIResponseError

def test_notion_simple():
    """Test basic Notion connection and permissions."""
    print("=== Simple Notion Connection Test ===")
    
    # Get credentials
    integration_secret = os.getenv("NOTION_INTEGRATION_SECRET", "")
    database_id = os.getenv("NOTION_DATABASE_ID", "")
    
    print(f"Integration Secret present: {bool(integration_secret)}")
    print(f"Integration Secret length: {len(integration_secret) if integration_secret else 0}")
    print(f"Database ID: {database_id}")
    print(f"Database ID length: {len(database_id)}")
    print()
    
    if not integration_secret or not database_id:
        print("❌ Missing credentials")
        return
    
    try:
        # Test 1: Create client
        print("🔄 Creating Notion client...")
        client = Client(auth=integration_secret)
        print("✅ Client created successfully")
        print()
        
        # Test 2: Basic API test (list users - should work with any valid token)
        print("🔄 Testing basic API access...")
        try:
            users = client.users.list()
            print(f"✅ Basic API works - found {len(users.get('results', []))} users")
        except APIResponseError as e:
            print(f"❌ Basic API failed: {e}")
            print("This means the token itself is invalid")
            return
        print()
        
        # Test 3: Database access
        print("🔄 Testing database access...")
        try:
            response = client.databases.query(database_id=database_id, page_size=1)
            print("✅ Database access successful!")
            print(f"Database has {len(response.get('results', []))} items")
        except APIResponseError as e:
            print(f"❌ Database access failed: {e}")
            if e.status == 401:
                print("💡 This means the integration is not connected to this database")
                print("   Go to your database → ... → Connections → Add your integration")
            elif e.status == 404:
                print("💡 Database not found - check the database ID")
            return
        print()
        
        print("🎉 All tests passed! Notion integration is working correctly.")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_notion_simple()