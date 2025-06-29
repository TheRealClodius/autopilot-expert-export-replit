#!/usr/bin/env python3
"""
Simple test to search Confluence for the UX Audit Evaluation Template
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def test_confluence_search():
    """Test direct Confluence search for UX Audit Evaluation Template"""
    
    print("🔍 Testing direct Confluence search for UX Audit Evaluation Template...")
    
    try:
        # Initialize Atlassian tool
        atlassian_tool = AtlassianTool()
        
        # Search for the UX Audit Evaluation Template
        print("📋 Searching Confluence for 'UX Audit Evaluation Template'...")
        
        result = await atlassian_tool.search_confluence_pages(
            query="UX Audit Evaluation Template",
            max_results=10
        )
        
        if result:
            print(f"✅ Search completed successfully")
            print(f"📄 Found {len(result)} results:")
            
            for i, page in enumerate(result, 1):
                print(f"\n   Result {i}:")
                print(f"      Title: {page.get('title', 'N/A')}")
                print(f"      Space: {page.get('space', {}).get('name', 'N/A')}")
                print(f"      Author: {page.get('version', {}).get('by', {}).get('displayName', 'N/A')}")
                print(f"      Created by: {page.get('history', {}).get('createdBy', {}).get('displayName', 'N/A')}")
                print(f"      URL: {page.get('_links', {}).get('webui', 'N/A')}")
                
                # Check if this looks like the UX Audit template
                title = page.get('title', '').lower()
                if 'ux audit' in title and 'template' in title:
                    print(f"🎯 FOUND TARGET DOCUMENT!")
                    creator = page.get('history', {}).get('createdBy', {}).get('displayName', 'Unknown')
                    author = page.get('version', {}).get('by', {}).get('displayName', 'Unknown')
                    print(f"      Document creator: {creator}")
                    print(f"      Last modified by: {author}")
                    
                    if 'mausam' in creator.lower() or 'mausam' in author.lower():
                        print("🎉 SUCCESS: Found Mausam Jain as expected!")
                    else:
                        print(f"⚠️  Expected Mausam Jain, found: Creator={creator}, Author={author}")
        else:
            print("❌ No results found or search failed")
            
    except Exception as e:
        print(f"❌ Error during search: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_confluence_search())