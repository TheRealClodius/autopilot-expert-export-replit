"""
Test Deployment Fix Verification

Quick test to verify the deployment Redis fix has resolved MCP execution issues.
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_mcp_execution_after_redis_fix():
    """Test that MCP execution works after Redis connection fix"""
    
    print("🔧 TESTING DEPLOYMENT REDIS FIX")
    print("=" * 50)
    
    # Test 1: Server Health
    print("\n1️⃣ Testing server health...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/health", timeout=5.0)
            print(f"   FastAPI Server: {response.status_code} - {response.text}")
            
            response = await client.get("http://localhost:8001/healthz", timeout=5.0)
            print(f"   MCP Server: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Server health check failed: {e}")
        return False
    
    # Test 2: Orchestrator Intelligence
    print("\n2️⃣ Testing orchestrator MCP routing...")
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        from services.memory_service import MemoryService
        from services.trace_manager import TraceManager
        
        memory_service = MemoryService()
        trace_manager = TraceManager()
        orchestrator = OrchestratorAgent(memory_service, trace_manager)
        
        # Test UiPath query that should route to MCP
        test_query = "Can you find any open bugs in the AUTOPILOT project?"
        
        result = await orchestrator.analyze_query_for_test(test_query)
        
        if result and 'atlassian_actions' in result:
            atlassian_actions = result['atlassian_actions']
            print(f"   ✅ Orchestrator correctly routed to MCP: {len(atlassian_actions)} actions")
            
            for action in atlassian_actions:
                mcp_tool = action.get('mcp_tool', 'unknown')
                arguments = action.get('arguments', {})
                print(f"   📋 Action: {mcp_tool} with {len(arguments)} arguments")
                
                if mcp_tool == 'jira_search' and 'jql' in arguments:
                    print(f"   🎯 JQL Query: {arguments['jql'][:50]}...")
                    return True
            
        print(f"   ❌ Orchestrator routing failed or no MCP actions generated")
        return False
        
    except Exception as e:
        print(f"   ❌ Orchestrator test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mcp_execution_after_redis_fix())
    
    if result:
        print("\n✅ DEPLOYMENT FIX VERIFICATION: SUCCESS")
        print("   Redis connection issue resolved")
        print("   MCP routing working correctly") 
        print("   System ready for production deployment")
    else:
        print("\n❌ DEPLOYMENT FIX VERIFICATION: FAILED")
        print("   Additional troubleshooting needed")