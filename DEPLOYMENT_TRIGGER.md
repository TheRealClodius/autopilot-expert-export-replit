# CRITICAL DEPLOYMENT ENVIRONMENT VARIABLES

## 1. Redis Connection Error Fix

**Problem:** Deployment showing `error dial tcp 127.0.0.1:6379: connect: connection refused`

**Root Cause:** When these environment variables are EMPTY in deployment, something defaults to `redis://localhost:6379`

### Required Redis Environment Variables

```bash
# For Replit Secrets (cannot have empty values)
CELERY_BROKER_URL = memory://
CELERY_RESULT_BACKEND = cache+memory://
REDIS_URL = memory://
```

## 2. MCP SERVER CONNECTIVITY FIX

**Problem:** `Atlassian Error (jira_search encountered an issue)` - `All connection attempts failed`

**Root Cause:** MCP server not accessible at `http://localhost:8001` in deployment environment

### Required MCP Server Environment Variable

Choose the appropriate option for your deployment:

```bash
# Option 1: Single container deployment (default)
export MCP_SERVER_URL='http://localhost:8001'

# Option 2: Docker/container deployment
export MCP_SERVER_URL='http://mcp-atlassian:8001'

# Option 3: Host networking
export MCP_SERVER_URL='http://host.docker.internal:8001'

# Option 4: External MCP server
export MCP_SERVER_URL='http://your-mcp-host:8001'
```

### Deployment Diagnosis Steps

1. **Check MCP Server Status:**
   ```bash
   curl http://localhost:8001/healthz
   # Should return: {"status":"ok"}
   ```

2. **Test MCP Connectivity:**
   ```bash
   curl -X POST http://localhost:8001/mcp/ \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'
   ```

3. **Verify Container/Process Status:**
   ```bash
   # Check if MCP server process is running
   ps aux | grep mcp
   
   # Check port binding
   netstat -tlnp | grep 8001
   ```

## Deployment Status

- ✅ Application code updated to handle empty Redis configurations
- ✅ Celery fallback to memory transport implemented
- ✅ MCP server URL made configurable via environment variable
- ✅ AtlassianTool working with authentic UiPath data locally
- 🔄 **DEPLOYMENT NEEDED:** Environment variables must be set for deployment network

## Final Verification

After setting environment variables, check logs for:

**Redis:**
```
- celery_app - INFO - Using memory transport (broker_url='')
- celery_app - INFO - Using cache+memory backend (backend_url='')
```

**MCP Server:**
```
- tools.atlassian_tool - INFO - HTTP-based Atlassian tool initialized successfully
- Successfully retrieved X Confluence pages
```

This will eliminate ALL Redis connection attempts and MCP connectivity issues in deployment.