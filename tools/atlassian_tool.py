"""
Atlassian Tool - Integration with Atlassian services via MCP (Model Context Protocol) remote server.
Provides access to Jira issues, Confluence pages, and project management capabilities.
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from config import settings
from services.trace_manager import trace_manager
from mcp import client
from mcp.client.session import ClientSession
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    Atlassian integration tool using MCP (Model Context Protocol) remote server.
    Provides access to Jira and Confluence via the Atlassian MCP server.
    """
    
    def __init__(self):
        """Initialize Atlassian tool with MCP server configuration."""
        # Configuration for MCP server
        self.jira_url = settings.ATLASSIAN_JIRA_URL
        self.jira_username = settings.ATLASSIAN_JIRA_USERNAME
        self.jira_token = settings.ATLASSIAN_JIRA_TOKEN
        self.confluence_url = settings.ATLASSIAN_CONFLUENCE_URL
        self.confluence_username = settings.ATLASSIAN_CONFLUENCE_USERNAME
        self.confluence_token = settings.ATLASSIAN_CONFLUENCE_TOKEN
        
        # MCP client session
        self._session: Optional[ClientSession] = None
        self._process: Optional[subprocess.Popen] = None
        
        self.available = bool(
            self.jira_url and self.jira_username and self.jira_token and
            self.confluence_url and self.confluence_username and self.confluence_token
        )
        
        if self.available:
            logger.info("Atlassian tool initialized successfully")
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
            # Create MCP server command
            # For Atlassian MCP, we need to run the server with our credentials
            mcp_command = [
                "npx", 
                "@modelcontextprotocol/server-atlassian",
                "--jira-url", self.jira_url,
                "--jira-username", self.jira_username,
                "--jira-token", self.jira_token,
                "--confluence-url", self.confluence_url,
                "--confluence-username", self.confluence_username,
                "--confluence-token", self.confluence_token
            ]
            
            # Start the MCP server process
            self._process = await asyncio.create_subprocess_exec(
                *mcp_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Create client session
            self._session = ClientSession(
                read_stream=self._process.stdout,
                write_stream=self._process.stdin
            )
            
            # Initialize the session
            await self._session.initialize()
            
            logger.info("MCP session established successfully")
            return self._session
            
        except Exception as e:
            logger.error(f"Failed to create MCP session: {e}")
            await self._cleanup_session()
            return None
    
    async def _cleanup_session(self):
        """Clean up MCP session and process."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing MCP session: {e}")
            self._session = None
        
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except Exception as e:
                logger.warning(f"Error terminating MCP process: {e}")
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool via MCP client.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool response
        """
        session = await self._get_session()
        if not session:
            return {"error": "MCP session not available"}
        
        try:
            # Call the tool
            result = await session.call_tool(tool_name, arguments)
            
            # Convert result to dictionary format
            if hasattr(result, 'content'):
                if isinstance(result.content, list) and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        try:
                            return json.loads(content.text)
                        except json.JSONDecodeError:
                            return {"text": content.text}
                    else:
                        return {"content": str(content)}
                else:
                    return {"content": str(result.content)}
            else:
                return {"result": str(result)}
                
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return {"error": f"MCP tool call failed: {str(e)}"}
    
    async def search_jira_issues(
        self,
        query: str,
        max_results: int = 10,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for Jira issues using JQL via MCP.
        
        Args:
            query: JQL query or text search terms
            max_results: Maximum number of results to return
            fields: List of fields to include in results
            
        Returns:
            Dict containing search results
        """
        if not self.available:
            return {
                "error": "Atlassian tool not configured",
                "message": "Atlassian credentials not available"
            }
        
        start_time = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"jira_search: {query}",
                    json.dumps({"query": query, "max_results": max_results}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            arguments = {
                "jql": query,
                "maxResults": max_results
            }
            
            if fields:
                arguments["fields"] = fields
            
            result = await self._call_tool("jira_search", arguments)
            
            if "error" in result:
                return result
            
            # Format the result for consistency with the original API
            return {
                "jira_search_results": {
                    "query": query,
                    "total_found": result.get("total", 0),
                    "returned_count": len(result.get("issues", [])),
                    "issues": result.get("issues", [])
                },
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Jira search failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def get_jira_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Jira issue via MCP.
        
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
            
        Returns:
            Dict containing issue details
        """
        if not self.available:
            return {
                "error": "Atlassian tool not configured",
                "message": "Atlassian credentials not available"
            }
        
        start_time = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"jira_get_issue: {issue_key}",
                    json.dumps({"issue_key": issue_key}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            arguments = {
                "issueKey": issue_key
            }
            
            result = await self._call_tool("jira_get_issue", arguments)
            
            if "error" in result:
                return result
            
            return {
                "jira_issue": result.get("issue", {}),
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Failed to get Jira issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def search_confluence_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for Confluence pages via MCP.
        
        Args:
            query: Search terms
            space_key: Optional space key to limit search
            max_results: Maximum number of results to return
            
        Returns:
            Dict containing search results
        """
        if not self.available:
            return {
                "error": "Atlassian tool not configured",
                "message": "Atlassian credentials not available"
            }
        
        start_time = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"confluence_search: {query}",
                    json.dumps({"query": query, "space_key": space_key, "max_results": max_results}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            arguments = {
                "cql": query,
                "limit": max_results
            }
            
            if space_key:
                arguments["spaceKey"] = space_key
            
            result = await self._call_tool("confluence_search", arguments)
            
            if "error" in result:
                return result
            
            return {
                "confluence_search_results": {
                    "query": query,
                    "space_key": space_key,
                    "total_found": result.get("totalSize", 0),
                    "returned_count": len(result.get("results", [])),
                    "pages": result.get("results", [])
                },
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Confluence search failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def get_confluence_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Confluence page via MCP.
        
        Args:
            page_id: The Confluence page ID
            
        Returns:
            Dict containing page details
        """
        if not self.available:
            return {
                "error": "Atlassian tool not configured",
                "message": "Atlassian credentials not available"
            }
        
        start_time = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"confluence_get_page: {page_id}",
                    json.dumps({"page_id": page_id}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            arguments = {
                "pageId": page_id
            }
            
            result = await self._call_tool("confluence_get_page", arguments)
            
            if "error" in result:
                return result
            
            return {
                "confluence_page": result.get("page", {}),
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Failed to get Confluence page: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def create_jira_issue(
        self,
        project_key: str,
        issue_type: str = "Task",
        summary: str = "",
        description: str = "",
        priority: str = "Medium",
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Jira issue via MCP.
        
        Args:
            project_key: The project key
            issue_type: Type of issue (Task, Bug, Story, etc.)
            summary: Issue summary
            description: Issue description
            priority: Issue priority
            assignee: Optional assignee username
            
        Returns:
            Dict containing created issue details
        """
        if not self.available:
            return {
                "error": "Atlassian tool not configured",
                "message": "Atlassian credentials not available"
            }
        
        start_time = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"jira_create_issue: {project_key}",
                    json.dumps({
                        "project_key": project_key,
                        "issue_type": issue_type,
                        "summary": summary
                    }),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            arguments = {
                "projectKey": project_key,
                "issueType": issue_type,
                "summary": summary,
                "description": description,
                "priority": priority
            }
            
            if assignee:
                arguments["assignee"] = assignee
            
            result = await self._call_tool("jira_create_issue", arguments)
            
            if "error" in result:
                return result
            
            return {
                "jira_issue_created": result.get("issue", {}),
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Failed to create Jira issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_session()