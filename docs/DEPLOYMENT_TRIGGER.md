# Two-Project Deployment Architecture

## Overview

The multi-agent system has been restructured into two independent Replit projects for better scalability and maintainability:

1. **Main Agent System** (this project) - FastAPI with Slack integration
2. **Standalone MCP Server** (separate project) - Atlassian MCP service

## Project 1: Main Agent System (Current Project)

### What This Contains:
- FastAPI server with Slack webhook integration
- Multi-agent system (Orchestrator, Client, Observer agents)
- Vector search, Perplexity search, Outlook meeting tools
- Memory service and performance optimization
- LangSmith tracing integration

### Dependencies Removed:
- Redis server (uses memory cache fallback)
- MCP server (connects to external MCP service)
- Docker dependencies

### Deployment:
```bash
# This project runs standalone on port 5000
python main.py
```

### Environment Variables:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
GEMINI_API_KEY=...
MCP_SERVER_URL=https://your-mcp-server.replit.app
PINECONE_API_KEY=...
PERPLEXITY_API_KEY=...
LANGSMITH_API_KEY=...
```

## Project 2: Standalone MCP Server (New Separate Project)

### Files to Copy to New Project:
- `mcp_server_standalone.py` (main startup file)
- `requirements_mcp_server.txt` (minimal dependencies)
- `.replit_mcp_server` (rename to `.replit`)
- `mcp-atlassian/` directory (if using custom MCP implementation)

### Environment Variables for MCP Project:
```
ATLASSIAN_JIRA_URL=https://your-org.atlassian.net
ATLASSIAN_JIRA_USERNAME=your-email@company.com
ATLASSIAN_JIRA_TOKEN=your-api-token
ATLASSIAN_CONFLUENCE_URL=https://your-org.atlassian.net
ATLASSIAN_CONFLUENCE_USERNAME=your-email@company.com
ATLASSIAN_CONFLUENCE_TOKEN=your-api-token
PORT=8001
```

### Deployment Steps:
1. Create new Replit project
2. Copy standalone MCP files
3. Install dependencies: `pip install -r requirements_mcp_server.txt`
4. Set environment variables
5. Deploy on port 8001

## Connection Configuration

After deploying both projects:

1. **Get MCP Server URL**: After deploying MCP project, note the public URL
2. **Update Main Project**: Set `MCP_SERVER_URL` to the MCP server's public URL
3. **Test Connection**: Use `/admin/test-atlassian-integration` endpoint

## Benefits of Two-Project Architecture

1. **Independent Scaling**: Each service scales based on its needs
2. **Simplified Deployment**: No complex dual-server startup scripts
3. **Resource Efficiency**: MCP server is lightweight, main app handles complex AI
4. **Better Maintenance**: Changes to one service don't affect the other
5. **Cleaner Dependencies**: Each project has only what it needs

## Ready for Deployment

✅ **Main Project Status**: Ready to deploy
- All Redis dependencies eliminated
- Memory cache fallback working
- FastAPI server running on port 5000
- All external dependencies configurable via environment variables

✅ **MCP Server Files**: Ready for separate project
- Standalone server configuration created
- Minimal dependencies defined
- Environment validation implemented
- Health check endpoints available

## Next Steps

1. Deploy this current project (main agent system)
2. Create new Replit project for MCP server
3. Copy MCP files to new project and deploy
4. Update `MCP_SERVER_URL` environment variable
5. Test end-to-end integration