"""
Atlassian Tool - Integration with Atlassian services via MCP server for Jira and Confluence operations.
Provides access to Jira issues, Confluence pages, and project management capabilities.
"""

import json
import logging
import time
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from config import settings
from services.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class AtlassianTool:
    """
    Atlassian integration tool using MCP (Model Context Protocol) server.
    Provides access to Jira and Confluence via the Atlassian MCP server.
    """
    
    def __init__(self):
        """Initialize Atlassian tool with MCP server configuration."""
        # Configuration based on the provided working example
        self.jira_url = settings.ATLASSIAN_JIRA_URL
        self.jira_username = settings.ATLASSIAN_JIRA_USERNAME
        self.jira_token = settings.ATLASSIAN_JIRA_TOKEN
        self.confluence_url = settings.ATLASSIAN_CONFLUENCE_URL
        self.confluence_username = settings.ATLASSIAN_CONFLUENCE_USERNAME
        self.confluence_token = settings.ATLASSIAN_CONFLUENCE_TOKEN
        
        # MCP server configuration
        self.mcp_url = settings.ATLASSIAN_MCP_URL or "https://mcp.atlassian.com/v1/sse"
        
        self.available = bool(
            self.jira_url and self.jira_username and self.jira_token and
            self.confluence_url and self.confluence_username and self.confluence_token
        )
        
        if self.available:
            logger.info("Atlassian tool initialized successfully")
        else:
            logger.warning("Atlassian tool unavailable - missing credentials")
    
    async def _make_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the Atlassian MCP server.
        
        Args:
            method: The MCP method to call
            params: Parameters for the method
            
        Returns:
            Response from the MCP server
        """
        try:
            request_data = {
                "jsonrpc": "2.0",
                "id": f"req_{int(time.time() * 1000)}",
                "method": method,
                "params": params
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.jira_token}",  # Use Jira token for auth
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.mcp_url,
                    json=request_data,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "error" in result:
                    logger.error(f"MCP server error: {result['error']}")
                    return {"error": result["error"]}
                
                return result.get("result", {})
                
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            return {"error": f"MCP request failed: {str(e)}"}
    
    async def search_jira_issues(
        self,
        query: str,
        max_results: int = 10,
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Search for Jira issues using JQL or text search.
        
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
            
            search_fields = fields if fields is not None else ["summary", "status", "priority", "assignee", "created", "updated"]
            params = {
                "jql": query,
                "maxResults": max_results,
                "fields": search_fields
            }
            
            result = await self._make_mcp_request("jira/search", params)
            
            if "error" in result:
                return result
            
            # Process and format results
            issues = result.get("issues", [])
            processed_issues = []
            
            for issue in issues:
                fields_data = issue.get("fields", {})
                processed_issue = {
                    "key": issue.get("key"),
                    "summary": fields_data.get("summary"),
                    "status": fields_data.get("status", {}).get("name"),
                    "priority": fields_data.get("priority", {}).get("name"),
                    "assignee": fields_data.get("assignee", {}).get("displayName") if fields_data.get("assignee") else "Unassigned",
                    "created": fields_data.get("created"),
                    "updated": fields_data.get("updated"),
                    "url": f"{self.jira_url}/browse/{issue.get('key')}"
                }
                processed_issues.append(processed_issue)
            
            return {
                "jira_search_results": {
                    "query": query,
                    "total_found": result.get("total", 0),
                    "returned_count": len(processed_issues),
                    "issues": processed_issues
                },
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Jira search failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def get_jira_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Jira issue.
        
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
                    {"issue_key": issue_key},
                    trace_manager.current_trace_id
                )
            
            params = {"issueKey": issue_key}
            result = await self._make_mcp_request("jira/issue", params)
            
            if "error" in result:
                return result
            
            # Process the issue data
            fields = result.get("fields", {})
            processed_issue = {
                "key": result.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                "reporter": fields.get("reporter", {}).get("displayName"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "project": fields.get("project", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "url": f"{self.jira_url}/browse/{result.get('key')}"
            }
            
            return {
                "jira_issue": processed_issue,
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Failed to get Jira issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def search_confluence_pages(
        self,
        query: str,
        space_key: str = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for Confluence pages.
        
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
                await trace_manager.log_tool_operation(
                    "atlassian_confluence_search",
                    {"query": query, "space_key": space_key, "max_results": max_results},
                    trace_manager.current_trace_id
                )
            
            params = {
                "cql": f"text ~ \"{query}\"" + (f" and space = \"{space_key}\"" if space_key else ""),
                "limit": max_results
            }
            
            result = await self._make_mcp_request("confluence/search", params)
            
            if "error" in result:
                return result
            
            # Process results
            pages = result.get("results", [])
            processed_pages = []
            
            for page in pages:
                processed_page = {
                    "id": page.get("id"),
                    "title": page.get("title"),
                    "space_key": page.get("space", {}).get("key"),
                    "space_name": page.get("space", {}).get("name"),
                    "excerpt": page.get("excerpt", ""),
                    "url": page.get("_links", {}).get("webui"),
                    "last_modified": page.get("lastModified"),
                    "version": page.get("version", {}).get("number")
                }
                processed_pages.append(processed_page)
            
            return {
                "confluence_search_results": {
                    "query": query,
                    "space_key": space_key,
                    "total_found": result.get("totalSize", 0),
                    "returned_count": len(processed_pages),
                    "pages": processed_pages
                },
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Confluence search failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def get_confluence_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Confluence page.
        
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
                await trace_manager.log_tool_operation(
                    "atlassian_confluence_get_page",
                    {"page_id": page_id},
                    trace_manager.current_trace_id
                )
            
            params = {"pageId": page_id, "expand": "body.storage,space,version"}
            result = await self._make_mcp_request("confluence/page", params)
            
            if "error" in result:
                return result
            
            # Process the page data
            processed_page = {
                "id": result.get("id"),
                "title": result.get("title"),
                "space_key": result.get("space", {}).get("key"),
                "space_name": result.get("space", {}).get("name"),
                "content": result.get("body", {}).get("storage", {}).get("value", ""),
                "url": result.get("_links", {}).get("webui"),
                "version": result.get("version", {}).get("number"),
                "created": result.get("history", {}).get("createdDate"),
                "last_modified": result.get("version", {}).get("when"),
                "author": result.get("version", {}).get("by", {}).get("displayName")
            }
            
            return {
                "confluence_page": processed_page,
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Failed to get Confluence page: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def create_jira_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str = "",
        priority: str = "Medium",
        assignee: str = None
    ) -> Dict[str, Any]:
        """
        Create a new Jira issue.
        
        Args:
            project_key: The project key where to create the issue
            issue_type: Type of issue (e.g., "Task", "Bug", "Story")
            summary: Issue summary/title
            description: Issue description
            priority: Issue priority
            assignee: Username to assign the issue to
            
        Returns:
            Dict containing created issue information
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
                await trace_manager.log_tool_operation(
                    "atlassian_jira_create_issue",
                    {"project": project_key, "type": issue_type, "summary": summary},
                    trace_manager.current_trace_id
                )
            
            issue_data = {
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "summary": summary,
                "description": description,
                "priority": {"name": priority}
            }
            
            if assignee:
                issue_data["assignee"] = {"name": assignee}
            
            params = {"fields": issue_data}
            result = await self._make_mcp_request("jira/create", params)
            
            if "error" in result:
                return result
            
            return {
                "jira_issue_created": {
                    "key": result.get("key"),
                    "id": result.get("id"),
                    "url": f"{self.jira_url}/browse/{result.get('key')}",
                    "summary": summary,
                    "project": project_key,
                    "issue_type": issue_type
                },
                "response_time": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            error_msg = f"Failed to create Jira issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}