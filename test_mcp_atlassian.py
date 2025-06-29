#!/usr/bin/env python3
"""
Test MCP Atlassian Integration
Tests the new MCP-based Atlassian tool implementation
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def test_mcp_atlassian():
    """Test the new MCP Atlassian tool implementation"""
    
    print("🔍 Testing MCP Atlassian tool...")
    
    tool = AtlassianTool()
    
    print(f"✅ Tool available: {tool.available}")
    
    if not tool.available:
        print("❌ Tool not available - missing credentials")
        print(f"Jira URL: {bool(tool.jira_url)}")
        print(f"Jira Username: {bool(tool.jira_username)}")
        print(f"Jira Token: {bool(tool.jira_token)}")
        print(f"Confluence URL: {bool(tool.confluence_url)}")
        print(f"Confluence Username: {bool(tool.confluence_username)}")
        print(f"Confluence Token: {bool(tool.confluence_token)}")
        return
    
    print("🔍 Testing MCP session creation...")
    try:
        session = await tool._get_session()
        if session:
            print("✅ MCP session created successfully")
        else:
            print("❌ Failed to create MCP session")
            return
    except Exception as e:
        print(f"❌ MCP session creation failed: {e}")
        return
    
    print("🔍 Testing Confluence search...")
    try:
        result = await tool.search_confluence_pages("template", max_results=3)
        print("📄 CONFLUENCE SEARCH RESULT:")
        print(f"Status: {'✅ Success' if 'error' not in result else '❌ Error'}")
        if 'error' not in result:
            search_results = result.get('confluence_search_results', {})
            pages = search_results.get('pages', [])
            print(f"Found: {search_results.get('total_found', 0)} total, {len(pages)} returned")
            for i, page in enumerate(pages[:2], 1):
                print(f"  {i}. {page.get('title', 'No title')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Confluence search failed: {e}")
    
    print("\n🔍 Testing Jira search...")
    try:
        result = await tool.search_jira_issues("project = AUTOPILOT", max_results=3)
        print("📄 JIRA SEARCH RESULT:")
        print(f"Status: {'✅ Success' if 'error' not in result else '❌ Error'}")
        if 'error' not in result:
            search_results = result.get('jira_search_results', {})
            issues = search_results.get('issues', [])
            print(f"Found: {search_results.get('total_found', 0)} total, {len(issues)} returned")
            for i, issue in enumerate(issues[:2], 1):
                print(f"  {i}. {issue.get('key')}: {issue.get('summary', 'No summary')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Jira search failed: {e}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    await tool._cleanup_session()
    print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(test_mcp_atlassian())