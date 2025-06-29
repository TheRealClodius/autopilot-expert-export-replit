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

# Import trace manager for LangSmith monitoring
try:
    from services.trace_manager import TraceManager
    TRACE_MANAGER_AVAILABLE = True
except ImportError:
    TRACE_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    HTTP-based Atlassian integration tool.
    Connects to running MCP server via SSE transport.
    """
    
    def __init__(self, trace_manager=None):
        """Initialize HTTP-based Atlassian tool"""
        self.mcp_server_url = settings.MCP_SERVER_URL
        self.sse_endpoint = f"{self.mcp_server_url}/mcp/sse"
        self.session_id = None
        self.messages_endpoint = None
        
        # Initialize trace manager for LangSmith monitoring
        if trace_manager and TRACE_MANAGER_AVAILABLE:
            self.trace_manager = trace_manager
        elif TRACE_MANAGER_AVAILABLE:
            try:
                self.trace_manager = TraceManager()
            except Exception:
                self.trace_manager = None
        else:
            self.trace_manager = None
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
    
    def _map_tool_name(self, our_tool_name: str) -> str:
        """Map our tool names to official MCP tool names
        
        Based on MCP server logs, the actual tool names are prefixed:
        - confluence_search, confluence_get_page, confluence_create_page
        - jira_search, jira_get_issue, jira_create_issue
        """
        # Our tool names are already correct!
        # The MCP server uses prefixed names, not the generic names from the documentation
        return our_tool_name
    
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
            headers = {
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache'
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get SSE endpoint to obtain session info
                response = await client.get(self.sse_endpoint, headers=headers)
                
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
        
        # Start timing for LangSmith trace
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.debug(f"Executing MCP tool: {tool_name} with args: {arguments}")
            logger.debug(f"Using MCP server URL: {self.mcp_server_url}")
            
            # Use FastMCP streamable-http transport with session management
            # First create a session, then send the tool call
            base_endpoint = f"{self.mcp_server_url}/mcp"
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            # Deployment-aware connectivity with retry logic
            mcp_urls_to_try = [
                self.mcp_server_url,  # Configured URL first
                "http://localhost:8001",  # Standard fallback
                "http://127.0.0.1:8001",  # Alternative localhost
                "http://0.0.0.0:8001"  # Wildcard fallback
            ]
            
            working_url = None
            last_error = None
            
            for url_to_test in mcp_urls_to_try:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        # Test basic connectivity
                        health_response = await client.get(f"{url_to_test}/healthz")
                        if health_response.status_code == 200:
                            working_url = url_to_test
                            logger.info(f"MCP server connectivity verified at: {working_url}")
                            break
                except Exception as e:
                    last_error = e
                    logger.debug(f"Failed to connect to {url_to_test}: {e}")
                    continue
            
            if not working_url:
                logger.error(f"MCP server connectivity test failed: {last_error}")
                return {
                    "error": "mcp_server_unreachable", 
                    "message": f"Cannot reach MCP server. Tried URLs: {', '.join(mcp_urls_to_try)}. Last error: {last_error}"
                }
            
            # Use the working URL for actual MCP communication
            base_endpoint = f"{working_url}/mcp"
            
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                # Step 1: Create session via redirect handling
                session_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "atlassian-client",
                            "version": "1.0.0"
                        }
                    }
                }
                
                logger.debug(f"Initializing MCP session with request: {session_request}")
                session_response = await client.post(base_endpoint, json=session_request, headers=headers)
                
                # Handle redirect to session-specific endpoint
                if session_response.status_code == 307:
                    redirect_url = session_response.headers.get("location")
                    if redirect_url:
                        logger.debug(f"Following redirect to session URL: {redirect_url}")
                        session_response = await client.post(redirect_url, json=session_request, headers=headers)
                
                if session_response.status_code != 200:
                    logger.error(f"Failed to initialize MCP session: {session_response.status_code} - {session_response.text}")
                    return {
                        "error": f"session_init_failed_{session_response.status_code}",
                        "message": f"Failed to initialize MCP session: {session_response.text}"
                    }
                
                # Extract session info from SSE response
                session_id = session_response.headers.get("mcp-session-id")
                session_url = session_response.url
                response_text = session_response.text
                
                # Parse SSE response to extract JSON result
                logger.debug(f"Session response text: {response_text}")
                session_result = None
                for line in response_text.split('\n'):
                    line = line.strip()
                    if line.startswith('data: '):
                        try:
                            json_data = line[6:]  # Remove 'data: ' prefix
                            session_result = json.loads(json_data)
                            logger.debug(f"Parsed session result: {session_result}")
                            break
                        except json.JSONDecodeError as e:
                            logger.debug(f"JSON decode error for line '{line}': {e}")
                            continue
                
                if not session_result:
                    logger.error("Failed to parse session initialization response")
                    return {
                        "error": "session_parse_failed",
                        "message": "Could not parse session initialization response"
                    }
                
                logger.debug(f"Session established: ID={session_id}, URL={session_url}")
                
                # Step 2: Send initialized notification to complete handshake
                initialized_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                # Add session ID to headers if available
                initialized_headers = headers.copy()
                if session_id:
                    initialized_headers["mcp-session-id"] = session_id
                
                logger.debug(f"Sending initialized notification: {initialized_request}")
                init_response = await client.post(str(session_url), json=initialized_request, headers=initialized_headers)
                logger.debug(f"Initialized response: {init_response.status_code}")
                
                # Wait for the initialization to complete before proceeding
                # 202 Accepted is the correct response for notifications
                if init_response.status_code not in [200, 202]:
                    logger.error(f"Failed to send initialized notification: {init_response.status_code}")
                    return {
                        "error": "initialization_failed",
                        "message": f"Failed to complete MCP handshake: {init_response.text}"
                    }
                
                logger.debug(f"MCP handshake completed successfully (status: {init_response.status_code})")
                
                # Step 3: Call the tool using the session URL with session headers
                tool_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
                
                # Add session ID to headers if available
                tool_headers = headers.copy()
                if session_id:
                    tool_headers["mcp-session-id"] = session_id
                
                # Map our tool name to the official MCP tool name
                mapped_tool_name = self._map_tool_name(tool_name)
                logger.debug(f"Tool mapping: {tool_name} → {mapped_tool_name}")
                
                # Update the request with the mapped tool name
                tool_request["params"]["name"] = mapped_tool_name
                
                logger.debug(f"Calling MCP tool with request: {tool_request}")
                response = await client.post(str(session_url), json=tool_request, headers=tool_headers)
                
                logger.debug(f"Tool call response status: {response.status_code}")
                logger.debug(f"Tool call response headers: {response.headers}")
                
                if response.status_code == 200:
                    # Handle SSE response for tool calls too
                    if response.headers.get("content-type", "").startswith("text/event-stream"):
                        response_text = response.text
                        logger.debug(f"Tool response SSE text: {response_text}")
                        
                        # Parse SSE response
                        result_data = None
                        for line in response_text.split('\n'):
                            if line.startswith('data: '):
                                try:
                                    json_data = line[6:]  # Remove 'data: ' prefix
                                    result_data = json.loads(json_data)
                                    break
                                except json.JSONDecodeError:
                                    continue
                        
                        if not result_data:
                            logger.error("Failed to parse tool response from SSE")
                            return {
                                "error": "tool_response_parse_failed",
                                "message": "Could not parse tool response from SSE stream"
                            }
                    else:
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
                        # Calculate execution time and log to LangSmith
                        end_time = asyncio.get_event_loop().time()
                        duration_ms = (end_time - start_time) * 1000
                        
                        # Log successful MCP tool operation to LangSmith
                        if self.trace_manager:
                            await self.trace_manager.log_mcp_tool_operation(
                                tool_name=tool_name,
                                arguments=arguments,
                                results=mcp_result,
                                duration_ms=duration_ms
                            )
                        
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
            
            # Enhanced error logging for production debugging
            import traceback
            full_traceback = traceback.format_exc()
            
            error_data = {
                'tool_name': tool_name,
                'arguments': arguments,
                'error_message': error_msg,
                'exception_type': type(e).__name__,
                'stack_trace': full_traceback,
                'mcp_server_url': self.mcp_server_url,
                'tool_available': self.available
            }
            
            logger.error(f"ATLASSIAN_TOOL_ERROR: {json.dumps(error_data, default=str)}")
            logger.error(error_msg)
            logger.error(f"Full traceback: {full_traceback}")
            
            # For specific connection-related errors, provide deployment-aware error messages
            if "Connection" in str(e) or "timeout" in str(e).lower() or "refused" in str(e).lower():
                return {
                    "error": "connection_failed",
                    "message": f"Cannot connect to MCP server at {self.mcp_server_url}. In deployment, set MCP_SERVER_URL to the correct endpoint for your environment.",
                    "exception_type": type(e).__name__,
                    "deployment_help": "Try: export MCP_SERVER_URL='http://your-deployment-host:8001'"
                }
            elif "handshake" in str(e).lower() or "initialized" in str(e).lower():
                return {
                    "error": "mcp_handshake_failed",
                    "message": "MCP protocol handshake failed. The server may be starting up.",
                    "exception_type": type(e).__name__,
                    "retry_suggested": True
                }
            elif "All connection attempts failed" in str(e):
                return {
                    "error": "mcp_server_unreachable",
                    "message": f"MCP server unreachable at {self.mcp_server_url}. This is a deployment network configuration issue.",
                    "exception_type": type(e).__name__,
                    "deployment_help": "Check MCP_SERVER_URL environment variable and ensure MCP server is running"
                }
            else:
                # Calculate execution time and log error to LangSmith
                end_time = asyncio.get_event_loop().time()
                duration_ms = (end_time - start_time) * 1000
                
                # Log failed MCP tool operation to LangSmith
                if self.trace_manager:
                    await self.trace_manager.log_mcp_tool_operation(
                        tool_name=tool_name,
                        arguments=arguments,
                        duration_ms=duration_ms,
                        error=error_msg
                    )
                
                return {
                    "error": "execution_error",
                    "message": error_msg,
                    "exception_type": type(e).__name__,
                    "debug_info": {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "mcp_server_url": self.mcp_server_url,
                        "tool_available": self.available,
                        "stack_trace": full_traceback
                    }
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