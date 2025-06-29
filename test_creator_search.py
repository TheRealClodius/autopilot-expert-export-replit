#!/usr/bin/env python3
"""
Test the enhanced creator search functionality
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def test_creator_search():
    """Test the creator search with smart CQL query building"""
    
    print("🔍 Testing enhanced creator search functionality...")
    
    try:
        # Initialize Atlassian tool
        atlassian_tool = AtlassianTool()
        
        # Test the smart CQL query building
        test_queries = [
            "List all pages created by Andrei Clodius",
            "created by Andrei Clodius",
            "pages by Andrei Clodius",
            "Andrei Clodius pages"
        ]
        
        for query in test_queries:
            print(f"\n📝 Testing query: '{query}'")
            smart_cql = atlassian_tool._build_smart_cql_query(query)
            print(f"   Generated CQL: {smart_cql}")
        
        # Test actual search with automatic retry
        print(f"\n🔍 Testing actual search with automatic retry...")
        
        result = await atlassian_tool.search_confluence_pages(
            query="List all pages created by Andrei Clodius",
            max_results=10
        )
        
        if result and "error" not in result:
            pages = result.get("confluence_search_results", {}).get("pages", [])
            print(f"✅ Search completed successfully")
            print(f"📄 Found {len(pages)} pages:")
            
            for i, page in enumerate(pages, 1):
                print(f"\n   Page {i}:")
                print(f"      Title: {page.get('title', 'N/A')}")
                print(f"      Space: {page.get('space', 'N/A')}")
                print(f"      Creator: {page.get('creator', 'N/A')}")
                print(f"      URL: {page.get('url', 'N/A')}")
                
        else:
            print(f"❌ Search failed: {result}")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_creator_search())