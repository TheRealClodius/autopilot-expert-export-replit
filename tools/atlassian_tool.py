"""
HTTP-based Atlassian Tool

Connects to the running MCP Atlassian server via SSE transport
using the proper MCP client protocol.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, Optional, List
import httpx
from mcp.client.sse import sse_client
from config import settings

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    HTTP-based Atlassian integration tool.
    Connects to running MCP server via SSE transport.
    """
    
    def __init__(self):
        """Initialize HTTP-based Atlassian tool"""
        self.mcp_server_url = "http://localhost:8001"
        self.sse_endpoint = f"{self.mcp_server_url}/sse"
        self.session_id = None
        self.messages_endpoint = None
        self.available_tools = [
            'jira_search',
            'jira_get', 
            'jira_create',
            'confluence_search',
            'confluence_get'
        ]
        
        # Check if credentials are available
        self.available = self._check_credentials()
        
        if self.available:
            logger.info("HTTP-based Atlassian tool initialized successfully")
        else:
            logger.warning("Atlassian tool initialized but credentials missing")
    
    def _check_credentials(self) -> bool:
        """Check if required Atlassian credentials are available"""
        required_vars = [
            settings.ATLASSIAN_CONFLUENCE_URL,
            settings.ATLASSIAN_CONFLUENCE_USERNAME,
            settings.ATLASSIAN_CONFLUENCE_TOKEN,
            settings.ATLASSIAN_JIRA_URL,
            settings.ATLASSIAN_JIRA_USERNAME,
            settings.ATLASSIAN_JIRA_TOKEN
        ]
        
        return all(var for var in required_vars)
    
    async def _get_session_endpoint(self) -> str:
        """Get the messages endpoint from SSE initialization"""
        if self.messages_endpoint:
            return self.messages_endpoint
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get SSE endpoint to obtain session info
                response = await client.get(self.sse_endpoint)
                
                # Parse the SSE response to get the endpoint
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        endpoint_path = line[6:]  # Remove 'data: ' prefix
                        self.messages_endpoint = f"{self.mcp_server_url}{endpoint_path}"
                        logger.debug(f"Got messages endpoint: {self.messages_endpoint}")
                        return self.messages_endpoint
                        
                raise Exception("Could not parse SSE response for endpoint")
                
        except Exception as e:
            logger.error(f"Error getting SSE session endpoint: {e}")
            raise
    
    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP tool via SSE client to running server
        
        Args:
            tool_name: Name of the MCP tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self.available:
            return {
                "error": "Atlassian credentials not configured",
                "message": "Please configure ATLASSIAN_* environment variables"
            }
        
        try:
            logger.debug(f"Executing MCP tool: {tool_name} with args: {arguments}")
            
            # Use proper MCP SSE client
            async with sse_client(self.sse_endpoint) as (read, write):
                # Call the tool
                result = await write.call_tool(tool_name, arguments)
                
                logger.debug(f"MCP tool {tool_name} completed successfully")
                
                # Extract content from MCP result
                if hasattr(result, 'content') and result.content:
                    # Convert content list to dictionary format
                    content_dict = {}
                    for item in result.content:
                        if hasattr(item, 'type') and hasattr(item, 'text'):
                            if item.type == 'text':
                                content_dict['text'] = item.text
                        elif hasattr(item, 'data'):
                            content_dict.update(item.data if isinstance(item.data, dict) else {})
                    
                    return content_dict if content_dict else {"result": "success"}
                else:
                    return {"result": "success"}
                    
        except Exception as e:
            error_msg = f"Error executing MCP tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            return {
                "error": "execution_error",
                "message": error_msg
            }
    
    async def list_tools(self) -> List[str]:
        """List available MCP tools"""
        return self.available_tools
    
    async def check_server_health(self) -> bool:
        """Check if MCP server is healthy and responding"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.mcp_server_url}/healthz")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP server health check failed: {e}")
            return False