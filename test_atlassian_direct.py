#!/usr/bin/env python3
"""
Direct test of Atlassian tool to see actual output
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def test_atlassian_output():
    """Test the actual output from Atlassian tool"""
    
    print("🔍 Testing Atlassian tool direct output...")
    
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
    
    print("🔍 Testing Confluence search...")
    result = await tool.search_confluence_pages("A4E", max_results=5)
    
    print("📄 RAW RESULT:")
    print(result)
    
    print("\n🔍 Testing Jira search...")
    jira_result = await tool.search_jira_issues("project = AUTOPILOT", max_results=5)
    
    print("📄 JIRA RAW RESULT:")
    print(jira_result)

if __name__ == "__main__":
    asyncio.run(test_atlassian_output())