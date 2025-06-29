#!/usr/bin/env python3

"""
Test Jira MCP Integration Debug
Specifically test Jira operations to identify execution errors
"""

import asyncio
import sys
sys.path.append('.')

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_jira_mcp_debug():
    """Test Jira MCP operations to identify the execution error"""
    
    print("🔧 TESTING JIRA MCP DEBUG")
    print("=" * 50)
    
    try:
        # Initialize services
        print("1️⃣ Initializing orchestrator...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        if not orchestrator.atlassian_tool.available:
            print("❌ Atlassian tool not available")
            return False
        
        print("✅ Orchestrator initialized")
        
        # Test Jira search
        print("\n2️⃣ Testing Jira search...")
        jira_action = {
            "mcp_tool": "jira_search",
            "arguments": {
                "jql": "project = DESIGN ORDER BY created DESC",
                "limit": 5
            }
        }
        
        print(f"   Action: {jira_action}")
        
        result = await orchestrator._execute_mcp_action_direct(jira_action)
        
        print(f"\n📊 JIRA SEARCH RESULT:")
        print("=" * 50)
        
        if result and result.get("success"):
            print(f"✅ Jira search successful")
            results = result.get("result", [])
            print(f"   Found {len(results)} results")
            
            for i, issue in enumerate(results if isinstance(results, list) else []):
                if isinstance(issue, dict):
                    key = issue.get("key", "No key")
                    summary = issue.get("fields", {}).get("summary", "No summary")
                    print(f"     {i+1}. {key}: {summary}")
            
            return True
        else:
            print(f"❌ Jira search failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            
            # Try a simpler query
            print("\n3️⃣ Trying simpler Jira query...")
            simple_action = {
                "mcp_tool": "jira_search",
                "arguments": {
                    "jql": "ORDER BY created DESC",
                    "limit": 3
                }
            }
            
            simple_result = await orchestrator._execute_mcp_action_direct(simple_action)
            
            if simple_result and simple_result.get("success"):
                print(f"✅ Simple Jira query worked")
                return True
            else:
                print(f"❌ Simple Jira query also failed")
                print(f"   Error: {simple_result.get('error', 'Unknown error')}")
                return False
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_jira_mcp_debug())
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")