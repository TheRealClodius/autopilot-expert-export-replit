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
        """Get or create MCP client session with timeout and retry logic."""
        if self._session is not None:
            return self._session
        
        if not self.available:
            logger.error("Cannot create MCP session - credentials not available")
            return None
        
        # Try direct REST API fallback first to avoid MCP hangs
        logger.info("Attempting direct REST API connection test")
        rest_test = await self._test_direct_rest_connection()
        if not rest_test:
            logger.warning("Direct REST API connection failed, skipping MCP")
            return None
        
        max_retries = 2  # Reduced retries to avoid long hangs
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Creating MCP session (attempt {retry_count + 1}/{max_retries})")
                
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
                
                # Create MCP session using stdio client with tight timeouts
                from mcp.client.stdio import StdioServerParameters
                server_params = StdioServerParameters(
                    command=command_parts[0],  # "uvx"
                    args=command_parts[1:]     # ["mcp-atlassian", "--jira-url", ...]
                )
                
                # Use aggressive timeouts to prevent hangs
                try:
                    self._session_context = stdio_client(server_params)
                    read_stream, write_stream = await asyncio.wait_for(
                        self._session_context.__aenter__(),
                        timeout=20.0  # Reduced from 30s
                    )
                    
                    self._session = ClientSession(read_stream, write_stream)
                    await asyncio.wait_for(
                        self._session.initialize(),
                        timeout=10.0  # Reduced from 15s
                    )
                    
                    logger.info("MCP Atlassian session established successfully")
                    return self._session
                    
                except asyncio.TimeoutError:
                    logger.warning(f"MCP session creation timed out (attempt {retry_count + 1})")
                    await self._cleanup_session()
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        await asyncio.sleep(1)  # Reduced wait time
                    continue
                
            except Exception as e:
                logger.error(f"Failed to create MCP session (attempt {retry_count + 1}): {e}")
                await self._cleanup_session()
                retry_count += 1
                
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # Reduced wait time
                    continue
                else:
                    break
        
        logger.error(f"Failed to establish MCP session after {max_retries} attempts")
        return None
    
    async def _test_direct_rest_connection(self) -> bool:
        """Test direct REST API connection to validate credentials"""
        try:
            import httpx
            import base64
            
            # Test Jira connection
            jira_auth = base64.b64encode(f"{self.jira_username}:{self.jira_token}".encode()).decode()
            headers = {"Authorization": f"Basic {jira_auth}", "Content-Type": "application/json"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                jira_url = f"{self.jira_url}/rest/api/2/myself"
                response = await client.get(jira_url, headers=headers)
                
                if response.status_code == 200:
                    logger.info("Jira REST API connection successful")
                    return True
                else:
                    logger.warning(f"Jira REST API test failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Direct REST API test failed: {e}")
            return False
    
    async def _execute_direct_rest_api(self, tool_name: str, arguments: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Execute tool using direct REST API as fallback when MCP fails"""
        try:
            import httpx
            import base64
            
            logger.info(f"Executing {tool_name} via direct REST API fallback")
            
            if tool_name == "confluence_search":
                # Confluence search via REST API
                conf_auth = base64.b64encode(f"{self.confluence_username}:{self.confluence_token}".encode()).decode()
                headers = {"Authorization": f"Basic {conf_auth}", "Content-Type": "application/json"}
                
                query = arguments.get("query", "")
                limit = arguments.get("limit", 10)
                space_key = arguments.get("space_key")
                
                search_url = f"{self.confluence_url}/rest/api/search"
                params = {
                    "cql": f"text ~ \"{query}\"",
                    "limit": limit
                }
                if space_key:
                    params["cql"] = f"space = {space_key} AND text ~ \"{query}\""
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(search_url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        pages = []
                        for result in data.get("results", []):
                            if result.get("content", {}).get("type") == "page":
                                content = result["content"]
                                pages.append({
                                    "id": content.get("id"),
                                    "title": content.get("title"),
                                    "url": f"{self.confluence_url}{content.get('_links', {}).get('webui', '')}",
                                    "space": {
                                        "key": content.get("space", {}).get("key"),
                                        "name": content.get("space", {}).get("name")
                                    },
                                    "excerpt": result.get("excerpt", "")
                                })
                        
                        return {
                            "pages": pages,
                            "mcp_tool": tool_name,
                            "response_time": round(time.time() - start_time, 2),
                            "source": "direct_rest_api"
                        }
                    else:
                        return {"error": f"Confluence search failed: {response.status_code}", "source": "direct_rest_api"}
            
            elif tool_name == "jira_search":
                # Jira search via REST API
                jira_auth = base64.b64encode(f"{self.jira_username}:{self.jira_token}".encode()).decode()
                headers = {"Authorization": f"Basic {jira_auth}", "Content-Type": "application/json"}
                
                jql = arguments.get("jql", "")
                max_results = arguments.get("max_results", 10)
                
                search_url = f"{self.jira_url}/rest/api/2/search"
                params = {
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": "summary,status,assignee,created,updated"
                }
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(search_url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        issues = []
                        for issue in data.get("issues", []):
                            issues.append({
                                "key": issue.get("key"),
                                "id": issue.get("id"),
                                "url": f"{self.jira_url}/browse/{issue.get('key')}",
                                "fields": {
                                    "summary": issue.get("fields", {}).get("summary"),
                                    "status": issue.get("fields", {}).get("status", {}).get("name"),
                                    "assignee": issue.get("fields", {}).get("assignee", {}).get("displayName") if issue.get("fields", {}).get("assignee") else None,
                                    "created": issue.get("fields", {}).get("created"),
                                    "updated": issue.get("fields", {}).get("updated")
                                }
                            })
                        
                        return {
                            "issues": issues,
                            "total": data.get("total", len(issues)),
                            "mcp_tool": tool_name,
                            "response_time": round(time.time() - start_time, 2),
                            "source": "direct_rest_api"
                        }
                    else:
                        return {"error": f"Jira search failed: {response.status_code}", "source": "direct_rest_api"}
            
            else:
                return {"error": f"Direct REST API fallback not implemented for {tool_name}", "source": "direct_rest_api"}
                
        except Exception as e:
            error_msg = f"Direct REST API fallback failed for {tool_name}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "source": "direct_rest_api"}
    
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
        Execute MCP tool directly with timeout and error handling.
        
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
            
            # Try MCP first, then fallback to direct REST API
            session = None
            try:
                session = await asyncio.wait_for(self._get_session(), timeout=25.0)
            except asyncio.TimeoutError:
                logger.warning("MCP session creation timed out, falling back to direct REST API")
                return await self._execute_direct_rest_api(tool_name, arguments, start_time)
            
            if not session:
                logger.warning("MCP session not available, falling back to direct REST API")
                return await self._execute_direct_rest_api(tool_name, arguments, start_time)
            
            # Direct MCP tool call with timeout
            try:
                logger.info(f"Executing MCP tool {tool_name} with args: {arguments}")
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=15.0  # 15 second timeout for tool execution
                )
                logger.info(f"MCP tool {tool_name} completed successfully")
                
            except asyncio.TimeoutError:
                logger.warning(f"MCP tool {tool_name} execution timed out, falling back to direct REST API")
                return await self._execute_direct_rest_api(tool_name, arguments, start_time)
            
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
                        logger.info(f"Successfully parsed JSON response from {tool_name}")
                        return parsed_result
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse JSON response from {tool_name}, returning as text")
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
            return {"error": error_msg, "mcp_tool": tool_name, "response_time": round(time.time() - start_time, 2)}
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_session()