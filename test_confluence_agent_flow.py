#!/usr/bin/env python3
"""
Test Confluence Agent Flow - Simulating Real Agent Workflow
"""
import asyncio
import time
from tools.atlassian_tool import AtlassianTool

async def test_confluence_agent_flow():
    """Test the actual agent workflow for Confluence access"""
    
    print("🤖 TESTING CONFLUENCE AGENT WORKFLOW")
    print("="*50)
    
    # Initialize the Atlassian tool like the agent does
    atlassian_tool = AtlassianTool()
    
    if not atlassian_tool.available:
        print("❌ Atlassian tool not available - credentials missing")
        return
    
    print("✅ Atlassian tool initialized successfully")
    print(f"   Jira URL: {atlassian_tool.jira_url}")
    print(f"   Confluence URL: {atlassian_tool.confluence_url}")
    
    # Test different types of Confluence searches that agents might perform
    test_cases = [
        {
            "name": "General Documentation Search", 
            "query": "API documentation",
            "description": "Search for general API documentation"
        },
        {
            "name": "Specific Template Search",
            "query": "UX Audit Evaluation Template", 
            "description": "Search for a specific template"
        },
        {
            "name": "Creator-Based Search",
            "query": "pages created by Andrei Clodius",
            "description": "Search for pages by a specific creator"
        },
        {
            "name": "Project Documentation",
            "query": "UiPath Autopilot documentation",
            "description": "Search for project-specific documentation"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test_case['name']}")
        print(f"Query: '{test_case['query']}'")
        print(f"Description: {test_case['description']}")
        
        start_time = time.time()
        
        try:
            # Perform the search exactly like the agent would
            result = await atlassian_tool.search_confluence_pages(
                query=test_case['query'],
                max_results=5
            )
            
            elapsed = time.time() - start_time
            
            print(f"⏱️ Execution time: {elapsed:.2f}s")
            
            # Analyze the result
            if isinstance(result, dict):
                if "error" in result:
                    print(f"❌ Search failed with error: {result['error']}")
                    if "message" in result:
                        print(f"   Message: {result['message']}")
                elif "confluence_search_results" in result:
                    search_results = result["confluence_search_results"]
                    total_found = search_results.get("total_found", 0)
                    pages = search_results.get("pages", [])
                    
                    print(f"✅ Search completed successfully")
                    print(f"   Total found: {total_found}")
                    print(f"   Returned: {len(pages)}")
                    
                    if pages:
                        print("   Results:")
                        for j, page in enumerate(pages[:3], 1):  # Show first 3
                            title = page.get("title", "No title")
                            space = page.get("space_name", "Unknown space")
                            print(f"     {j}. {title}")
                            print(f"        Space: {space}")
                    else:
                        print("   No pages returned")
                else:
                    print(f"❓ Unexpected result format: {type(result)}")
                    print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            else:
                print(f"❓ Unexpected result type: {type(result)}")
                print(f"   Content: {str(result)[:200]}...")
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"💥 Exception after {elapsed:.2f}s: {str(e)}")
            print(f"   Exception type: {type(e).__name__}")
    
    # Test getting a specific page (if we found any)
    print(f"\n🧪 TEST 5: Get Specific Page")
    try:
        # Try to get a specific page by ID (use a known page from UiPath Confluence)
        result = await atlassian_tool.get_confluence_page("123456789")  # This will likely fail, but we'll see how
        
        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Page access failed (expected): {result['error']}")
            elif "confluence_page" in result:
                page = result["confluence_page"]
                print(f"✅ Page accessed successfully: {page.get('title', 'No title')}")
            else:
                print(f"❓ Unexpected page result format")
        
    except Exception as e:
        print(f"💥 Page access exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_confluence_agent_flow())