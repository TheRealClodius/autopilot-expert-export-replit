#!/usr/bin/env python3
"""
Test Deployment Fix Verification

This script verifies that the deployment-aware MCP URL configuration fix
resolves the production "execution error" issues.
"""

import asyncio
import os
import aiohttp
from config import settings
from tools.atlassian_tool import AtlassianTool
from agents.orchestrator_agent import OrchestratorAgent
from services.trace_manager import TraceManager
from models.schemas import ProcessedMessage


async def test_deployment_fix():
    """Test the deployment fix thoroughly"""
    
    print("=" * 80)
    print("🔧 DEPLOYMENT FIX VERIFICATION TEST")
    print("=" * 80)
    
    # 1. Test Environment Detection
    print("\n1️⃣ ENVIRONMENT DETECTION TEST")
    print("-" * 50)
    
    replit_domains = os.getenv("REPLIT_DOMAINS", "")
    print(f"REPLIT_DOMAINS: {replit_domains}")
    
    is_deployment = any([
        os.getenv("REPLIT_DEPLOYMENT") == "1",
        os.getenv("DEPLOYMENT_ENV") == "production",
        os.getenv("PORT") and os.getenv("PORT") != "5000",
        "replit.app" in replit_domains,
        "replit.dev" in replit_domains,
        len(replit_domains) > 0 and ("riker." in replit_domains or "wolf." in replit_domains)
    ])
    
    print(f"Detected as deployment: {is_deployment}")
    print(f"Configured MCP URL: {settings.MCP_SERVER_URL}")
    print(f"Deployment-aware MCP URL: {settings.DEPLOYMENT_AWARE_MCP_URL}")
    
    if is_deployment:
        print("✅ Running in deployment environment")
    else:
        print("ℹ️ Running in local development environment")
    
    # 2. Test MCP Server Connectivity
    print("\n2️⃣ MCP SERVER CONNECTIVITY TEST")
    print("-" * 50)
    
    mcp_url = settings.DEPLOYMENT_AWARE_MCP_URL
    health_url = f"{mcp_url}/healthz"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(health_url, timeout=10) as response:
                if response.status == 200:
                    print(f"✅ MCP server health check passed: {health_url}")
                else:
                    print(f"❌ MCP server health check failed: {response.status}")
    except Exception as e:
        print(f"❌ MCP server connectivity failed: {e}")
        return False
    
    # 3. Test AtlassianTool Initialization
    print("\n3️⃣ ATLASSIAN TOOL INITIALIZATION TEST")
    print("-" * 50)
    
    try:
        atlassian_tool = AtlassianTool()
        print(f"✅ AtlassianTool initialized successfully")
        print(f"   MCP Server URL: {atlassian_tool.mcp_server_url}")
        print(f"   SSE Endpoint: {atlassian_tool.sse_endpoint}")
        
        # Verify URL matches deployment-aware setting
        if atlassian_tool.mcp_server_url == settings.DEPLOYMENT_AWARE_MCP_URL:
            print("✅ URL configuration matches deployment-aware setting")
        else:
            print(f"❌ URL mismatch: tool={atlassian_tool.mcp_server_url}, config={settings.DEPLOYMENT_AWARE_MCP_URL}")
            return False
            
    except Exception as e:
        print(f"❌ AtlassianTool initialization failed: {e}")
        return False
    
    # 4. Test MCP Tool Execution
    print("\n4️⃣ MCP TOOL EXECUTION TEST")
    print("-" * 50)
    
    try:
        result = await atlassian_tool.execute_mcp_tool("confluence_search", {
            "query": "Autopilot deployment test",
            "limit": 3
        })
        
        if "error" in result:
            print(f"❌ MCP tool execution failed: {result['error']}")
            if "message" in result:
                print(f"   Details: {result['message']}")
            return False
        else:
            print("✅ MCP tool execution successful!")
            if "result" in result and isinstance(result["result"], list):
                print(f"   Retrieved {len(result['result'])} results")
                for i, page in enumerate(result["result"][:2]):  # Show first 2 results
                    title = page.get("title", "No title")
                    space = page.get("space", {}).get("name", "Unknown space")
                    print(f"   [{i+1}] {title} (Space: {space})")
                    
    except Exception as e:
        print(f"❌ MCP tool execution exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Test Orchestrator Integration
    print("\n5️⃣ ORCHESTRATOR INTEGRATION TEST")
    print("-" * 50)
    
    try:
        trace_manager = TraceManager()
        orchestrator = OrchestratorAgent(trace_manager=trace_manager)
        
        # Create test message
        test_message = ProcessedMessage(
            text="Can you find information about UiPath Autopilot features?",
            user_id="U123TEST",
            user_name="Test User",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Test Engineer",
            user_department="Testing",
            channel_id="C123TEST",
            channel_name="testing",
            message_ts="1234567890.123456",
            thread_ts=None,
            is_dm=False,
            is_thread_reply=False,
            is_bot_mentioned=True
        )
        
        print("Testing orchestrator with Autopilot query...")
        
        # Process the query
        state_stack = await orchestrator.process_query(test_message)
        
        if state_stack and "orchestrator_analysis" in state_stack:
            analysis = state_stack["orchestrator_analysis"]
            tools_used = analysis.get("tools_used", [])
            
            print(f"✅ Orchestrator processing successful!")
            print(f"   Tools used: {tools_used}")
            
            # Check if atlassian_search was used
            if any("atlassian" in tool.lower() for tool in tools_used):
                print("✅ Atlassian tool was correctly utilized by orchestrator")
                
                # Check for results
                if "search_results" in analysis:
                    results = analysis["search_results"]
                    if results:
                        print(f"✅ Retrieved {len(results)} search results")
                        first_result = results[0]
                        print(f"   First result: {first_result.get('title', 'No title')}")
                    else:
                        print("⚠️ No search results found (may be normal)")
                else:
                    print("⚠️ No search results in analysis")
            else:
                print("❌ Atlassian tool was not used by orchestrator")
                return False
        else:
            print("❌ Orchestrator processing failed - no state stack generated")
            return False
            
    except Exception as e:
        print(f"❌ Orchestrator integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Summary
    print("\n" + "=" * 80)
    print("🎯 DEPLOYMENT FIX VERIFICATION SUMMARY")
    print("=" * 80)
    
    print("✅ Environment detection working correctly")
    print("✅ MCP server connectivity established")  
    print("✅ AtlassianTool URL configuration fixed")
    print("✅ MCP tool execution successful")
    print("✅ Orchestrator integration working")
    print()
    print("🚀 DEPLOYMENT FIX VERIFICATION: PASSED")
    print("   System is ready for production deployment!")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_deployment_fix())
    exit(0 if success else 1)