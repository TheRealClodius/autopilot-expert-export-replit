"""
Simplified HTTP-based Atlassian Tool

Connects to the MCP Atlassian server via direct HTTP tool calls,
bypassing complex session management.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
import httpx
from config import settings

# Setup logging
logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    Simplified HTTP-based Atlassian integration tool.
    Connects to MCP server via direct tool calls.
    """

    def __init__(self, trace_manager=None):
        """Initialize simplified HTTP-based Atlassian tool"""
        self.available_tools = []
        self.mcp_server_url = self._get_mcp_server_url()
        self.trace_manager = trace_manager
        logger.info(f"Using configured MCP server URL: {self.mcp_server_url}")
        logger.info("HTTP-based Atlassian tool initialized successfully")

    def _get_mcp_server_url(self) -> str:
        """Get the MCP server URL from configuration"""
        url = settings.MCP_SERVER_URL or "https://remote-mcp-server-andreiclodius.replit.app"
        # Ensure URL has proper protocol
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        return url.rstrip('/')

    def _check_credentials(self) -> bool:
        """Check if required Atlassian credentials are available"""
        required_vars = [
            "ATLASSIAN_JIRA_URL",
            "ATLASSIAN_JIRA_USERNAME", 
            "ATLASSIAN_JIRA_TOKEN",
            "ATLASSIAN_CONFLUENCE_URL",
            "ATLASSIAN_CONFLUENCE_USERNAME",
            "ATLASSIAN_CONFLUENCE_TOKEN"
        ]
        
        for var in required_vars:
            if not getattr(settings, var, None):
                logger.warning(f"Missing required environment variable: {var}")
                return False
        return True

    async def discover_available_tools(self) -> List[Dict[str, Any]]:
        """Dynamically discover available tools from the MCP server"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get tools via MCP list tools call
                response = await client.post(
                    f"{self.mcp_server_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "tools/list",
                        "params": {}
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    tools_data = result.get("result", {}).get("tools", [])
                    
                    # Extract tool names for our available_tools list
                    self.available_tools = [tool.get("name", "") for tool in tools_data if tool.get("name")]
                    
                    logger.info(f"Discovered {len(self.available_tools)} Atlassian tools: {self.available_tools}")
                    return tools_data
                else:
                    logger.error(f"Failed to discover tools: {response.status_code}")
                    # Fallback to known tools
                    self.available_tools = ["get_jira_issues", "create_jira_issue", "get_confluence_pages", "create_confluence_page", "get_atlassian_status"]
                    return []
                    
        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
            # Fallback to known tools
            self.available_tools = ["get_jira_issues", "create_jira_issue", "get_confluence_pages", "create_confluence_page", "get_atlassian_status"]
            return []

    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP tool via direct HTTP call to running server
        
        Args:
            tool_name: Name of the MCP tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        # Check credentials before attempting to use tools
        if not self._check_credentials():
            return {
                "error": "Atlassian credentials not configured",
                "message": "Please configure ATLASSIAN_* environment variables"
            }
        
        # Start timing for LangSmith trace
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.debug(f"Executing MCP tool: {tool_name} with args: {arguments}")
            
            # Direct tool call without session initialization
            base_endpoint = f"{self.mcp_server_url}/mcp"
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            logger.info(f"Calling direct MCP tool at: {self.mcp_server_url}")
            
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                tool_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
                
                logger.debug(f"Calling MCP tool with request: {tool_request}")
                response = await client.post(base_endpoint, json=tool_request, headers=headers)
                
                logger.debug(f"Tool call response status: {response.status_code}")
                logger.debug(f"Tool call response: {response.text[:500]}...")
                
                if response.status_code == 200:
                    result_data = response.json()
                    
                    # Check for MCP protocol error
                    if "error" in result_data and result_data["error"] is not None:
                        error_info = result_data['error']
                        logger.error(f"MCP protocol error: {error_info}")
                        return {
                            "error": "mcp_protocol_error",
                            "message": str(error_info)
                        }
                    
                    # Extract result from MCP response
                    mcp_result = result_data.get("result", {})
                    
                    if mcp_result:
                        logger.debug(f"MCP tool {tool_name} completed successfully")
                        
                        # Calculate execution time and log to LangSmith
                        end_time = asyncio.get_event_loop().time()
                        duration_ms = (end_time - start_time) * 1000
                        
                        # Log successful MCP tool operation to LangSmith
                        if self.trace_manager:
                            await self.trace_manager.log_mcp_tool_operation(
                                tool_name=tool_name,
                                arguments=arguments,
                                result=mcp_result,
                                duration_ms=duration_ms,
                                success=True
                            )
                        
                        # Return success with the result
                        return {
                            "success": True,
                            "result": mcp_result
                        }
                    else:
                        logger.warning(f"MCP tool {tool_name} returned empty result")
                        return {
                            "success": True,
                            "result": {"message": "Tool executed successfully but returned no data"}
                        }
                else:
                    logger.error(f"Tool call failed with status {response.status_code}: {response.text}")
                    return {
                        "error": f"tool_call_failed_{response.status_code}",
                        "message": f"Tool call failed: {response.text}"
                    }
        
        except Exception as e:
            logger.error(f"Exception during MCP tool execution: {str(e)}")
            
            # Calculate execution time for failed operation
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000
            
            # Log failed MCP tool operation to LangSmith
            if self.trace_manager:
                await self.trace_manager.log_mcp_tool_operation(
                    tool_name=tool_name,
                    arguments=arguments,
                    result={"error": str(e)},
                    duration_ms=duration_ms,
                    success=False
                )
            
            return {
                "error": "execution_error",
                "message": f"Failed to execute MCP tool: {str(e)}"
            }

    async def list_tools(self) -> List[str]:
        """List available MCP tools"""
        if not self.available_tools:
            await self.discover_available_tools()
        return self.available_tools

    async def check_server_health(self) -> bool:
        """Check if MCP server is healthy and responding"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.mcp_server_url}/health")
                return response.status_code == 200
        except Exception:
            return False