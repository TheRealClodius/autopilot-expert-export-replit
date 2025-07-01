"""
Atlassian Guru - Specialized agent for all Atlassian MCP server interactions.
Acts as a "black box" tool for the orchestrator, encapsulating all Jira/Confluence logic.
"""

import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log, after_log

from config import settings

logger = logging.getLogger(__name__)

class AtlassianToolbelt:
    """
    Specialized agent that acts as a black box for all Atlassian operations.
    The orchestrator doesn't need to know anything about Jira/Confluence specifics.
    """
    
    def __init__(self):
        """Initialize the Atlassian specialist agent"""
        self.mcp_server_url = settings.DEPLOYMENT_AWARE_MCP_URL.strip()
        self.session_id = None
        self.messages_endpoint = None
        self.dynamic_prompt = None
        self.available_tools = []
        
        # Initialize HTTP client with connection pooling
        self.http_client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        logger.info(f"AtlassianToolbelt initialized with MCP server: {self.mcp_server_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close HTTP client and cleanup"""
        if hasattr(self, 'http_client') and self.http_client:
            await self.http_client.aclose()
            logger.debug("AtlassianToolbelt HTTP client closed")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )
    async def _initialize_mcp_connection(self) -> bool:
        """Initialize connection to MCP server and discover capabilities"""
        try:
            # Health check first
            health_response = await self.http_client.get(f"{self.mcp_server_url}/health")
            if health_response.status_code != 200:
                logger.warning(f"MCP server health check failed: {health_response.status_code}")
                return False
            
            logger.info("MCP server health check passed, skipping initialize method (not supported)")
            
            # Discover available tools directly (skip initialize since this server doesn't support it)
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            tools_response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=tools_request)
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                if "result" in tools_data and "tools" in tools_data["result"]:
                    self.available_tools = tools_data["result"]["tools"]
                    logger.info(f"Discovered {len(self.available_tools)} tools from MCP server")
                    
                    # Log available Atlassian tools
                    atlassian_tools = [t for t in self.available_tools if any(keyword in t.get('name', '').lower() for keyword in ['jira', 'confluence', 'atlassian'])]
                    logger.info(f"Found {len(atlassian_tools)} Atlassian tools: {[t.get('name') for t in atlassian_tools]}")
                    
                    # Get dynamic prompt if available
                    await self._fetch_dynamic_prompt()
                    return True
            
            logger.warning("Failed to discover tools from MCP server")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing MCP connection: {e}")
            return False
    
    async def _fetch_dynamic_prompt(self):
        """Fetch dynamic prompt from MCP server if available"""
        try:
            # Check if server has dynamic prompt capability
            prompt_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "prompts/list",
                "params": {}
            }
            
            response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=prompt_request)
            if response.status_code == 200:
                prompt_data = response.json()
                if "result" in prompt_data and "prompts" in prompt_data["result"]:
                    prompts = prompt_data["result"]["prompts"]
                    
                    # Look for dynamic system prompt
                    for prompt in prompts:
                        if prompt.get("name") == "dynamic_system_prompt":
                            # Get the actual prompt content
                            get_prompt_request = {
                                "jsonrpc": "2.0",
                                "id": 4,
                                "method": "prompts/get",
                                "params": {
                                    "name": "dynamic_system_prompt"
                                }
                            }
                            
                            prompt_response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=get_prompt_request)
                            if prompt_response.status_code == 200:
                                prompt_content = prompt_response.json()
                                if "result" in prompt_content:
                                    self.dynamic_prompt = prompt_content["result"]
                                    logger.info("Retrieved dynamic system prompt from MCP server")
                                    break
                                    
        except Exception as e:
            logger.debug(f"Dynamic prompt not available or failed to fetch: {e}")
    
    async def execute_task(self, task: str) -> Dict[str, Any]:
        """
        Execute an Atlassian-related task using the MCP server.
        This is the main interface method that the orchestrator will call.
        
        Args:
            task: Natural language description of what to do
            
        Returns:
            Dictionary with execution results, status, and any data found
        """
        try:
            # Initialize connection if not already done
            if not self.available_tools:
                connection_success = await self._initialize_mcp_connection()
                if not connection_success:
                    return {
                        "status": "error",
                        "message": "Could not connect to Atlassian services",
                        "data": None
                    }
            
            # Use the dynamic prompt to understand what to do
            if self.dynamic_prompt:
                # Let the MCP server's AI determine the best approach
                result = await self._execute_with_dynamic_prompt(task)
            else:
                # Fallback to direct tool execution
                result = await self._execute_with_direct_tools(task)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing Atlassian task: {e}")
            return {
                "status": "error",
                "message": f"Failed to execute task: {str(e)}",
                "data": None
            }
    
    async def _execute_with_dynamic_prompt(self, task: str) -> Dict[str, Any]:
        """Execute task using the MCP server's dynamic prompt capabilities"""
        try:
            # Call the MCP server's AI to handle the task
            ai_request = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "ai/complete",
                "params": {
                    "prompt": f"{self.dynamic_prompt}\n\nUser request: {task}",
                    "tools": [tool["name"] for tool in self.available_tools]
                }
            }
            
            response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=ai_request)
            if response.status_code == 200:
                ai_data = response.json()
                if "result" in ai_data:
                    return {
                        "status": "success",
                        "message": "Task completed using AI capabilities",
                        "data": ai_data["result"],
                        "execution_method": "dynamic_prompt"
                    }
            
            # If AI completion fails, fall back to direct tools
            return await self._execute_with_direct_tools(task)
            
        except Exception as e:
            logger.warning(f"Dynamic prompt execution failed, falling back to direct tools: {e}")
            return await self._execute_with_direct_tools(task)
    
    async def _execute_with_direct_tools(self, task: str) -> Dict[str, Any]:
        """Execute task using direct tool calls (fallback method)"""
        try:
            # Simple task classification and tool selection
            task_lower = task.lower()
            
            if any(keyword in task_lower for keyword in ["search", "find", "look", "get"]):
                if "confluence" in task_lower or "documentation" in task_lower or "page" in task_lower:
                    return await self._search_confluence(task)
                elif "jira" in task_lower or "issue" in task_lower or "ticket" in task_lower:
                    return await self._search_jira(task)
                else:
                    # Try both and return combined results
                    jira_result = await self._search_jira(task)
                    confluence_result = await self._search_confluence(task)
                    
                    return {
                        "status": "success",
                        "message": "Searched both Jira and Confluence",
                        "data": {
                            "jira": jira_result.get("data"),
                            "confluence": confluence_result.get("data")
                        },
                        "execution_method": "direct_tools_combined"
                    }
            
            elif any(keyword in task_lower for keyword in ["create", "add", "new"]):
                if "issue" in task_lower or "ticket" in task_lower or "jira" in task_lower:
                    return await self._create_jira_issue(task)
                else:
                    return {
                        "status": "error",
                        "message": "Creating Confluence pages not yet supported via direct tools",
                        "data": None
                    }
            
            else:
                # Default to search
                return await self._search_both(task)
                
        except Exception as e:
            logger.error(f"Direct tool execution failed: {e}")
            return {
                "status": "error",
                "message": f"Tool execution failed: {str(e)}",
                "data": None
            }
    
    async def _search_jira(self, query: str) -> Dict[str, Any]:
        """Search Jira issues"""
        try:
            tool_request = {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "get_jira_issues",
                    "arguments": {
                        "jql": f"text ~ \"{query}\" OR summary ~ \"{query}\"",
                        "limit": 10
                    }
                }
            }
            
            response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=tool_request)
            if response.status_code == 200:
                result_data = response.json()
                return {
                    "status": "success",
                    "message": "Jira search completed",
                    "data": result_data.get("result"),
                    "source": "jira"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Jira search failed: {response.status_code}",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"Jira search error: {e}")
            return {
                "status": "error",
                "message": f"Jira search error: {str(e)}",
                "data": None
            }
    
    async def _search_confluence(self, query: str) -> Dict[str, Any]:
        """Search Confluence pages"""
        try:
            tool_request = {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "get_confluence_pages",
                    "arguments": {
                        "query": query,
                        "limit": 10
                    }
                }
            }
            
            response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=tool_request)
            if response.status_code == 200:
                result_data = response.json()
                return {
                    "status": "success",
                    "message": "Confluence search completed",
                    "data": result_data.get("result"),
                    "source": "confluence"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Confluence search failed: {response.status_code}",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"Confluence search error: {e}")
            return {
                "status": "error",
                "message": f"Confluence search error: {str(e)}",
                "data": None
            }
    
    async def _search_both(self, query: str) -> Dict[str, Any]:
        """Search both Jira and Confluence"""
        jira_task = self._search_jira(query)
        confluence_task = self._search_confluence(query)
        
        jira_result, confluence_result = await asyncio.gather(jira_task, confluence_task, return_exceptions=True)
        
        return {
            "status": "success",
            "message": "Searched both Jira and Confluence",
            "data": {
                "jira": jira_result.get("data") if isinstance(jira_result, dict) else None,
                "confluence": confluence_result.get("data") if isinstance(confluence_result, dict) else None
            },
            "execution_method": "direct_tools_both"
        }
    
    async def _create_jira_issue(self, task: str) -> Dict[str, Any]:
        """Create a new Jira issue"""
        try:
            # Simple parsing for creation (this could be enhanced)
            tool_request = {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "create_jira_issue",
                    "arguments": {
                        "project_key": "AUTOPILOT",  # Default project
                        "issue_type": "Task",
                        "summary": task,
                        "description": f"Task created via AtlassianToolbelt: {task}"
                    }
                }
            }
            
            response = await self.http_client.post(f"{self.mcp_server_url}/mcp", json=tool_request)
            if response.status_code == 200:
                result_data = response.json()
                return {
                    "status": "success",
                    "message": "Jira issue created",
                    "data": result_data.get("result"),
                    "source": "jira_create"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Jira issue creation failed: {response.status_code}",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"Jira creation error: {e}")
            return {
                "status": "error",
                "message": f"Jira creation error: {str(e)}",
                "data": None
            }
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Return information about what this toolbelt can do"""
        if not self.available_tools:
            await self._initialize_mcp_connection()
        
        return {
            "available_tools": [tool.get("name", "unknown") for tool in self.available_tools],
            "capabilities": [
                "Search Jira issues",
                "Search Confluence pages", 
                "Create Jira issues",
                "Get issue details",
                "Get page details"
            ],
            "server_url": self.mcp_server_url,
            "has_dynamic_prompt": self.dynamic_prompt is not None
        }
    
    async def health_check(self) -> bool:
        """Check if the Atlassian services are available"""
        try:
            response = await self.http_client.get(f"{self.mcp_server_url}/health")
            return response.status_code == 200
        except:
            return False