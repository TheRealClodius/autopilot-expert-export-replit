#!/usr/bin/env python3
"""
Test MCP Simple Connection - Try minimal MCP setup to identify the hang
"""

import asyncio
import subprocess
import json
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from config import settings

async def test_simple_mcp():
    """Test MCP with minimal setup"""
    print("Testing MCP with simple configuration...")
    
    # Test 1: Can we run the MCP server at all?
    print("\nStep 1: Testing MCP server startup")
    try:
        # Try running the server with minimal args
        result = subprocess.run([
            "uvx", "mcp-atlassian", "--version"
        ], capture_output=True, text=True, timeout=10)
        
        print(f"MCP server version check: {result.returncode}")
        if result.stdout:
            print(f"Version output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error output: {result.stderr.strip()}")
            
    except Exception as e:
        print(f"Version check failed: {e}")
        return
    
    # Test 2: Try connecting with stdio
    print("\nStep 2: Testing stdio connection")
    
    try:
        # Simplified command
        command_parts = [
            "uvx", "mcp-atlassian",
            "--jira-url", settings.ATLASSIAN_JIRA_URL,
            "--jira-username", settings.ATLASSIAN_JIRA_USERNAME, 
            "--jira-token", settings.ATLASSIAN_JIRA_TOKEN,
            "--confluence-url", settings.ATLASSIAN_CONFLUENCE_URL,
            "--confluence-username", settings.ATLASSIAN_CONFLUENCE_USERNAME,
            "--confluence-token", settings.ATLASSIAN_CONFLUENCE_TOKEN,
            "--transport", "stdio"  # Explicitly specify stdio
        ]
        
        print("Starting MCP server with stdio transport...")
        
        server_params = StdioServerParameters(
            command="uvx",
            args=command_parts[1:]  # Skip 'uvx'
        )
        
        # Try with shorter timeout
        session_context = stdio_client(server_params)
        
        print("Attempting server connection...")
        read_stream, write_stream = await asyncio.wait_for(
            session_context.__aenter__(),
            timeout=20.0
        )
        
        print("Creating client session...")
        session = ClientSession(read_stream, write_stream)
        
        print("Initializing session...")
        await asyncio.wait_for(session.initialize(), timeout=10.0)
        
        print("SUCCESS: MCP session established!")
        
        # Test a simple tool call
        print("Testing tool call...")
        result = await asyncio.wait_for(
            session.call_tool("confluence_search", {"query": "test", "limit": 1}),
            timeout=15.0
        )
        
        print(f"Tool call result type: {type(result)}")
        content_list = getattr(result, 'content', [])
        if content_list:
            content = content_list[0]
            if hasattr(content, 'text'):
                print(f"Got response: {content.text[:200]}...")
            else:
                print(f"Content: {content}")
        
        # Cleanup
        await session_context.__aexit__(None, None, None)
        print("Session cleaned up successfully")
        
        return True
        
    except asyncio.TimeoutError as e:
        print(f"Connection timed out: {e}")
        return False
    except Exception as e:
        print(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_mcp())
    print(f"\nFinal result: {'SUCCESS' if result else 'FAILED'}")