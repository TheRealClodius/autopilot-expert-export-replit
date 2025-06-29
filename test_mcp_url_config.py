#!/usr/bin/env python3
"""
Test MCP URL Configuration

Verify AtlassianTool uses configurable URL setting instead of hardcoded localhost.
"""

import os
from tools.atlassian_tool import AtlassianTool
from config import settings

def test_mcp_url_config():
    """Test that AtlassianTool uses configurable MCP_SERVER_URL"""
    
    print("🧪 MCP URL CONFIGURATION TEST")
    print("=" * 50)
    
    # Show current configuration
    print(f"1. Current MCP_SERVER_URL setting: {settings.MCP_SERVER_URL}")
    
    # Initialize AtlassianTool
    tool = AtlassianTool()
    print(f"2. AtlassianTool mcp_server_url: {tool.mcp_server_url}")
    print(f"3. AtlassianTool sse_endpoint: {tool.sse_endpoint}")
    
    # Verify they match
    if tool.mcp_server_url == settings.MCP_SERVER_URL:
        print("   ✅ AtlassianTool correctly uses configurable URL")
    else:
        print("   ❌ AtlassianTool NOT using configurable URL")
        return False
    
    # Test that changing the environment variable would affect the tool
    print(f"\n4. Testing URL configuration flexibility:")
    expected_sse = f"{settings.MCP_SERVER_URL}/sse"
    if tool.sse_endpoint == expected_sse:
        print(f"   ✅ SSE endpoint correctly derived: {tool.sse_endpoint}")
    else:
        print(f"   ❌ SSE endpoint mismatch. Expected: {expected_sse}, Got: {tool.sse_endpoint}")
        return False
    
    print(f"\n✅ MCP URL CONFIGURATION TEST PASSED")
    print(f"💡 To fix deployment connectivity:")
    print(f"   export MCP_SERVER_URL='http://your-deployment-mcp-host:8001'")
    
    return True

if __name__ == "__main__":
    success = test_mcp_url_config()
    exit(0 if success else 1)