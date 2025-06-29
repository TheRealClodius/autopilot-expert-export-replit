#!/usr/bin/env python3
"""
Deployment startup script that launches both FastAPI server and MCP server
This solves the critical issue where deployment only runs main.py but not the MCP server
"""

import os
import sys
import subprocess
import time
import signal
import asyncio
import aiohttp
from datetime import datetime


def log_message(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


async def wait_for_service(url, service_name, max_attempts=30, delay=2):
    """Wait for a service to become available"""
    log_message(f"Waiting for {service_name} at {url}")
    
    for attempt in range(max_attempts):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        log_message(f"✅ {service_name} is ready!")
                        return True
        except Exception as e:
            if attempt % 5 == 0:  # Log every 5 attempts
                log_message(f"Attempt {attempt + 1}: {service_name} not ready yet...")
            await asyncio.sleep(delay)
    
    log_message(f"❌ {service_name} failed to start after {max_attempts * delay} seconds")
    return False


def start_mcp_server():
    """Start the MCP server process"""
    log_message("🚀 Starting MCP Atlassian Server...")
    
    try:
        # Start MCP server as background process
        mcp_process = subprocess.Popen(
            [sys.executable, "run_mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        log_message(f"MCP server started with PID: {mcp_process.pid}")
        return mcp_process
        
    except Exception as e:
        log_message(f"❌ Failed to start MCP server: {e}")
        return None


def start_fastapi_server():
    """Start the FastAPI server process"""
    log_message("🚀 Starting FastAPI Server...")
    
    try:
        # Start FastAPI server
        fastapi_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        log_message(f"FastAPI server started with PID: {fastapi_process.pid}")
        return fastapi_process
        
    except Exception as e:
        log_message(f"❌ Failed to start FastAPI server: {e}")
        return None


async def monitor_services():
    """Monitor both services and ensure they stay healthy"""
    log_message("🔍 Starting service monitoring...")
    
    while True:
        try:
            # Check MCP server health
            mcp_healthy = await wait_for_service("http://localhost:8001/healthz", "MCP Server", max_attempts=1, delay=1)
            
            # Check FastAPI server health  
            fastapi_healthy = await wait_for_service("http://localhost:5000/health", "FastAPI Server", max_attempts=1, delay=1)
            
            if not mcp_healthy:
                log_message("⚠️ MCP server health check failed")
            
            if not fastapi_healthy:
                log_message("⚠️ FastAPI server health check failed")
            
            if mcp_healthy and fastapi_healthy:
                log_message("✅ Both services healthy")
            
            # Wait before next check
            await asyncio.sleep(30)
            
        except Exception as e:
            log_message(f"❌ Error in service monitoring: {e}")
            await asyncio.sleep(10)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log_message(f"Received signal {signum}, shutting down...")
    sys.exit(0)


async def main():
    """Main deployment startup function"""
    log_message("=" * 80)
    log_message("🚀 DEPLOYMENT STARTUP - DUAL SERVER LAUNCH")
    log_message("=" * 80)
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start MCP server first
    mcp_process = start_mcp_server()
    if not mcp_process:
        log_message("❌ Critical: MCP server failed to start")
        sys.exit(1)
    
    # Wait for MCP server to be ready
    log_message("⏳ Waiting for MCP server to initialize...")
    mcp_ready = await wait_for_service("http://localhost:8001/healthz", "MCP Server")
    
    if not mcp_ready:
        log_message("❌ Critical: MCP server not responding")
        mcp_process.terminate()
        sys.exit(1)
    
    # Start FastAPI server
    fastapi_process = start_fastapi_server()
    if not fastapi_process:
        log_message("❌ Critical: FastAPI server failed to start")
        mcp_process.terminate()
        sys.exit(1)
    
    # Wait for FastAPI server to be ready
    log_message("⏳ Waiting for FastAPI server to initialize...")
    fastapi_ready = await wait_for_service("http://localhost:5000/health", "FastAPI Server")
    
    if not fastapi_ready:
        log_message("❌ Critical: FastAPI server not responding")
        mcp_process.terminate()
        fastapi_process.terminate()
        sys.exit(1)
    
    log_message("✅ DEPLOYMENT READY - Both servers operational!")
    log_message("🔗 FastAPI Server: http://localhost:5000")
    log_message("🔗 MCP Server: http://localhost:8001")
    
    # Keep the main process alive and monitor services
    try:
        await monitor_services()
    except KeyboardInterrupt:
        log_message("Shutting down deployment...")
    finally:
        # Clean shutdown
        log_message("Terminating services...")
        if mcp_process and mcp_process.poll() is None:
            mcp_process.terminate()
        if fastapi_process and fastapi_process.poll() is None:
            fastapi_process.terminate()
        log_message("Deployment shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log_message(f"❌ Deployment startup failed: {e}")
        sys.exit(1)