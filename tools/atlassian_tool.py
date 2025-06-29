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
    
    async def _make_confluence_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a direct request to Confluence REST API.
        
        Args:
            endpoint: The API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            Response from Confluence API
        """
        try:
            # Use basic auth with email and API token
            auth = (self.confluence_username, self.confluence_token)
            
            # Build full URL
            base_url = self.confluence_url.rstrip('/wiki')  # Remove /wiki if present
            url = f"{base_url}/wiki/rest/api{endpoint}"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    params=params or {},
                    headers=headers,
                    auth=auth
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Confluence API request failed: {e}")
            return {"error": f"Confluence API request failed: {str(e)}"}
    
    async def _make_jira_request(self, endpoint: str, params: Dict[str, Any] = None, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a direct request to Jira REST API.
        
        Args:
            endpoint: The API endpoint (without base URL)
            params: Query parameters
            method: HTTP method
            data: Request body data
            
        Returns:
            Response from Jira API
        """
        try:
            # Use basic auth with email and API token
            auth = (self.jira_username, self.jira_token)
            
            # Build full URL
            url = f"{self.jira_url.rstrip('/')}/rest/api/2{endpoint}"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(
                        url,
                        params=params or {},
                        headers=headers,
                        auth=auth
                    )
                else:
                    response = await client.request(
                        method,
                        url,
                        params=params or {},
                        json=data,
                        headers=headers,
                        auth=auth
                    )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Jira API request failed: {e}")
            return {"error": f"Jira API request failed: {str(e)}"}
    
    def _build_smart_cql_query(self, query: str) -> str:
        """
        Build intelligent CQL query based on the type of request.
        Handles creator searches, title searches, and general text searches.
        """
        query_lower = query.lower()
        
        # Handle creator-based searches
        if any(phrase in query_lower for phrase in ["created by", "authored by", "made by", "by "]):
            # Extract creator name from query
            for phrase in ["created by ", "authored by ", "made by ", "by "]:
                if phrase in query_lower:
                    creator_name = query_lower.split(phrase)[1].strip()
                    # Remove common trailing words
                    creator_name = creator_name.replace(" pages", "").replace(" documents", "").strip()
                    return f'creator = "{creator_name}"'
        
        # Handle title-specific searches
        elif any(phrase in query_lower for phrase in ["title:", "titled ", "named ", "called "]):
            # Extract title from query
            title_part = query
            for phrase in ["title:", "titled ", "named ", "called "]:
                if phrase.lower() in query_lower:
                    title_part = query_lower.split(phrase.lower())[1].strip()
                    break
            return f'title ~ "{title_part}"'
        
        # Handle space-specific searches
        elif any(phrase in query_lower for phrase in ["in space", "space:"]):
            # This would be handled by the space_key parameter, so do general search
            return f'text ~ "{query}"'
        
        # Default to general text search
        else:
            return f'text ~ "{query}"'
    
    def _get_alternative_cql_queries(self, original_query: str, failed_cql: str) -> List[str]:
        """
        Generate alternative CQL queries when the original fails.
        Handles common CQL syntax issues and provides fallback options.
        """
        alternatives = []
        query_lower = original_query.lower()
        
        # If the failed query was a creator search, try variations
        if 'creator =' in failed_cql:
            # Extract the creator name and try different formats
            creator_match = failed_cql.split('creator = "')[1].split('"')[0]
            
            # Try with displayName
            alternatives.append(f'creator.displayName = "{creator_match}"')
            
            # Try with accountId approach (less likely to work without knowing the accountId)
            # alternatives.append(f'creator.accountId = "{creator_match}"')
            
            # Fall back to text search that includes the creator name
            alternatives.append(f'text ~ "{creator_match}"')
            
            # Try searching in the content for the name
            alternatives.append(f'title ~ "{creator_match}" or text ~ "{creator_match}"')
        
        # If it was a text search that failed, try simpler approaches
        elif 'text ~' in failed_cql:
            search_term = failed_cql.split('text ~ "')[1].split('"')[0]
            
            # Try title search
            alternatives.append(f'title ~ "{search_term}"')
            
            # Try a more specific search
            alternatives.append(f'title ~ "{search_term}" or label = "{search_term}"')
        
        # Always fall back to the most basic search if nothing else works
        if not alternatives:
            # Extract key terms and do a simple text search
            key_terms = original_query.replace("created by", "").replace("by", "").strip()
            if key_terms:
                alternatives.append(f'text ~ "{key_terms}"')
        
        return alternatives
    
    async def search_jira_issues(
        self,
        query: str,
        max_results: int = 10,
        fields: Optional[List[str]] = None
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
            
            # Convert fields list to comma-separated string for Jira API
            params["fields"] = ",".join(search_fields)
            result = await self._make_jira_request("/search", params)
            
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
                    "url": f"{self.jira_url.rstrip('/')}/browse/{issue.get('key')}"
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
                    json.dumps({"issue_key": issue_key}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            result = await self._make_jira_request(f"/issue/{issue_key}")
            
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
                "url": f"{self.jira_url.rstrip('/')}/browse/{result.get('key')}"
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
        space_key: Optional[str] = None,
        max_results: int = 10,
        fetch_content: bool = True
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
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"confluence_search: {query}",
                    json.dumps({"query": query, "space_key": space_key, "max_results": max_results}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            # Smart CQL query construction based on query type
            cql_query = self._build_smart_cql_query(query)
            if space_key:
                cql_query += f" and space = \"{space_key}\""
                
            params = {
                "cql": cql_query,
                "limit": max_results
            }
            
            result = await self._make_confluence_request("/content/search", params)
            
            # If we get an error and it looks like a CQL syntax issue, try alternative approaches
            if "error" in result and "400" in str(result.get("error", "")):
                logger.info(f"CQL query failed, trying alternative approach: {cql_query}")
                
                # Try alternative CQL approaches for common failures
                alternative_queries = self._get_alternative_cql_queries(query, cql_query)
                
                for alt_query in alternative_queries:
                    logger.info(f"Trying alternative CQL: {alt_query}")
                    alt_params = {
                        "cql": alt_query,
                        "limit": max_results
                    }
                    if space_key:
                        alt_params["cql"] += f" and space = \"{space_key}\""
                    
                    alt_result = await self._make_confluence_request("/content/search", alt_params)
                    
                    if "error" not in alt_result:
                        logger.info(f"Alternative CQL query succeeded: {alt_query}")
                        result = alt_result
                        break
                else:
                    # If all alternatives failed, return the original error
                    return result
            elif "error" in result:
                return result
            
            # Process results
            pages = result.get("results", [])
            processed_pages = []
            
            for page in pages:
                # Construct proper full URL from relative webui path
                webui_path = page.get("_links", {}).get("webui", "")
                if webui_path:
                    # Base URL without /wiki suffix + /wiki + webui path
                    base_url = self.confluence_url.rstrip('/wiki')
                    full_url = f"{base_url}/wiki{webui_path}" if webui_path.startswith('/') else f"{base_url}/wiki/{webui_path}"
                else:
                    full_url = None
                
                processed_page = {
                    "id": page.get("id"),
                    "title": page.get("title"),
                    "space_key": page.get("space", {}).get("key"),
                    "space_name": page.get("space", {}).get("name"),
                    "excerpt": page.get("excerpt", ""),
                    "url": full_url,
                    "last_modified": page.get("lastModified"),
                    "version": page.get("version", {}).get("number")
                }
                processed_pages.append(processed_page)
            
            # If fetch_content is True, get detailed content from top 3 pages
            detailed_pages = []
            if fetch_content and processed_pages:
                top_pages = processed_pages[:3]  # Get content from top 3 most relevant pages
                
                for page in top_pages:
                    page_id = page.get("id")
                    if page_id:
                        page_content = await self.get_confluence_page(page_id)
                        if page_content and not page_content.get("error"):
                            detailed_pages.append(page_content.get("confluence_page", {}))
                        
                        # Add small delay to avoid rate limiting
                        await asyncio.sleep(0.1)
            
            return {
                "confluence_search_results": {
                    "query": query,
                    "space_key": space_key,
                    "total_found": result.get("totalSize", 0),
                    "returned_count": len(processed_pages),
                    "pages": processed_pages,
                    "detailed_content": detailed_pages if fetch_content else []
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
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"confluence_get_page: {page_id}",
                    json.dumps({"page_id": page_id}),
                    {"trace_id": trace_manager.current_trace_id}
                )
            
            result = await self._make_confluence_request(f"/content/{page_id}", {
                "expand": "body.storage,space,version,history"
            })
            
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
        assignee: Optional[str] = None
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
                await trace_manager.log_agent_operation(
                    "atlassian_tool",
                    f"jira_create_issue: {summary}",
                    json.dumps({"project": project_key, "type": issue_type, "summary": summary}),
                    {"trace_id": trace_manager.current_trace_id}
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
            
            result = await self._make_jira_request("/issue", method="POST", data={"fields": issue_data})
            
            if "error" in result:
                return result
            
            return {
                "jira_issue_created": {
                    "key": result.get("key"),
                    "id": result.get("id"),
                    "url": f"{self.jira_url.rstrip('/')}/browse/{result.get('key')}",
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