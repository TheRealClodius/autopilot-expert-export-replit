#!/usr/bin/env python3
"""
Run MCP Atlassian Server with HTTP Transport

This script runs the official mcp-atlassian server using SSE transport
to avoid stdio handshake issues in our environment.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the mcp_atlassian module to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment variables for Atlassian credentials
os.environ["CONFLUENCE_URL"] = os.getenv("ATLASSIAN_CONFLUENCE_URL", "")
os.environ["CONFLUENCE_USERNAME"] = os.getenv("ATLASSIAN_CONFLUENCE_USERNAME", "")
os.environ["CONFLUENCE_API_TOKEN"] = os.getenv("ATLASSIAN_CONFLUENCE_TOKEN", "")
os.environ["JIRA_URL"] = os.getenv("ATLASSIAN_JIRA_URL", "")
os.environ["JIRA_USERNAME"] = os.getenv("ATLASSIAN_JIRA_USERNAME", "")
os.environ["JIRA_API_TOKEN"] = os.getenv("ATLASSIAN_JIRA_TOKEN", "")

# Enable verbose logging
os.environ["MCP_VERBOSE"] = "true"
os.environ["MCP_LOGGING_STDOUT"] = "true"

# Set transport and port
transport = "sse"  # Use SSE transport instead of stdio
port = 8001
host = "127.0.0.1"

async def main():
    """Run the MCP server with SSE transport"""
    print(f"🚀 Starting MCP Atlassian Server on {transport} transport at {host}:{port}")
    
    try:
        # Import the main MCP server module
        from mcp_atlassian.servers import main_mcp
        
        # Run with SSE transport
        await main_mcp.run_async(
            transport=transport,
            host=host,
            port=port,
            log_level="debug"
        )
    except Exception as e:
        print(f"❌ Error starting MCP server: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 MCP ATLASSIAN SERVER STARTUP")
    print("=" * 50)
    
    # Check credentials
    required_vars = [
        "ATLASSIAN_CONFLUENCE_URL",
        "ATLASSIAN_CONFLUENCE_USERNAME", 
        "ATLASSIAN_CONFLUENCE_TOKEN",
        "ATLASSIAN_JIRA_URL",
        "ATLASSIAN_JIRA_USERNAME",
        "ATLASSIAN_JIRA_TOKEN"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ All required environment variables present")
    
    # Run the server
    success = asyncio.run(main())
    
    if not success:
        sys.exit(1)
    
    print("✅ MCP server started successfully")