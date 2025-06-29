#!/usr/bin/env python3
"""
Test Deployment - Autopilot Query

Test the exact query from the user's screenshot to verify the deployment fix works.
"""

import asyncio
import sys
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_autopilot_roadmap_query():
    """Test the exact query from user's screenshot"""
    
    print("\n" + "="*60)
    print("DEPLOYMENT TEST: Autopilot Roadmap Query")
    print("="*60)
    
    try:
        # Step 1: Verify MCP server is ready
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get("http://localhost:8001/healthz")
            if health_response.status_code != 200:
                print(f"❌ MCP server not healthy: {health_response.status_code}")
                return False
        
        print("✅ MCP server health check: PASSED")
        
        # Step 2: Test direct MCP query for Autopilot roadmap
        from tools.atlassian_tool import AtlassianTool
        
        tool = AtlassianTool()
        if not tool.available:
            print("❌ AtlassianTool not available")
            return False
        
        print("✅ AtlassianTool availability: PASSED")
        
        # Step 3: Test the exact query from screenshot
        print("\n🔍 Testing query: 'help me retrieve the roadmap for Autopilot for Everyone'")
        
        start_time = time.time()
        
        # Try Confluence search for Autopilot roadmap
        confluence_result = await tool.execute_mcp_tool('confluence_search', {
            'query': 'Autopilot for Everyone roadmap',
            'limit': 5
        })
        
        confluence_time = time.time() - start_time
        
        print(f"⏱️  Confluence search completed in {confluence_time:.2f}s")
        
        if confluence_result.get('success'):
            results = confluence_result.get('result', {})
            if isinstance(results, dict) and 'result' in results:
                pages = results['result']
                print(f"✅ Found {len(pages)} Confluence pages:")
                
                for i, page in enumerate(pages[:3], 1):
                    title = page.get('title', 'Unknown')
                    url = page.get('url', '')
                    space = page.get('space', {}).get('name', 'Unknown Space')
                    print(f"   {i}. {title} ({space})")
                    if url:
                        print(f"      URL: {url}")
                
                if pages:
                    print("\n✅ CONFLUENCE SEARCH: SUCCESS - Found Autopilot documentation")
                else:
                    print("\n⚠️  CONFLUENCE SEARCH: No pages found")
            else:
                print(f"\n❌ CONFLUENCE SEARCH: Unexpected result format: {type(results)}")
        else:
            error_msg = confluence_result.get('error', 'Unknown error')
            print(f"\n❌ CONFLUENCE SEARCH: FAILED - {error_msg}")
        
        # Step 4: Try Jira search for Autopilot roadmap
        print(f"\n🔍 Searching Jira for Autopilot roadmap...")
        
        jira_start = time.time()
        jira_result = await tool.execute_mcp_tool('jira_search', {
            'query': 'Autopilot for Everyone roadmap',
            'limit': 3
        })
        
        jira_time = time.time() - jira_start
        print(f"⏱️  Jira search completed in {jira_time:.2f}s")
        
        if jira_result.get('success'):
            issues = jira_result.get('result', {}).get('result', [])
            if issues:
                print(f"✅ Found {len(issues)} Jira issues:")
                for i, issue in enumerate(issues, 1):
                    key = issue.get('key', 'Unknown')
                    summary = issue.get('summary', 'No summary')
                    status = issue.get('status', 'Unknown')
                    print(f"   {i}. {key}: {summary} [{status}]")
                
                print("\n✅ JIRA SEARCH: SUCCESS - Found Autopilot issues")
            else:
                print("\n⚠️  JIRA SEARCH: No issues found")
        else:
            error_msg = jira_result.get('error', 'Unknown error')
            print(f"\n❌ JIRA SEARCH: FAILED - {error_msg}")
        
        total_time = time.time() - start_time
        print(f"\n🎯 TOTAL QUERY TIME: {total_time:.2f}s")
        
        # Step 5: Determine overall success
        confluence_success = confluence_result.get('success', False)
        jira_success = jira_result.get('success', False)
        
        if confluence_success or jira_success:
            print("\n✅ DEPLOYMENT TEST: SUCCESS")
            print("   The bot can now access Autopilot documentation!")
            return True
        else:
            print("\n❌ DEPLOYMENT TEST: FAILED")
            print("   The bot still cannot access Autopilot documentation")
            return False
        
    except Exception as e:
        print(f"\n❌ DEPLOYMENT TEST: EXCEPTION - {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the deployment test"""
    success = await test_autopilot_roadmap_query()
    
    if success:
        print("\n🎉 The deployment issue has been RESOLVED!")
        print("   Users can now ask for Autopilot roadmaps and get proper responses.")
    else:
        print("\n⚠️  The deployment issue persists.")
        print("   Additional troubleshooting may be needed.")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)