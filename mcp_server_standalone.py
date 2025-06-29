#!/usr/bin/env python3
"""
Standalone MCP Atlassian Server
This can be deployed as a separate Replit project for the MCP service
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_message(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def validate_environment():
    """Validate required environment variables for MCP server"""
    required_vars = [
        "ATLASSIAN_JIRA_URL",
        "ATLASSIAN_JIRA_USERNAME", 
        "ATLASSIAN_JIRA_TOKEN",
        "ATLASSIAN_CONFLUENCE_URL",
        "ATLASSIAN_CONFLUENCE_USERNAME",
        "ATLASSIAN_CONFLUENCE_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        log_message(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    log_message("✅ All required environment variables present")
    return True

async def main():
    """Main function to run standalone MCP server"""
    
    log_message("🔧 MCP ATLASSIAN SERVER STARTUP")
    log_message("=" * 50)
    
    # Validate environment
    if not validate_environment():
        log_message("❌ Environment validation failed")
        sys.exit(1)
    
    # Get port from environment (Replit deployment compatibility)
    port = int(os.getenv("PORT", "8001"))
    host = "0.0.0.0"
    
    log_message(f"🚀 Starting MCP Atlassian Server on {host}:{port}")
    
    try:
        # Import and run the MCP server
        from mcp_atlassian.server import create_app
        import uvicorn
        
        # Create the FastAPI app
        app = create_app()
        
        # Run the server
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        log_message(f"✅ MCP Server starting on http://{host}:{port}")
        log_message(f"🔗 Health check: http://{host}:{port}/healthz")
        log_message(f"🔗 MCP endpoint: http://{host}:{port}/mcp/sse")
        
        await server.serve()
        
    except ImportError as e:
        log_message(f"❌ Failed to import MCP server: {e}")
        log_message("Make sure mcp-atlassian is properly installed")
        sys.exit(1)
    except Exception as e:
        log_message(f"❌ Failed to start MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())