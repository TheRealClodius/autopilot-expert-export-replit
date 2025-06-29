#!/usr/bin/env python3
"""
Direct Atlassian Search Test
Tests the Atlassian tool directly to see actual search results for "Andrei Clodius"
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def test_direct_confluence_search():
    """Test direct Confluence search for Andrei Clodius"""
    
    print("🔍 DIRECT ATLASSIAN CONFLUENCE SEARCH TEST")
    print("Searching for: Pages created by Andrei Clodius")
    print("="*60)
    
    try:
        # Initialize Atlassian tool
        atlassian_tool = AtlassianTool()
        
        # Test 1: Direct creator search with CQL
        print("\n🎯 TEST 1: CQL Creator Search")
        print("Query: creator = \"Andrei Clodius\"")
        
        result1 = await atlassian_tool.search_confluence_pages(
            query="creator = \"Andrei Clodius\"",
            max_results=10
        )
        
        print(f"Result Type: {type(result1)}")
        print(f"Success: {result1.get('success', False) if isinstance(result1, dict) else 'Unknown'}")
        
        if isinstance(result1, dict) and result1.get('success'):
            pages = result1.get('confluence_search_results', {}).get('pages', [])
            print(f"✅ Found {len(pages)} pages")
            
            for i, page in enumerate(pages, 1):
                title = page.get('title', 'No title')
                creator = page.get('creator', 'Unknown creator')
                space = page.get('space', {}).get('name', 'Unknown space')
                print(f"   {i}. {title}")
                print(f"      Creator: {creator}")
                print(f"      Space: {space}")
                print()
        else:
            print(f"❌ Search failed")
            if isinstance(result1, dict):
                error = result1.get('error', 'Unknown error')
                print(f"   Error: {error}")
        
        # Test 2: Alternative search approach
        print("\n🎯 TEST 2: Alternative Search")
        print("Query: Andrei Clodius (simple text search)")
        
        result2 = await atlassian_tool.search_confluence_pages(
            query="Andrei Clodius",
            max_results=10
        )
        
        print(f"Result Type: {type(result2)}")
        print(f"Success: {result2.get('success', False) if isinstance(result2, dict) else 'Unknown'}")
        
        if isinstance(result2, dict) and result2.get('success'):
            pages = result2.get('confluence_search_results', {}).get('pages', [])
            print(f"✅ Found {len(pages)} pages")
            
            for i, page in enumerate(pages, 1):
                title = page.get('title', 'No title')
                creator = page.get('creator', 'Unknown creator')
                space = page.get('space', {}).get('name', 'Unknown space')
                print(f"   {i}. {title}")
                print(f"      Creator: {creator}")
                print(f"      Space: {space}")
                print()
        else:
            print(f"❌ Search failed")
            if isinstance(result2, dict):
                error = result2.get('error', 'Unknown error')
                print(f"   Error: {error}")
        
        # Test 3: Check if credentials are working
        print("\n🎯 TEST 3: General Search (Credential Test)")
        print("Query: UiPath (general search)")
        
        result3 = await atlassian_tool.search_confluence_pages(
            query="UiPath",
            max_results=5
        )
        
        print(f"Result Type: {type(result3)}")
        print(f"Success: {result3.get('success', False) if isinstance(result3, dict) else 'Unknown'}")
        
        if isinstance(result3, dict) and result3.get('success'):
            pages = result3.get('confluence_search_results', {}).get('pages', [])
            print(f"✅ Found {len(pages)} pages (credentials working)")
        else:
            print(f"❌ Credentials may not be working")
            if isinstance(result3, dict):
                error = result3.get('error', 'Unknown error')
                print(f"   Error: {error}")
        
        return result1, result2, result3
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None

if __name__ == "__main__":
    result1, result2, result3 = asyncio.run(test_direct_confluence_search())
    
    print(f"\n📝 SUMMARY:")
    print(f"Direct Atlassian tool testing completed.")
    print(f"This shows the actual search results without orchestrator involvement.")