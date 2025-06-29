"""
Atlassian Tool - Clean MCP-Only Implementation
Direct MCP integration using the mcp-atlassian package without REST API fallbacks.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    Clean MCP-only Atlassian integration tool.
    Communicates directly with mcp-atlassian server for all operations.
    """
    
    def __init__(self):
        """Initialize clean MCP-only Atlassian tool."""
        # Load credentials from environment
        self.jira_url = os.getenv("ATLASSIAN_JIRA_URL", "")
        self.jira_username = os.getenv("ATLASSIAN_JIRA_USERNAME", "")
        self.jira_token = os.getenv("ATLASSIAN_JIRA_TOKEN", "")
        self.confluence_url = os.getenv("ATLASSIAN_CONFLUENCE_URL", "")
        self.confluence_username = os.getenv("ATLASSIAN_CONFLUENCE_USERNAME", "")
        self.confluence_token = os.getenv("ATLASSIAN_CONFLUENCE_TOKEN", "")
        
        # MCP session management
        self._session: Optional[ClientSession] = None
        self._session_context = None
        
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
            logger.info("Clean MCP-only Atlassian tool initialized successfully")
        else:
            logger.warning("Atlassian tool unavailable - missing credentials")
    
    async def _get_session(self) -> Optional[ClientSession]:
        """Get or create MCP client session with timeout and retry logic."""
        if self._session is not None:
            return self._session
        
        if not self.available:
            logger.error("Cannot create MCP session - credentials not available")
            return None
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Creating MCP session (attempt {retry_count + 1}/{max_retries})")
                
                # Build command for mcp-atlassian server
                command_parts = [
                    "uvx", "mcp-atlassian",
                    "--jira-url", self.jira_url,
                    "--jira-username", self.jira_username,
                    "--jira-token", self.jira_token,
                    "--confluence-url", self.confluence_url,
                    "--confluence-username", self.confluence_username,
                    "--confluence-token", self.confluence_token
                ]
                
                logger.info(f"MCP command: uvx mcp-atlassian --jira-url {self.jira_url} [credentials redacted]")
                
                server_params = StdioServerParameters(
                    command=command_parts[0],  # "uvx"
                    args=command_parts[1:]     # ["mcp-atlassian", "--jira-url", ...]
                )
                
                try:
                    logger.info("Creating stdio client context...")
                    self._session_context = stdio_client(server_params)
                    
                    logger.info("Entering session context...")
                    read_stream, write_stream = await asyncio.wait_for(
                        self._session_context.__aenter__(),
                        timeout=45.0  # Allow time for uvx to download and start
                    )
                    
                    logger.info("Creating ClientSession...")
                    self._session = ClientSession(read_stream, write_stream)
                    
                    logger.info("Initializing session...")
                    await asyncio.wait_for(
                        self._session.initialize(),
                        timeout=30.0
                    )
                    
                    logger.info("MCP Atlassian session established successfully")
                    return self._session
                    
                except asyncio.TimeoutError:
                    logger.error(f"MCP session creation timed out (attempt {retry_count + 1})")
                    await self._cleanup_session()
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        await asyncio.sleep(2)  # Wait before retry
                    continue
                
            except Exception as e:
                logger.error(f"Failed to create MCP session (attempt {retry_count + 1}): {e}")
                await self._cleanup_session()
                retry_count += 1
                
                if retry_count < max_retries:
                    await asyncio.sleep(2)
                    continue
                else:
                    break
        
        logger.error(f"Failed to establish MCP session after {max_retries} attempts")
        return None
    
    async def _cleanup_session(self):
        """Clean up MCP session."""
        try:
            if self._session:
                # Note: MCP ClientSession may not have a close() method
                self._session = None
                logger.debug("MCP session cleared")
            
            if self._session_context:
                try:
                    await self._session_context.__aexit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Session context cleanup error (expected): {e}")
                self._session_context = None
                logger.debug("MCP session context cleaned up")
                
        except Exception as e:
            logger.debug(f"Session cleanup error (non-critical): {e}")
    
    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP tool directly with timeout and error handling.
        
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
        
        session = await self._get_session()
        if not session:
            return {
                "error": "Failed to establish MCP session",
                "mcp_tool": tool_name,
                "response_time": round(time.time() - start_time, 2)
            }
        
        try:
            logger.info(f"Executing MCP tool: {tool_name} with args: {arguments}")
            
            # Execute tool through MCP session
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=30.0
            )
            
            response_time = round(time.time() - start_time, 2)
            logger.info(f"MCP tool {tool_name} completed in {response_time}s")
            
            # Add metadata to response
            if isinstance(result, dict):
                result["mcp_tool"] = tool_name
                result["response_time"] = response_time
                result["source"] = "mcp_server"
                return result
            else:
                return {
                    "result": result,
                    "mcp_tool": tool_name,
                    "response_time": response_time,
                    "source": "mcp_server"
                }
                
        except asyncio.TimeoutError:
            logger.error(f"MCP tool {tool_name} timed out after 30s")
            return {
                "error": f"Tool execution timed out after 30 seconds",
                "mcp_tool": tool_name,
                "response_time": round(time.time() - start_time, 2)
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
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_session()