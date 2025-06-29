#!/usr/bin/env python3
"""
Deployment startup script for Cloud Run.
Handles deployment-specific configuration and starts the FastAPI server.
"""
import os
import sys
import logging
import asyncio
from main import app
import uvicorn

# Configure logging for deployment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def configure_deployment_environment():
    """Configure environment variables for Cloud Run deployment"""
    
    # Set deployment-specific environment variables
    os.environ["DEPLOYMENT_ENV"] = "production"
    os.environ["REPLIT_DEPLOYMENT"] = "1"
    
    # Ensure Redis and Celery use memory transport in deployment
    if not os.environ.get("REDIS_URL"):
        os.environ["REDIS_URL"] = ""  # Force memory cache
        logger.info("Redis URL not configured, using memory cache")
    
    if not os.environ.get("CELERY_BROKER_URL"):
        os.environ["CELERY_BROKER_URL"] = ""  # Force memory transport
        logger.info("Celery broker URL not configured, using memory transport")
    
    # Set MCP server URL to remote deployed service
    if not os.environ.get("MCP_SERVER_URL"):
        os.environ["MCP_SERVER_URL"] = "https://remote-mcp-server-andreiclodius.replit.app"
        logger.info("MCP server URL configured for remote service")
    
    # Disable port forwarding in deployment
    os.environ.pop("PORT_6379", None)
    os.environ.pop("PORT_8001", None)
    
    logger.info("Deployment environment configured successfully")

def main():
    """Main deployment startup function"""
    
    logger.info("Starting deployment initialization...")
    
    # Configure deployment environment
    configure_deployment_environment()
    
    # Get port from environment (Cloud Run provides this)
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"  # Bind to all interfaces for Cloud Run
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    
    # Start the FastAPI server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        # Deployment-optimized settings
        workers=1,  # Single worker for Cloud Run
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30
    )

if __name__ == "__main__":
    main()