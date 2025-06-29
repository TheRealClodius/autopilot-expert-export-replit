#!/usr/bin/env python3
"""
Pure MCP Verification Test

Direct test of MCP Atlassian integration without agent infrastructure.
Validates MCP server communication and real data retrieval.
"""

import asyncio
import logging
import json
from tools.atlassian_tool import AtlassianTool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_tools():
    """Test MCP tools directly"""
    
    print("🧪 PURE MCP ATLASSIAN VERIFICATION")
    print("="*50)
    
    # Initialize Atlassian tool
    atlassian_tool = AtlassianTool()
    
    # Test MCP server health
    print("\n🏥 Testing MCP Server Health...")
    try:
        is_healthy = await atlassian_tool.check_server_health()
        if is_healthy:
            print("✅ MCP server is healthy and responding")
        else:
            print("❌ MCP server health check failed")
            return
    except Exception as e:
        print(f"❌ MCP server health check error: {e}")
        return
    
    # Test different MCP tools
    test_cases = [
        {
            "name": "Confluence Search",
            "tool": "confluence_search", 
            "args": {"query": "autopilot for everyone", "limit": 5},
            "expected_fields": ["title", "url", "content"]
        },
        {
            "name": "Jira Search", 
            "tool": "jira_search",
            "args": {"jql": "project = AUTOPILOT AND issuetype = Bug", "max_results": 5},
            "expected_fields": ["key", "summary", "status"]
        },
        {
            "name": "List Available Tools",
            "tool": "list_tools",
            "args": {},
            "expected_fields": []
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔧 Testing: {test_case['name']}")
        print("-" * 30)
        
        try:
            if test_case['tool'] == 'list_tools':
                result = await atlassian_tool.list_tools()
                print(f"✅ Available tools: {result}")
            else:
                result = await atlassian_tool.execute_mcp_tool(
                    test_case['tool'], 
                    test_case['args']
                )
                
                if result.get("success"):
                    results = result.get("result", [])
                    if isinstance(results, list) and len(results) > 0:
                        print(f"✅ Retrieved {len(results)} results")
                        
                        # Show sample result structure
                        sample = results[0]
                        if isinstance(sample, dict):
                            print(f"📄 Sample result keys: {list(sample.keys())}")
                            
                            # Check for expected fields
                            has_expected = all(field in sample for field in test_case['expected_fields'])
                            if has_expected or not test_case['expected_fields']:
                                print(f"✅ {test_case['name']}: SUCCESS")
                                
                                # Show some sample data
                                if 'title' in sample:
                                    print(f"   Title: {sample.get('title', 'N/A')}")
                                if 'url' in sample:
                                    print(f"   URL: {sample.get('url', 'N/A')}")
                                if 'key' in sample:
                                    print(f"   Key: {sample.get('key', 'N/A')}")
                            else:
                                print(f"⚠️ Missing expected fields: {test_case['expected_fields']}")
                        else:
                            print(f"ℹ️ Result format: {type(sample)}")
                    else:
                        print("⚠️ No results returned")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"❌ MCP call failed: {error}")
                    
        except Exception as e:
            print(f"❌ Error testing {test_case['name']}: {e}")
            logger.exception(f"MCP test failed: {test_case['name']}")
    
    print("\n" + "="*50)
    print("🎯 PURE MCP VERIFICATION COMPLETE")
    print("="*50)

async def main():
    """Main test runner"""
    await test_mcp_tools()

if __name__ == "__main__":
    asyncio.run(main())