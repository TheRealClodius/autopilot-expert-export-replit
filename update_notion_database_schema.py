#!/usr/bin/env python3
"""
Update Notion database to match our embedding pipeline schema.
"""
import os
from notion_client import Client
from notion_client.errors import APIResponseError

def update_database_schema():
    """Add the required fields to the existing database."""
    print("=== Updating Notion Database Schema ===")
    
    integration_secret = os.getenv("NOTION_INTEGRATION_SECRET", "")
    database_id = os.getenv("NOTION_DATABASE_ID", "")
    
    if not integration_secret or not database_id:
        print("Missing credentials")
        return
    
    try:
        client = Client(auth=integration_secret)
        
        # Define the schema we need
        new_properties = {
            "Run ID": {
                "title": {}  # This will replace Name as the title field
            },
            "Timestamp": {
                "date": {}
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "Success", "color": "green"},
                        {"name": "Failed", "color": "red"},
                        {"name": "Running", "color": "yellow"},
                        {"name": "Partial", "color": "orange"}
                    ]
                }
            },
            "Channels Checked": {
                "number": {}
            },
            "Messages Embedded": {
                "number": {}
            },
            "Duration (seconds)": {
                "number": {}
            },
            "Trigger Type": {
                "select": {
                    "options": [
                        {"name": "Manual via Notion Dashboard", "color": "blue"},
                        {"name": "Hourly Automatic", "color": "default"},
                        {"name": "Manual via API", "color": "purple"}
                    ]
                }
            },
            "Errors": {
                "rich_text": {}
            }
        }
        
        print("Updating database schema...")
        
        # Update the database with new properties
        response = client.databases.update(
            database_id=database_id,
            properties=new_properties
        )
        
        print("✅ Database schema updated successfully!")
        print("New fields added:")
        for field_name in new_properties.keys():
            print(f"  - {field_name}")
        
        return True
        
    except APIResponseError as e:
        print(f"API error: {e}")
        print(f"Status: {e.status}")
        if e.status == 400:
            print("This might be because the integration doesn't have permission to modify the database schema.")
            print("Try adding the fields manually instead.")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    update_database_schema()