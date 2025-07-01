#!/usr/bin/env python3
"""
Fix the Notion database schema to work with the current database structure.
"""
import os
from notion_client import Client
from notion_client.errors import APIResponseError

def fix_database_schema():
    """Fix database schema to work with simple Name field."""
    print("=== Fixing Notion Database Schema ===")
    
    # Get credentials
    integration_secret = os.getenv("NOTION_INTEGRATION_SECRET", "")
    database_id = os.getenv("NOTION_DATABASE_ID", "")
    
    if not integration_secret or not database_id:
        print("❌ Missing credentials")
        return
    
    try:
        client = Client(auth=integration_secret)
        
        # First, let's see what the current database structure looks like
        print("🔄 Checking current database structure...")
        database_info = client.databases.retrieve(database_id=database_id)
        
        current_properties = database_info.get("properties", {})
        print(f"Current fields in database: {list(current_properties.keys())}")
        
        # Create a simple test entry using just the Name field
        print("🔄 Creating test entry with current structure...")
        
        test_properties = {}
        
        # If there's a Name field, use it
        if "Name" in current_properties:
            test_properties["Name"] = {
                "title": [{"text": {"content": "Test Embedding Run - 2025-07-01 11:21"}}]
            }
        
        # If there are other existing fields, try to populate them
        for field_name, field_config in current_properties.items():
            field_type = field_config.get("type")
            if field_name == "Name":
                continue  # Already handled
            
            print(f"Found field: {field_name} (type: {field_type})")
            
            if field_type == "select":
                # For select fields, use the first option or create a default
                options = field_config.get("select", {}).get("options", [])
                if options:
                    test_properties[field_name] = {"select": {"name": options[0]["name"]}}
                else:
                    test_properties[field_name] = {"select": {"name": "Success"}}
            elif field_type == "number":
                test_properties[field_name] = {"number": 0}
            elif field_type == "rich_text":
                test_properties[field_name] = {"rich_text": [{"text": {"content": "Test run"}}]}
            elif field_type == "date":
                test_properties[field_name] = {"date": {"start": "2025-07-01T11:21:00"}}
        
        # Create the test page
        response = client.pages.create(
            parent={"database_id": database_id},
            properties=test_properties
        )
        
        page_id = response["id"]
        print(f"✅ Successfully created test page: {page_id}")
        print("🎉 Check your Notion database - you should see the test entry!")
        
    except APIResponseError as e:
        print(f"❌ Notion API error: {e}")
        print(f"Status: {e.status}")
        print(f"Code: {e.code}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    fix_database_schema()