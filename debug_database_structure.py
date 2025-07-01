"""
Debug script to inspect the actual database structure and field types.
"""
import os
import json
from notion_client import Client

def debug_database_structure():
    """Debug the actual database structure to understand field types."""
    
    # Initialize Notion client
    notion_secret = os.getenv("NOTION_INTEGRATION_SECRET")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_secret or not database_id:
        print("Missing environment variables:")
        print(f"NOTION_INTEGRATION_SECRET: {'✓' if notion_secret else '✗'}")
        print(f"NOTION_DATABASE_ID: {'✓' if database_id else '✗'}")
        return
    
    client = Client(auth=notion_secret)
    
    try:
        # Get database structure
        print("=== DATABASE STRUCTURE ===")
        db_response = client.databases.retrieve(database_id=database_id)
        properties = db_response.get("properties", {})
        
        print(f"Database Title: {db_response.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
        print(f"Properties Found: {len(properties)}")
        
        for prop_name, prop_details in properties.items():
            print(f"  - {prop_name}: {prop_details.get('type', 'unknown')}")
        
        # Get recent entries to see actual data structure
        print("\n=== RECENT ENTRIES ===")
        query_response = client.databases.query(
            database_id=database_id,
            page_size=3
        )
        
        print(f"Total entries: {len(query_response.get('results', []))}")
        
        for i, page in enumerate(query_response.get('results', [])[:2]):
            print(f"\n--- Entry {i+1} ---")
            print(f"Page ID: {page['id']}")
            
            for prop_name, prop_data in page.get('properties', {}).items():
                print(f"{prop_name}: {json.dumps(prop_data, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_database_structure()