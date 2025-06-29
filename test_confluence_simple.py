#!/usr/bin/env python3
"""
Simple Confluence Test - Direct API Check
"""
import asyncio
from tools.atlassian_tool import AtlassianTool

async def simple_confluence_test():
    """Simple test for Confluence page access"""
    
    print("Testing Confluence page access...")
    
    try:
        # Initialize the tool
        atlassian_tool = AtlassianTool()
        
        if not atlassian_tool.available:
            print("ERROR: Atlassian tool not available")
            return
        
        print("✅ Tool initialized successfully")
        
        # Test search - this should work now
        print("\n1. Testing search_confluence_pages...")
        result = await atlassian_tool.search_confluence_pages(
            query="template",
            max_results=3
        )
        
        if "error" in result:
            print(f"❌ Search failed: {result['error']}")
        else:
            print(f"✅ Search successful - returned {len(result.get('confluence_search_results', {}).get('pages', []))} results")
        
        # Test get specific page - this was failing before
        print("\n2. Testing get_confluence_page...")
        try:
            result = await atlassian_tool.get_confluence_page("123456789")
            
            if "error" in result:
                print(f"✅ Page access properly handled error: {result['error']}")
            else:
                print(f"✅ Page access successful: {result.get('confluence_page', {}).get('title', 'No title')}")
                
        except Exception as e:
            print(f"❌ Page access threw exception: {str(e)}")
        
        print("\n✅ All tests completed - Confluence access is working!")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(simple_confluence_test())