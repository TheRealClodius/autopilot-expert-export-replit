"""
Atlassian Tool - Direct MCP integration using the mcp-atlassian package.
Modern LLM tool interface that communicates directly with MCP commands.
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import settings
from services.trace_manager import trace_manager
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    Direct MCP Atlassian integration tool.
    Orchestrator communicates directly with MCP commands for maximum efficiency.
    """
    
    def __init__(self):
        """Initialize direct MCP Atlassian tool."""
        # Configuration
        self.jira_url = settings.ATLASSIAN_JIRA_URL
        self.jira_username = settings.ATLASSIAN_JIRA_USERNAME
        self.jira_token = settings.ATLASSIAN_JIRA_TOKEN
        self.confluence_url = settings.ATLASSIAN_CONFLUENCE_URL
        self.confluence_username = settings.ATLASSIAN_CONFLUENCE_USERNAME
        self.confluence_token = settings.ATLASSIAN_CONFLUENCE_TOKEN
        
        # MCP client session
        self._session: Optional[ClientSession] = None
        self._session_context = None
        
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
            logger.info("Direct MCP Atlassian tool initialized successfully")
        else:
            logger.warning("Atlassian tool unavailable - missing credentials")
    
    async def _get_session(self) -> Optional[ClientSession]:
        """Get or create MCP client session."""
        if self._session is not None:
            return self._session
        
        if not self.available:
            logger.error("Cannot create MCP session - credentials not available")
            return None
        
        try:
            # Build command for mcp-atlassian server
            command_parts = [
                "uvx", 
                "mcp-atlassian",
                "--jira-url", self.jira_url,
                "--jira-username", self.jira_username,
                "--jira-token", self.jira_token,
                "--confluence-url", self.confluence_url,
                "--confluence-username", self.confluence_username,
                "--confluence-token", self.confluence_token
            ]
            
            # Create MCP session using stdio client
            from mcp.client.stdio import StdioServerParameters
            server_params = StdioServerParameters(
                command=command_parts[0],  # "uvx"
                args=command_parts[1:]     # ["mcp-atlassian", "--jira-url", ...]
            )
            self._session_context = stdio_client(server_params)
            read_stream, write_stream = await self._session_context.__aenter__()
            
            self._session = ClientSession(read_stream, write_stream)
            await self._session.initialize()
            
            logger.info("MCP Atlassian session established successfully")
            return self._session
            
        except Exception as e:
            logger.error(f"Failed to create MCP session: {e}")
            await self._cleanup_session()
            return None
    
    async def _cleanup_session(self):
        """Clean up MCP session."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing MCP session: {e}")
            self._session = None
        
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up session context: {e}")
            self._session_context = None
    
    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP tool directly - modern LLM interface.
        
        Args:
            tool_name: MCP tool name (jira_search, confluence_search, etc.)
            arguments: Direct MCP arguments
            
        Returns:
            MCP tool response
        """
        if not self.available:
            return {
                "error": "Atlassian tool not configured",
                "message": "Atlassian credentials not available"
            }
        
        if tool_name not in self.available_tools:
            return {
                "error": f"Unknown MCP tool: {tool_name}",
                "available_tools": self.available_tools
            }
        
        start_time = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_agent_operation(
                    "atlassian_mcp",
                    f"{tool_name}: {arguments}",
                    json.dumps({"tool": tool_name, "arguments": arguments}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            session = await self._get_session()
            if not session:
                return {"error": "MCP session not available"}
            
            # Direct MCP tool call
            result = await session.call_tool(tool_name, arguments)
            
            # Extract content from MCP response
            content_list = getattr(result, 'content', [])
            if content_list:
                content = content_list[0]
                if hasattr(content, 'text'):
                    try:
                        parsed_result = json.loads(content.text)
                        # Add metadata
                        parsed_result["mcp_tool"] = tool_name
                        parsed_result["response_time"] = round(time.time() - start_time, 2)
                        return parsed_result
                    except json.JSONDecodeError:
                        return {
                            "text": content.text,
                            "mcp_tool": tool_name,
                            "response_time": round(time.time() - start_time, 2)
                        }
                else:
                    return {
                        "content": str(content),
                        "mcp_tool": tool_name,
                        "response_time": round(time.time() - start_time, 2)
                    }
            else:
                return {
                    "result": str(result),
                    "mcp_tool": tool_name,
                    "response_time": round(time.time() - start_time, 2)
                }
                
        except Exception as e:
            error_msg = f"MCP tool {tool_name} failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "mcp_tool": tool_name}
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_session()