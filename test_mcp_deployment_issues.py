#!/usr/bin/env python3
"""
Test MCP Atlassian tool execution to identify deployment-specific failures.
This will test the exact failure point causing "execution error" in production.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.atlassian_tool import AtlassianTool

async def test_mcp_deployment_issues():
    """Test MCP tool execution to identify deployment-specific failures"""
    print("🔧 MCP DEPLOYMENT ISSUES ANALYSIS")
    print("=" * 50)
    
    # Initialize tool
    print("\n1. Tool Initialization:")
    try:
        tool = AtlassianTool()
        print(f"   ✅ AtlassianTool initialized (available: {tool.available})")
        print(f"   Available tools: {tool.available_tools}")
    except Exception as e:
        print(f"   ❌ Tool initialization failed: {e}")
        return False
    
    if not tool.available:
        print("   ⚠️ Tool not available - missing credentials")
        return False
    
    # Test basic MCP server connectivity
    print("\n2. MCP Server Connectivity:")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get("http://localhost:8001/healthz")
            print(f"   ✅ Health check: {health_response.status_code}")
            
            # Test MCP endpoint redirect
            mcp_response = await client.post("http://localhost:8001/mcp", json={"test": "ping"})
            print(f"   ✅ MCP endpoint: {mcp_response.status_code} (redirect expected)")
            
    except Exception as e:
        print(f"   ❌ Connectivity test failed: {e}")
        return False
    
    # Test MCP tool execution
    print("\n3. MCP Tool Execution:")
    test_cases = [
        {
            "tool": "confluence_search",
            "args": {"query": "test", "limit": 1},
            "description": "Simple Confluence search"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n   Testing: {test_case['description']}")
        try:
            # Execute the MCP tool call
            result = await tool.execute_mcp_tool(
                tool_name=test_case["tool"],
                arguments=test_case["args"]
            )
            
            # Analyze the result
            if isinstance(result, dict):
                if "error" in result:
                    print(f"   ❌ Tool execution error: {result['error']}")
                    print(f"      Message: {result.get('message', 'No message')}")
                    
                    # Identify specific deployment issues
                    error_type = result.get('error', '')
                    if 'session_init_failed' in error_type:
                        print("   🔍 DEPLOYMENT ISSUE: MCP session initialization failure")
                    elif 'timeout' in error_type.lower():
                        print("   🔍 DEPLOYMENT ISSUE: Network timeout in container environment")
                    elif 'connection' in error_type.lower():
                        print("   🔍 DEPLOYMENT ISSUE: Inter-service communication failure")
                    elif 'authentication' in error_type.lower():
                        print("   🔍 DEPLOYMENT ISSUE: Atlassian authentication in container")
                    else:
                        print(f"   🔍 DEPLOYMENT ISSUE: Unknown error pattern: {error_type}")
                    
                    return False
                else:
                    print(f"   ✅ Tool execution successful")
                    print(f"      Result type: {type(result)}")
                    if "result" in result:
                        print(f"      Has result data: Yes")
                    return True
            else:
                print(f"   ⚠️ Unexpected result type: {type(result)}")
                return False
                
        except Exception as e:
            print(f"   ❌ Tool execution exception: {e}")
            print(f"   🔍 DEPLOYMENT ISSUE: Exception during MCP tool call")
            
            # Analyze exception type for deployment clues
            if "timeout" in str(e).lower():
                print("      → Container network timeout")
            elif "connection" in str(e).lower():
                print("      → Inter-service connection failure")
            elif "authentication" in str(e).lower():
                print("      → Credential access in container")
            else:
                print(f"      → Unknown exception pattern: {str(e)}")
            
            return False
    
    return True

async def main():
    """Run MCP deployment issues analysis"""
    success = await test_mcp_deployment_issues()
    
    print(f"\n{'='*50}")
    print(f"MCP DEPLOYMENT ANALYSIS: {'✅ WORKING' if success else '❌ ISSUES FOUND'}")
    print(f"{'='*50}")
    
    if success:
        print("\n✅ MCP Atlassian tool execution working correctly")
        print("   If you're seeing execution errors in deployment, the issue")
        print("   may be in orchestrator tool routing or state management")
    else:
        print("\n❌ MCP tool execution failing - deployment environment issues")
        print("   This explains the 'execution error' responses you're seeing")
        print("   The issue is in MCP protocol communication or container networking")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)