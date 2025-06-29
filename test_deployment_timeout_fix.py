#!/usr/bin/env python3

"""
Test Deployment Timeout Fix

This script tests the exact MCP tool execution path that might be timing out
in the deployed environment and implements timeout handling.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def test_deployment_timeout_fix():
    """Test MCP tool execution with timeout handling"""
    print("🕐 Testing Deployment Timeout Issues...")
    
    try:
        # Initialize the Atlassian tool
        atlassian_tool = AtlassianTool()
        
        print("🔧 Testing MCP tool execution with shorter timeout...")
        
        # Test the exact confluence search that was failing
        test_result = await asyncio.wait_for(
            atlassian_tool.execute_mcp_tool("confluence_search", {
                "query": "autopilot for everyone",
                "limit": 3  # Reduced limit for faster response
            }),
            timeout=15.0  # 15 second timeout
        )
        
        if test_result and not test_result.get("error"):
            print("✅ SUCCESS: MCP tool execution completed within timeout")
            
            # Check if we got actual results
            if isinstance(test_result, dict):
                result_data = test_result.get("result", [])
                if isinstance(result_data, list) and len(result_data) > 0:
                    print(f"   Retrieved {len(result_data)} Confluence pages")
                    for i, page in enumerate(result_data[:2], 1):
                        if isinstance(page, dict):
                            title = page.get("title", "No title")
                            print(f"   Page {i}: {title}")
                else:
                    print(f"   Result structure: {type(result_data)}")
            
            return True
        else:
            print(f"❌ MCP EXECUTION FAILED: {test_result}")
            return False
            
    except asyncio.TimeoutError:
        print("⏰ TIMEOUT: MCP tool execution exceeded 15 seconds")
        print("   This indicates the deployment environment has slower API response times")
        print("   Solution: Increase timeout values in production configuration")
        return False
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def suggest_deployment_fixes():
    """Suggest fixes for deployment environment issues"""
    print("\n🎯 DEPLOYMENT ENVIRONMENT FIXES:")
    print("1. TIMEOUT CONFIGURATION:")
    print("   - Increase MCP client timeout from 30s to 60s")
    print("   - Add retry logic for timeout errors")
    print("   - Implement graceful degradation for slow responses")
    print()
    print("2. SESSION MANAGEMENT:")
    print("   - Add connection pooling for MCP sessions")
    print("   - Implement session reuse instead of creating new sessions")
    print("   - Add health checks between tool calls")
    print()
    print("3. ERROR HANDLING:")
    print("   - Add specific timeout error messages for users")
    print("   - Implement fallback responses when MCP times out")
    print("   - Log detailed timing information for debugging")

if __name__ == "__main__":
    result = asyncio.run(test_deployment_timeout_fix())
    if not result:
        asyncio.run(suggest_deployment_fixes())