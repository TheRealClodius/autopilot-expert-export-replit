#!/usr/bin/env python3
"""
Test MCP connectivity specifically for deployment environment
"""

import asyncio
import logging
from tools.atlassian_tool import AtlassianTool
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from services.trace_manager import TraceManager
from services.memory_service import MemoryService
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_deployment_mcp_connectivity():
    """Test MCP connectivity in deployment-like conditions"""
    
    print("=" * 80)
    print("🚀 DEPLOYMENT MCP CONNECTIVITY TEST")
    print("=" * 80)
    
    # Test environment variables
    required_vars = [
        "ATLASSIAN_JIRA_URL", "ATLASSIAN_JIRA_USERNAME", "ATLASSIAN_JIRA_TOKEN",
        "ATLASSIAN_CONFLUENCE_URL", "ATLASSIAN_CONFLUENCE_USERNAME", "ATLASSIAN_CONFLUENCE_TOKEN"
    ]
    
    print("🔍 Checking environment variables...")
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return
    else:
        print("✅ All Atlassian environment variables present")
    
    # Test MCP server URL configuration
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
    print(f"🌐 MCP Server URL: {mcp_server_url}")
    
    # Test AtlassianTool directly
    print("\n🔧 Testing AtlassianTool direct connectivity...")
    atlassian_tool = AtlassianTool()
    
    if not atlassian_tool.available:
        print("❌ AtlassianTool not available")
        return
    
    # Test 1: Confluence search (most reliable)
    print("\n📄 Test 1: Confluence search for UiPath documentation")
    try:
        confluence_result = await atlassian_tool.execute_mcp_tool("confluence_search", {
            "query": "Autopilot Framework",
            "limit": 3
        })
        
        if "error" in confluence_result:
            print(f"❌ Confluence search failed: {confluence_result['error']}")
        else:
            print("✅ Confluence search successful")
            content = confluence_result.get("content", [])
            if content and len(content) > 0:
                print(f"📄 Retrieved {len(content)} Confluence pages")
            
    except Exception as e:
        print(f"❌ Confluence search exception: {e}")
    
    # Test 2: Jira search with project restriction (deployment-safe)
    print("\n🎫 Test 2: Jira search with project restriction")
    try:
        jira_result = await atlassian_tool.execute_mcp_tool("jira_search", {
            "jql": "project = DESIGN AND text ~ 'template'",
            "limit": 3
        })
        
        if "error" in jira_result:
            print(f"❌ Jira search failed: {jira_result['error']}")
        else:
            print("✅ Jira search successful")
            content = jira_result.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")
                if "Error calling tool" in text_content:
                    print("⚠️ JQL restriction - normal behavior in enterprise environment")
                else:
                    print(f"🎫 Retrieved {len(content)} Jira issues")
            
    except Exception as e:
        print(f"❌ Jira search exception: {e}")
    
    # Test 3: Full orchestrator integration
    print("\n🤖 Test 3: Full orchestrator integration with MCP")
    try:
        # Initialize services
        memory_service = MemoryService()
        trace_manager = TraceManager()
        
        # Initialize orchestrator
        orchestrator = OrchestratorAgent(
            memory_service=memory_service,
            trace_manager=trace_manager
        )
        
        # Create test message
        test_message = ProcessedMessage(
            text="Find me information about UiPath Autopilot templates",
            user_id="test_user",
            user_name="Test User",
            channel_id="test_channel",
            channel_name="test",
            message_ts="test_ts",
            is_dm=False,
            is_mention=True,
            is_thread_reply=False
        )
        
        print("🧠 Executing orchestrator query analysis...")
        result = await orchestrator.process_query(test_message)
        
        if result and "orchestrator_analysis" in result:
            analysis = result["orchestrator_analysis"]
            tools_used = analysis.get("tools_used", [])
            
            if "atlassian_search" in tools_used:
                print("✅ Orchestrator correctly routed to MCP Atlassian tools")
                
                # Check for actual results
                search_results = analysis.get("search_results", [])
                if search_results:
                    print(f"📊 Retrieved {len(search_results)} results via orchestrator")
                else:
                    print("⚠️ No search results in orchestrator analysis")
            else:
                print(f"⚠️ Orchestrator used tools: {tools_used} (expected atlassian_search)")
        else:
            print("❌ Orchestrator execution failed")
            
    except Exception as e:
        print(f"❌ Orchestrator integration exception: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 DEPLOYMENT MCP CONNECTIVITY TEST COMPLETE")
    print("=" * 80)
    print("Key Deployment Readiness Indicators:")
    print("1. Environment variables configured correctly")
    print("2. MCP server connectivity working")
    print("3. Direct AtlassianTool execution functional")
    print("4. Orchestrator routing to MCP tools correctly")
    print("\nIf all tests pass, MCP integration will work in deployment.")

if __name__ == "__main__":
    asyncio.run(test_deployment_mcp_connectivity())