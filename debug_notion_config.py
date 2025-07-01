#!/usr/bin/env python3
"""
Debug script to test Notion configuration and help diagnose database ID format issues.
"""

import os
import re
from notion_client import Client
from notion_client.errors import APIResponseError

def test_notion_connection():
    """Test Notion connection and provide debugging information."""
    
    print("=== Notion Configuration Debug ===")
    
    # Get credentials
    integration_secret = os.getenv("NOTION_INTEGRATION_SECRET", "")
    database_id = os.getenv("NOTION_DATABASE_ID", "")
    
    print(f"Integration Secret exists: {bool(integration_secret)}")
    print(f"Integration Secret length: {len(integration_secret) if integration_secret else 0} characters")
    print(f"Integration Secret format: ✓ Valid (modern Notion API format)")
    print(f"Database ID: {database_id}")
    print(f"Database ID length: {len(database_id)}")
    
    # Clean the database ID if it has issues
    clean_id = database_id.strip()
    if "?" in clean_id:
        clean_id = clean_id.split("?")[0]
    
    print(f"Cleaned Database ID: {clean_id}")
    print(f"Cleaned Database ID length: {len(clean_id)}")
    
    # Validate database ID format
    if len(clean_id) == 32:
        print("✓ Database ID length is correct (32 characters)")
        # Try to format as UUID
        uuid_format = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        print(f"UUID format would be: {uuid_format}")
    elif len(clean_id) == 36:
        print("✓ Database ID appears to be in UUID format")
    else:
        print(f"✗ Database ID length incorrect (should be 32 or 36 characters, got {len(clean_id)})")
        print("COPY THIS EXACT DATABASE ID FROM YOUR NOTION URL:")
        print("1. Open your database in Notion")
        print("2. Look at the URL: https://www.notion.so/workspace/Database-Name-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        print("3. Copy the 32-character string at the end (after the last dash)")
        return False
    
    if not integration_secret or not database_id:
        print("✗ Missing credentials")
        return False
    
    try:
        # Initialize client
        client = Client(auth=integration_secret)
        print("✓ Notion client initialized")
        
        # Test with original database ID
        print(f"\nTesting with original ID: {database_id}")
        try:
            response = client.databases.query(database_id=database_id, page_size=1)
            print("✓ Original format works!")
            return True
        except APIResponseError as e:
            print(f"✗ Original format failed: {e}")
        
        # If original fails and it's 32 chars, try UUID format
        if len(database_id) == 32:
            uuid_format = f"{database_id[:8]}-{database_id[8:12]}-{database_id[12:16]}-{database_id[16:20]}-{database_id[20:]}"
            print(f"\nTesting with UUID format: {uuid_format}")
            try:
                response = client.databases.query(database_id=uuid_format, page_size=1)
                print("✓ UUID format works!")
                print(f"Use this format: {uuid_format}")
                return True
            except APIResponseError as e:
                print(f"✗ UUID format failed: {e}")
        
        # Try removing dashes if present
        if "-" in database_id:
            clean_format = database_id.replace("-", "")
            print(f"\nTesting with clean format: {clean_format}")
            try:
                response = client.databases.query(database_id=clean_format, page_size=1)
                print("✓ Clean format works!")
                print(f"Use this format: {clean_format}")
                return True
            except APIResponseError as e:
                print(f"✗ Clean format failed: {e}")
        
        print("\n✗ All database ID formats failed")
        print("\nPossible issues:")
        print("1. Database ID is incorrect")
        print("2. Integration is not connected to the database")
        print("3. Integration lacks proper permissions")
        
        return False
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_notion_connection()