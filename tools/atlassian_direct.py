"""
Direct Atlassian API Integration

This tool directly connects to Confluence and Jira APIs to search for content
while the MCP SSE transport issues are being resolved.
"""

import asyncio
import base64
import logging
from typing import Dict, Any, Optional, List
import httpx
from config import settings

logger = logging.getLogger(__name__)

class AtlassianDirectTool:
    """
    Direct Atlassian API integration tool.
    Connects directly to Confluence and Jira REST APIs.
    """
    
    def __init__(self):
        """Initialize direct Atlassian tool"""
        self.confluence_url = settings.ATLASSIAN_CONFLUENCE_URL
        self.confluence_username = settings.ATLASSIAN_CONFLUENCE_USERNAME 
        self.confluence_token = settings.ATLASSIAN_CONFLUENCE_TOKEN
        
        self.jira_url = settings.ATLASSIAN_JIRA_URL
        self.jira_username = settings.ATLASSIAN_JIRA_USERNAME
        self.jira_token = settings.ATLASSIAN_JIRA_TOKEN
        
        # Check if credentials are available
        self.available = self._check_credentials()
        
        if self.available:
            logger.info("Direct Atlassian tool initialized successfully")
        else:
            logger.warning("Direct Atlassian tool initialized but credentials missing")
    
    def _check_credentials(self) -> bool:
        """Check if required Atlassian credentials are available"""
        confluence_ready = all([
            self.confluence_url,
            self.confluence_username,
            self.confluence_token
        ])
        
        jira_ready = all([
            self.jira_url,
            self.jira_username, 
            self.jira_token
        ])
        
        return confluence_ready or jira_ready
    
    def _create_auth_header(self, username: str, token: str) -> str:
        """Create Basic Auth header"""
        credentials = f"{username}:{token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def search_confluence_pages(self, query: str, space_key: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search Confluence pages using direct API
        
        Args:
            query: Search query
            space_key: Optional space key to limit search
            limit: Maximum number of results
            
        Returns:
            Search results
        """
        if not all([self.confluence_url, self.confluence_username, self.confluence_token]):
            return {
                "error": "Confluence credentials not configured",
                "message": "Please configure ATLASSIAN_CONFLUENCE_* environment variables"
            }
        
        try:
            headers = {
                "Authorization": self._create_auth_header(self.confluence_username, self.confluence_token),
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Build search URL
            search_url = f"{self.confluence_url}/rest/api/content/search"
            
            # Build CQL query
            cql_parts = [f'text ~ "{query}"']
            if space_key:
                cql_parts.append(f'space = "{space_key}"')
            
            cql_query = " AND ".join(cql_parts)
            
            params = {
                "cql": cql_query,
                "limit": limit,
                "expand": "body.view,space,version,history"
            }
            
            logger.info(f"Searching Confluence with CQL: {cql_query}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    # Format results for consistency
                    formatted_pages = []
                    for result in results:
                        page = {
                            "id": result.get("id"),
                            "title": result.get("title"),
                            "space_name": result.get("space", {}).get("name"),
                            "space_key": result.get("space", {}).get("key"),
                            "url": f"{self.confluence_url}/pages/viewpage.action?pageId={result.get('id')}",
                            "type": result.get("type"),
                            "status": result.get("status")
                        }
                        
                        # Extract excerpt from body
                        body = result.get("body", {}).get("view", {})
                        if body:
                            content = body.get("value", "")
                            # Simple text extraction (remove HTML tags)
                            import re
                            text_content = re.sub(r'<[^>]+>', '', content)
                            page["excerpt"] = text_content[:200].strip()
                        
                        formatted_pages.append(page)
                    
                    return {
                        "success": True,
                        "result": {
                            "confluence_search_results": {
                                "query": query,
                                "total_found": data.get("size", len(results)),
                                "pages": formatted_pages
                            }
                        }
                    }
                else:
                    logger.error(f"Confluence API error: {response.status_code} - {response.text}")
                    return {
                        "error": f"API error: {response.status_code}",
                        "message": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Error searching Confluence: {e}")
            return {
                "error": "search_failed",
                "message": str(e)
            }
    
    async def search_jira_issues(self, project: str = "", query: str = "", status: str = "") -> Dict[str, Any]:
        """
        Search Jira issues using direct API
        
        Args:
            project: Project key
            query: Search query
            status: Issue status
            
        Returns:
            Search results
        """
        if not all([self.jira_url, self.jira_username, self.jira_token]):
            return {
                "error": "Jira credentials not configured", 
                "message": "Please configure ATLASSIAN_JIRA_* environment variables"
            }
        
        try:
            headers = {
                "Authorization": self._create_auth_header(self.jira_username, self.jira_token),
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Build JQL query
            jql_parts = []
            if project:
                jql_parts.append(f'project = "{project}"')
            if query:
                jql_parts.append(f'(summary ~ "{query}" OR description ~ "{query}")')
            if status:
                jql_parts.append(f'status = "{status}"')
            
            jql_query = " AND ".join(jql_parts) if jql_parts else "project is not EMPTY"
            
            search_url = f"{self.jira_url}/rest/api/2/search"
            
            payload = {
                "jql": jql_query,
                "maxResults": 15,
                "fields": ["summary", "status", "assignee", "issuetype", "priority", "created", "updated"]
            }
            
            logger.info(f"Searching Jira with JQL: {jql_query}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(search_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    issues = data.get("issues", [])
                    
                    # Format results
                    formatted_issues = []
                    for issue in issues:
                        fields = issue.get("fields", {})
                        formatted_issue = {
                            "key": issue.get("key"),
                            "summary": fields.get("summary"),
                            "status": fields.get("status", {}).get("name"),
                            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                            "issue_type": fields.get("issuetype", {}).get("name"),
                            "priority": fields.get("priority", {}).get("name"),
                            "url": f"{self.jira_url}/browse/{issue.get('key')}"
                        }
                        formatted_issues.append(formatted_issue)
                    
                    return {
                        "success": True,
                        "result": {
                            "jira_search_results": {
                                "query": jql_query,
                                "total_found": data.get("total", len(issues)),
                                "issues": formatted_issues
                            }
                        }
                    }
                else:
                    logger.error(f"Jira API error: {response.status_code} - {response.text}")
                    return {
                        "error": f"API error: {response.status_code}",
                        "message": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Error searching Jira: {e}")
            return {
                "error": "search_failed", 
                "message": str(e)
            }
    
    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool with MCP-compatible interface for seamless integration
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self.available:
            return {
                "error": "Atlassian credentials not configured",
                "message": "Please configure ATLASSIAN_* environment variables"
            }
        
        try:
            logger.info(f"Executing direct Atlassian tool: {tool_name} with args: {arguments}")
            
            if tool_name == "confluence_search":
                return await self.search_confluence_pages(
                    query=arguments.get("query", ""),
                    space_key=arguments.get("space_key"),
                    limit=arguments.get("limit", 10)
                )
            
            elif tool_name == "jira_search":
                # Handle both direct arguments and JQL
                jql = arguments.get("jql", "")
                if jql:
                    # Extract project from JQL if present
                    project = ""
                    query = jql
                    if "project =" in jql.lower():
                        import re
                        project_match = re.search(r'project\s*=\s*"?([^"\s]+)"?', jql, re.IGNORECASE)
                        if project_match:
                            project = project_match.group(1)
                    
                    return await self.search_jira_issues(
                        project=project,
                        query=query,
                        status=""
                    )
                else:
                    return await self.search_jira_issues(
                        project=arguments.get("project", ""),
                        query=arguments.get("query", ""),
                        status=arguments.get("status", "")
                    )
            
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "message": f"Available tools: confluence_search, jira_search"
                }
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "error": "execution_error",
                "message": str(e)
            }