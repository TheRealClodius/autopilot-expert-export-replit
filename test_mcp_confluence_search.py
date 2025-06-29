#!/usr/bin/env python3
"""
Test MCP Confluence Search - "Autopilot for Everyone"

This test directly calls the MCP Atlassian tool to search for "autopilot for everyone"
in Confluence and shows the actual results returned from the MCP server.
"""
import asyncio
import json
from tools.atlassian_tool import AtlassianTool

async def test_confluence_search():
    """Test direct MCP Confluence search for 'autopilot for everyone'"""
    print("🔍 TESTING MCP CONFLUENCE SEARCH")
    print("=" * 50)
    print("Query: 'autopilot for everyone'")
    print("=" * 50)
    
    try:
        # Initialize Atlassian tool
        atlassian_tool = AtlassianTool()
        
        # Test direct MCP call to confluence_search
        search_query = "autopilot for everyone"
        arguments = {
            "query": search_query,
            "limit": 10
        }
        
        print(f"📡 Making MCP call: confluence_search")
        print(f"📋 Arguments: {arguments}")
        print("\n⏳ Calling MCP server...")
        
        # Execute MCP tool call
        result = await atlassian_tool.execute_mcp_tool("confluence_search", arguments)
        
        print("\n📊 MCP RESPONSE:")
        print("=" * 50)
        
        if result:
            print(f"✅ Response received (type: {type(result)})")
            
            # Pretty print the full response
            if isinstance(result, dict):
                print("📄 Full Response Structure:")
                print(json.dumps(result, indent=2, default=str))
                
                # Check for errors
                if "error" in result:
                    print(f"\n❌ Error found: {result['error']}")
                    return False
                
                # Look for Confluence search results
                confluence_data = result.get("result", {})
                if isinstance(confluence_data, dict):
                    search_results = confluence_data.get("confluence_search_results", {})
                    pages = search_results.get("pages", [])
                    total_found = search_results.get("total_found", 0)
                    
                    print(f"\n📈 SEARCH SUMMARY:")
                    print(f"Total results found: {total_found}")
                    print(f"Pages returned: {len(pages)}")
                    
                    if pages:
                        print(f"\n📚 CONFLUENCE PAGES FOUND:")
                        for i, page in enumerate(pages, 1):
                            title = page.get("title", "No title")
                            space = page.get("space_name", "Unknown space")
                            url = page.get("url", "No URL")
                            excerpt = page.get("excerpt", "No excerpt")[:100]
                            
                            print(f"\n{i}. {title}")
                            print(f"   Space: {space}")
                            print(f"   URL: {url}")
                            print(f"   Excerpt: {excerpt}...")
                        
                        print(f"\n✅ SUCCESS: Found {len(pages)} Confluence pages about 'autopilot for everyone'")
                        return True
                    else:
                        print(f"\n⚠️  No pages found in search results")
                        return False
                else:
                    print(f"\n⚠️  Unexpected result format: {type(confluence_data)}")
                    print(f"Raw result: {confluence_data}")
                    return False
            else:
                print(f"⚠️  Non-dict response: {result}")
                return False
        else:
            print("❌ No response received from MCP server")
            return False
            
    except Exception as e:
        print(f"💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_confluence_search()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 MCP CONFLUENCE INTEGRATION: WORKING")
        print("✅ Successfully retrieved Confluence content via MCP")
    else:
        print("❌ MCP CONFLUENCE INTEGRATION: NEEDS ATTENTION")
        print("❌ Could not retrieve Confluence content")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())