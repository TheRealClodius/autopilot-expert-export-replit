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
            
            # Use HTTP/JSON transport directly to FastMCP server
            # FastMCP supports both SSE and streamable-http transports
            mcp_endpoint = f"{self.mcp_server_url}/mcp"
            
            # Build MCP protocol request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(mcp_endpoint, json=mcp_request, headers=headers)
                
                if response.status_code == 200:
                    result_data = response.json()
                    
                    # Check for MCP protocol error
                    if "error" in result_data:
                        logger.error(f"MCP protocol error: {result_data['error']}")
                        return {
                            "error": "mcp_protocol_error",
                            "message": str(result_data["error"])
                        }
                    
                    # Extract result from MCP response
                    mcp_result = result_data.get("result", {})
                    content = mcp_result.get("content", [])
                    
                    logger.debug(f"MCP tool {tool_name} completed successfully with {len(content)} content items")
                    
                    # Parse content from MCP response
                    if content and isinstance(content, list):
                        # Look for text content with JSON data
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_content = item.get("text", "")
                                try:
                                    # Try to parse as JSON
                                    import json
                                    parsed_data = json.loads(text_content)
                                    return {
                                        "success": True,
                                        "result": parsed_data
                                    }
                                except json.JSONDecodeError:
                                    # Return as formatted text
                                    return {
                                        "success": True,
                                        "result": {"text_content": text_content}
                                    }
                        
                        # If no text content found, return content array
                        return {
                            "success": True,
                            "result": {"content": content}
                        }
                    else:
                        # Return basic success
                        return {
                            "success": True,
                            "result": mcp_result
                        }
                else:
                    logger.error(f"HTTP error calling MCP server: {response.status_code} - {response.text}")
                    return {
                        "error": f"http_error_{response.status_code}",
                        "message": f"MCP server returned {response.status_code}: {response.text}"
                    }
                    
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