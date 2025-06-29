"""
Atlassian Tool - SSE Transport Implementation
Uses HTTP/SSE transport instead of stdio to avoid handshake issues.
"""

import asyncio
import logging
import os
import time
import subprocess
import signal
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    SSE-based Atlassian integration tool.
    Starts MCP server with SSE transport and communicates over HTTP.
    """
    
    def __init__(self):
        """Initialize SSE-based Atlassian tool."""
        # Load credentials from environment
        self.jira_url = os.getenv("ATLASSIAN_JIRA_URL", "")
        self.jira_username = os.getenv("ATLASSIAN_JIRA_USERNAME", "")
        self.jira_token = os.getenv("ATLASSIAN_JIRA_TOKEN", "")
        self.confluence_url = os.getenv("ATLASSIAN_CONFLUENCE_URL", "")
        self.confluence_username = os.getenv("ATLASSIAN_CONFLUENCE_USERNAME", "")
        self.confluence_token = os.getenv("ATLASSIAN_CONFLUENCE_TOKEN", "")
        
        # SSE server management
        self._server_process: Optional[subprocess.Popen] = None
        self._server_port = 8001  # Use different port to avoid conflicts
        self._server_url = f"http://localhost:{self._server_port}"
        
        # Tool availability
        self.available = bool(
            self.jira_url and self.jira_username and self.jira_token and
            self.confluence_url and self.confluence_username and self.confluence_token
        )
        
        # Available MCP tools that orchestrator can use directly
        self.available_tools = [
            "jira_search",
            "jira_get", 
            "jira_create",
            "confluence_search",
            "confluence_get"
        ] if self.available else []
        
        if self.available:
            logger.info("SSE-based Atlassian tool initialized successfully")
        else:
            logger.warning("Atlassian tool unavailable - missing credentials")
    
    async def _start_server(self) -> bool:
        """Start MCP server with SSE transport."""
        if self._server_process is not None:
            return True  # Already running
        
        if not self.available:
            logger.error("Cannot start MCP server - credentials not available")
            return False
        
        try:
            # Environment variables for MCP server
            env_vars = os.environ.copy()
            env_vars.update({
                "JIRA_URL": self.jira_url,
                "JIRA_USERNAME": self.jira_username,
                "JIRA_API_TOKEN": self.jira_token,
                "CONFLUENCE_URL": self.confluence_url,
                "CONFLUENCE_USERNAME": self.confluence_username,
                "CONFLUENCE_API_TOKEN": self.confluence_token,
                "TRANSPORT": "sse",
                "PORT": str(self._server_port),
                "HOST": "127.0.0.1",  # Localhost only for security
                "MCP_VERBOSE": "true"
            })
            
            logger.info(f"Starting MCP server on port {self._server_port} with SSE transport")
            
            # Start server process
            import shutil
            uvx_path = shutil.which("uvx")
            if not uvx_path:
                logger.error("uvx not found in PATH")
                return False
            
            self._server_process = subprocess.Popen(
                [uvx_path, "mcp-atlassian"],
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            
            # Wait for server to start
            logger.info("Waiting for MCP server to start...")
            await asyncio.sleep(15)  # Give server time to download deps and start
            
            # Test server health
            return await self._test_server_health()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self._stop_server()
            return False
    
    async def _test_server_health(self) -> bool:
        """Test if MCP server is responding."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try health endpoint
                response = await client.get(f"{self._server_url}/health")
                if response.status_code == 200:
                    logger.info("MCP server health check passed")
                    return True
                else:
                    logger.warning(f"MCP server health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"MCP server health check failed: {e}")
            return False
    
    async def _stop_server(self):
        """Stop MCP server."""
        if self._server_process:
            try:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self._server_process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self._server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not responsive
                    os.killpg(os.getpgid(self._server_process.pid), signal.SIGKILL)
                    self._server_process.wait()
                
                logger.info("MCP server stopped")
                
            except Exception as e:
                logger.warning(f"Error stopping MCP server: {e}")
            
            finally:
                self._server_process = None
    
    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP tool via SSE/HTTP transport.
        
        Args:
            tool_name: MCP tool name (jira_search, confluence_search, etc.)
            arguments: Direct MCP arguments
            
        Returns:
            MCP tool response
        """
        start_time = time.time()
        
        if not self.available:
            return {
                "error": "Atlassian credentials not available",
                "mcp_tool": tool_name,
                "response_time": round(time.time() - start_time, 2)
            }
        
        if tool_name not in self.available_tools:
            return {
                "error": f"Unknown tool: {tool_name}. Available: {self.available_tools}",
                "mcp_tool": tool_name,
                "response_time": round(time.time() - start_time, 2)
            }
        
        # Start server if not running
        if not await self._start_server():
            return {
                "error": "Failed to start MCP server",
                "mcp_tool": tool_name,
                "response_time": round(time.time() - start_time, 2)
            }
        
        try:
            logger.info(f"Executing MCP tool via SSE: {tool_name} with args: {arguments}")
            
            # Prepare MCP request payload
            mcp_payload = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Make HTTP request to MCP server
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._server_url}/mcp",
                    json=mcp_payload
                )
                
                response_time = round(time.time() - start_time, 2)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"MCP tool {tool_name} completed in {response_time}s")
                    
                    # Add metadata to response
                    if isinstance(result, dict):
                        result["mcp_tool"] = tool_name
                        result["response_time"] = response_time
                        result["source"] = "mcp_sse_server"
                        return result
                    else:
                        return {
                            "result": result,
                            "mcp_tool": tool_name,
                            "response_time": response_time,
                            "source": "mcp_sse_server"
                        }
                else:
                    error_text = response.text
                    logger.error(f"MCP tool {tool_name} failed: HTTP {response.status_code} - {error_text}")
                    return {
                        "error": f"HTTP {response.status_code}: {error_text}",
                        "mcp_tool": tool_name,
                        "response_time": response_time
                    }
                    
        except Exception as e:
            logger.error(f"MCP tool {tool_name} execution failed: {e}")
            return {
                "error": f"Tool execution failed: {str(e)}",
                "mcp_tool": tool_name,
                "response_time": round(time.time() - start_time, 2)
            }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._start_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._stop_server()