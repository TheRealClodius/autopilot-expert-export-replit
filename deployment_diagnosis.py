#!/usr/bin/env python3
"""
Deployment Diagnosis Tool

This script diagnoses the exact differences between local and deployment environments
that cause "execution error" failures in production.
"""

import asyncio
import os
import sys
import json
import httpx
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from tools.atlassian_tool import AtlassianTool

class DeploymentDiagnostic:
    """Comprehensive deployment environment diagnostic"""
    
    def __init__(self):
        self.results = {
            "environment": {},
            "network": {},
            "mcp_server": {},
            "atlassian_tool": {},
            "authentication": {},
            "permissions": {},
            "summary": {"issues": [], "recommendations": []}
        }
    
    async def run_full_diagnosis(self):
        """Run complete deployment diagnosis"""
        print("🔍 DEPLOYMENT ENVIRONMENT DIAGNOSIS")
        print("=" * 60)
        
        await self._check_environment_variables()
        await self._check_network_connectivity()
        await self._check_mcp_server_status()
        await self._check_atlassian_tool_initialization()
        await self._check_authentication_flow()
        await self._check_permissions_and_paths()
        await self._test_production_execution_flow()
        
        self._generate_summary()
        self._print_results()
        
        return self.results
    
    async def _check_environment_variables(self):
        """Check all required environment variables"""
        print("\n🌍 Environment Variables Check")
        print("-" * 40)
        
        required_vars = [
            "ATLASSIAN_JIRA_URL",
            "ATLASSIAN_JIRA_USERNAME", 
            "ATLASSIAN_JIRA_TOKEN",
            "ATLASSIAN_CONFLUENCE_URL",
            "ATLASSIAN_CONFLUENCE_USERNAME",
            "ATLASSIAN_CONFLUENCE_TOKEN"
        ]
        
        env_status = {}
        for var in required_vars:
            value = os.getenv(var)
            if value:
                env_status[var] = f"✅ Present ({len(value)} chars)"
                print(f"  {var}: ✅ Present ({len(value)} chars)")
            else:
                env_status[var] = "❌ Missing"
                print(f"  {var}: ❌ Missing")
                self.results["summary"]["issues"].append(f"Missing environment variable: {var}")
        
        self.results["environment"]["variables"] = env_status
        
        # Check if URLs are properly formatted
        for url_var in ["ATLASSIAN_JIRA_URL", "ATLASSIAN_CONFLUENCE_URL"]:
            url = os.getenv(url_var)
            if url:
                is_valid = url.startswith(("http://", "https://"))
                print(f"  {url_var} format: {'✅ Valid' if is_valid else '❌ Invalid'}")
                if not is_valid:
                    self.results["summary"]["issues"].append(f"Invalid URL format: {url_var}")
    
    async def _check_network_connectivity(self):
        """Check network connectivity to required services"""
        print("\n🌐 Network Connectivity Check")
        print("-" * 40)
        
        endpoints_to_test = [
            ("MCP Server Health", "http://localhost:8001/healthz"),
            ("MCP Server Root", "http://localhost:8001/"),
            ("MCP Server Endpoint", "http://localhost:8001/mcp"),
        ]
        
        # Add Atlassian endpoints if configured
        if settings.ATLASSIAN_JIRA_URL:
            endpoints_to_test.append(("Jira API", f"{settings.ATLASSIAN_JIRA_URL}/rest/api/2/serverInfo"))
        if settings.ATLASSIAN_CONFLUENCE_URL:
            endpoints_to_test.append(("Confluence API", f"{settings.ATLASSIAN_CONFLUENCE_URL}/rest/api/space"))
        
        connectivity_results = {}
        
        for name, url in endpoints_to_test:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    status = f"✅ {response.status_code}"
                    print(f"  {name}: {status}")
                    connectivity_results[name] = {
                        "status": response.status_code,
                        "success": True,
                        "response_time": "< 10s"
                    }
            except httpx.TimeoutException:
                status = "❌ Timeout"
                print(f"  {name}: {status}")
                connectivity_results[name] = {"error": "timeout", "success": False}
                self.results["summary"]["issues"].append(f"Network timeout: {name}")
            except Exception as e:
                status = f"❌ Error: {str(e)[:50]}"
                print(f"  {name}: {status}")
                connectivity_results[name] = {"error": str(e), "success": False}
                self.results["summary"]["issues"].append(f"Network error: {name} - {str(e)}")
        
        self.results["network"]["connectivity"] = connectivity_results
    
    async def _check_mcp_server_status(self):
        """Check detailed MCP server status and endpoints"""
        print("\n🚀 MCP Server Status Check")
        print("-" * 40)
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Test health endpoint
                health_response = await client.get("http://localhost:8001/healthz")
                print(f"  Health endpoint: {health_response.status_code}")
                
                # Test MCP endpoint initialization
                init_request = {
                    "jsonrpc": "2.0",
                    "id": "test-init",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "deployment-diagnostic",
                            "version": "1.0.0"
                        }
                    }
                }
                
                print(f"  Testing MCP initialization...")
                mcp_response = await client.post(
                    "http://localhost:8001/mcp", 
                    json=init_request,
                    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
                )
                
                print(f"  MCP init response: {mcp_response.status_code}")
                print(f"  Response headers: {dict(mcp_response.headers)}")
                
                if mcp_response.status_code == 307:
                    redirect_url = mcp_response.headers.get("location")
                    print(f"  Redirect URL: {redirect_url}")
                    
                    if redirect_url:
                        redirect_response = await client.post(
                            redirect_url, 
                            json=init_request,
                            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
                        )
                        print(f"  Redirect response: {redirect_response.status_code}")
                        print(f"  Response content sample: {redirect_response.text[:200]}")
                
                self.results["mcp_server"]["status"] = "operational"
                self.results["mcp_server"]["health_check"] = health_response.status_code == 200
                
        except Exception as e:
            print(f"  ❌ MCP Server Error: {str(e)}")
            self.results["mcp_server"]["status"] = "failed"
            self.results["mcp_server"]["error"] = str(e)
            self.results["summary"]["issues"].append(f"MCP server failure: {str(e)}")
    
    async def _check_atlassian_tool_initialization(self):
        """Check AtlassianTool initialization and availability"""
        print("\n🔧 Atlassian Tool Initialization Check")
        print("-" * 40)
        
        try:
            tool = AtlassianTool()
            print(f"  Tool available: {'✅ Yes' if tool.available else '❌ No'}")
            print(f"  Available tools: {tool.available_tools}")
            
            if not tool.available:
                print(f"  ❌ Tool not available - likely missing credentials")
                self.results["summary"]["issues"].append("AtlassianTool not available - check credentials")
            
            self.results["atlassian_tool"]["available"] = tool.available
            self.results["atlassian_tool"]["tools"] = tool.available_tools
            
        except Exception as e:
            print(f"  ❌ Tool initialization error: {str(e)}")
            self.results["atlassian_tool"]["error"] = str(e)
            self.results["summary"]["issues"].append(f"AtlassianTool initialization failed: {str(e)}")
    
    async def _check_authentication_flow(self):
        """Test authentication flow to Atlassian services"""
        print("\n🔐 Authentication Flow Check")
        print("-" * 40)
        
        if not (settings.ATLASSIAN_JIRA_USERNAME and settings.ATLASSIAN_JIRA_TOKEN):
            print("  ❌ Jira credentials missing")
            self.results["summary"]["issues"].append("Jira authentication credentials missing")
            return
        
        try:
            # Test Jira authentication
            jira_auth = httpx.BasicAuth(settings.ATLASSIAN_JIRA_USERNAME, settings.ATLASSIAN_JIRA_TOKEN)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                jira_response = await client.get(
                    f"{settings.ATLASSIAN_JIRA_URL}/rest/api/2/serverInfo",
                    auth=jira_auth
                )
                
                print(f"  Jira auth test: {jira_response.status_code}")
                
                if jira_response.status_code == 401:
                    print("  ❌ Jira authentication failed - invalid credentials")
                    self.results["summary"]["issues"].append("Jira authentication failed - invalid credentials")
                elif jira_response.status_code == 403:
                    print("  ❌ Jira authentication failed - insufficient permissions")
                    self.results["summary"]["issues"].append("Jira authentication failed - insufficient permissions")
                elif jira_response.status_code == 200:
                    print("  ✅ Jira authentication successful")
                    server_info = jira_response.json()
                    print(f"    Server: {server_info.get('serverTitle', 'Unknown')}")
                
                self.results["authentication"]["jira"] = {
                    "status_code": jira_response.status_code,
                    "success": jira_response.status_code == 200
                }
                
        except Exception as e:
            print(f"  ❌ Jira auth error: {str(e)}")
            self.results["authentication"]["jira"] = {"error": str(e)}
            self.results["summary"]["issues"].append(f"Jira authentication error: {str(e)}")
        
        # Test Confluence authentication
        if settings.ATLASSIAN_CONFLUENCE_USERNAME and settings.ATLASSIAN_CONFLUENCE_TOKEN:
            try:
                confluence_auth = httpx.BasicAuth(settings.ATLASSIAN_CONFLUENCE_USERNAME, settings.ATLASSIAN_CONFLUENCE_TOKEN)
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    confluence_response = await client.get(
                        f"{settings.ATLASSIAN_CONFLUENCE_URL}/rest/api/space",
                        auth=confluence_auth,
                        params={"limit": 1}
                    )
                    
                    print(f"  Confluence auth test: {confluence_response.status_code}")
                    
                    if confluence_response.status_code == 401:
                        print("  ❌ Confluence authentication failed - invalid credentials")
                        self.results["summary"]["issues"].append("Confluence authentication failed - invalid credentials")
                    elif confluence_response.status_code == 403:
                        print("  ❌ Confluence authentication failed - insufficient permissions")
                        self.results["summary"]["issues"].append("Confluence authentication failed - insufficient permissions")
                    elif confluence_response.status_code == 200:
                        print("  ✅ Confluence authentication successful")
                    
                    self.results["authentication"]["confluence"] = {
                        "status_code": confluence_response.status_code,
                        "success": confluence_response.status_code == 200
                    }
                    
            except Exception as e:
                print(f"  ❌ Confluence auth error: {str(e)}")
                self.results["authentication"]["confluence"] = {"error": str(e)}
                self.results["summary"]["issues"].append(f"Confluence authentication error: {str(e)}")
    
    async def _check_permissions_and_paths(self):
        """Check file system permissions and path issues"""
        print("\n📁 Permissions and Paths Check")
        print("-" * 40)
        
        # Check current working directory
        cwd = os.getcwd()
        print(f"  Current directory: {cwd}")
        
        # Check if key files exist
        key_files = [
            "config.py",
            "tools/atlassian_tool.py",
            "run_mcp_server.py",
            "prompts.yaml"
        ]
        
        file_status = {}
        for file_path in key_files:
            exists = os.path.exists(file_path)
            file_status[file_path] = exists
            print(f"  {file_path}: {'✅ Exists' if exists else '❌ Missing'}")
            
            if not exists:
                self.results["summary"]["issues"].append(f"Missing file: {file_path}")
        
        self.results["permissions"]["cwd"] = cwd
        self.results["permissions"]["files"] = file_status
        
        # Check write permissions for logs
        try:
            test_file = "test_write_permissions.tmp"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print(f"  Write permissions: ✅ OK")
            self.results["permissions"]["write_access"] = True
        except Exception as e:
            print(f"  Write permissions: ❌ Failed - {str(e)}")
            self.results["permissions"]["write_access"] = False
            self.results["summary"]["issues"].append(f"Write permission error: {str(e)}")
    
    async def _test_production_execution_flow(self):
        """Test the actual production execution flow that's failing"""
        print("\n⚡ Production Execution Flow Test")
        print("-" * 40)
        
        try:
            # Test the exact flow that fails in production
            tool = AtlassianTool()
            
            if not tool.available:
                print("  ❌ Cannot test - tool not available")
                return
            
            # Test minimal Confluence search (the most likely to work)
            print("  Testing minimal Confluence search...")
            
            result = await asyncio.wait_for(
                tool.execute_mcp_tool('confluence_search', {
                    'query': 'test',
                    'limit': 1
                }),
                timeout=30.0
            )
            
            print(f"  Result type: {type(result)}")
            print(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if result.get('success'):
                print("  ✅ Execution successful")
                self.results["atlassian_tool"]["execution_test"] = "success"
            elif 'error' in result:
                print(f"  ❌ Execution error: {result['error']}")
                print(f"  Error message: {result.get('message', 'No message')}")
                self.results["atlassian_tool"]["execution_test"] = "failed"
                self.results["atlassian_tool"]["execution_error"] = result
                self.results["summary"]["issues"].append(f"Execution test failed: {result.get('message', result['error'])}")
            else:
                print(f"  ❓ Unexpected result: {result}")
                self.results["atlassian_tool"]["execution_test"] = "unexpected"
                self.results["atlassian_tool"]["unexpected_result"] = result
                
        except asyncio.TimeoutError:
            print("  ❌ Execution timeout (30s)")
            self.results["atlassian_tool"]["execution_test"] = "timeout"
            self.results["summary"]["issues"].append("Execution test timed out after 30 seconds")
        except Exception as e:
            print(f"  ❌ Execution exception: {str(e)}")
            print(f"  Full traceback:")
            traceback.print_exc()
            self.results["atlassian_tool"]["execution_test"] = "exception"
            self.results["atlassian_tool"]["execution_exception"] = str(e)
            self.results["summary"]["issues"].append(f"Execution test exception: {str(e)}")
    
    def _generate_summary(self):
        """Generate diagnostic summary and recommendations"""
        issues = self.results["summary"]["issues"]
        recommendations = []
        
        # Environment issues
        if any("Missing environment variable" in issue for issue in issues):
            recommendations.append("Configure missing environment variables in Replit Secrets")
        
        # Network issues
        if any("Network" in issue for issue in issues):
            recommendations.append("Check network connectivity and firewall settings")
        
        # Authentication issues
        if any("authentication" in issue.lower() for issue in issues):
            recommendations.append("Verify Atlassian credentials are correct and have proper permissions")
        
        # MCP server issues
        if any("MCP server" in issue for issue in issues):
            recommendations.append("Restart MCP server workflow or check server logs")
        
        # Timeout issues
        if any("timeout" in issue.lower() for issue in issues):
            recommendations.append("Increase timeout values or check for performance bottlenecks")
        
        # Generic execution errors
        if any("Execution" in issue for issue in issues):
            recommendations.append("Check detailed error logs and verify all dependencies are available")
        
        if not issues:
            recommendations.append("No issues detected - system appears to be functioning correctly")
        
        self.results["summary"]["recommendations"] = recommendations
    
    def _print_results(self):
        """Print diagnostic results summary"""
        print("\n" + "=" * 60)
        print("🎯 DIAGNOSTIC SUMMARY")
        print("=" * 60)
        
        issues = self.results["summary"]["issues"]
        recommendations = self.results["summary"]["recommendations"]
        
        if issues:
            print(f"\n❌ Issues Found ({len(issues)}):")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ No issues detected")
        
        print(f"\n💡 Recommendations ({len(recommendations)}):")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        print(f"\n📊 Full results saved to diagnostic results")

async def main():
    """Run deployment diagnostic"""
    diagnostic = DeploymentDiagnostic()
    results = await diagnostic.run_full_diagnosis()
    
    # Save results to file for analysis
    with open("deployment_diagnostic_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: deployment_diagnostic_results.json")
    
    return len(results["summary"]["issues"]) == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)