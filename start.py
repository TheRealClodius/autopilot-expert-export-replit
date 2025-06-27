#!/usr/bin/env python3
"""
Simple startup script for deployment
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
if __name__ == "__main__":
    from main import app
    import uvicorn
    
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )