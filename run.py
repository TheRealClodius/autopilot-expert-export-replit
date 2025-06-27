#!/usr/bin/env python3
"""
Deployment entry point for Replit hosting.
Handles environment setup and graceful startup.
"""

import os
import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Ensure we're in the right directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        sys.path.insert(0, script_dir)
        
        logger.info("Starting Autopilot Expert Multi-Agent System...")
        
        # Import the application
        from main import app
        import uvicorn
        
        # Get port from environment (required for Replit deployment)
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"Starting server on port {port}")
        
        # Run the application
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()