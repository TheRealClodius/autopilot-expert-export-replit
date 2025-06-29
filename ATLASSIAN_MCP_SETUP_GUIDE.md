# Atlassian MCP Server Setup Guide

## Current Status
✅ **MCP Server Connected**: https://remote-mcp-server-andreiclodius.replit.app  
❌ **Atlassian Tools Missing**: Server only has basic test tools (`echo`, `get_system_info`, `health_check`)  
⚠️ **Expected Tools**: `jira_search`, `confluence_search`, `jira_get`, `confluence_get`, `jira_create`

## Required Environment Variables for MCP Server

Based on the [MCP-Atlassian README](https://github.com/sooperset/mcp-atlassian), your MCP server needs these environment variables:

### Method A: API Token Authentication (Recommended)
```bash
# Jira Configuration
JIRA_URL=https://uipath.atlassian.net
JIRA_USERNAME=your-email@uipath.com
JIRA_API_TOKEN=your-api-token

# Confluence Configuration  
CONFLUENCE_URL=https://uipath.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@uipath.com
CONFLUENCE_API_TOKEN=your-api-token
```

### Getting API Tokens
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token" 
3. Name it "MCP Server Integration"
4. Copy the token immediately (it won't be shown again)

## Verification Steps

Once you add the credentials to your MCP server:

1. **Restart MCP Server** with new environment variables
2. **Test Available Tools**:
   ```bash
   curl -X POST https://remote-mcp-server-andreiclodius.replit.app/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/list",
       "params": {}
     }'
   ```
3. **Expected Response**: Should include `jira_search`, `confluence_search`, `jira_get`, `confluence_get`, `jira_create`

## Testing Commands

After setup, test with these queries:
- "Search for AUTOPILOT bugs in Jira"
- "Find Confluence documentation about API endpoints"  
- "Create a Jira ticket for testing MCP integration"

## Current Integration Status

Our main application is correctly configured and ready to use Atlassian tools once your MCP server exposes them. The orchestrator will:

- Route UiPath/Autopilot queries to `atlassian_search` 
- Generate proper MCP format commands (`jira_search`, `confluence_search`)
- Display results with clickable links in Slack

The only missing piece is the Atlassian tool availability on the MCP server side.