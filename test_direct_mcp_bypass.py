#!/usr/bin/env python3

"""
Test Direct MCP Bypass
Test MCP execution bypassing all orchestrator complexity
"""

import asyncio
import sys
sys.path.append('.')

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_direct_mcp_bypass():
    """Test the new direct MCP execution method"""
    
    print("🔧 TESTING DIRECT MCP BYPASS")
    print("=" * 50)
    
    try:
        # Initialize minimal services
        print("1️⃣ Initializing orchestrator...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        if not orchestrator.atlassian_tool.available:
            print("❌ Atlassian tool not available")
            return False
        
        print("✅ Orchestrator initialized")
        
        # Test direct MCP execution method
        print("\n2️⃣ Testing direct MCP execution...")
        action = {
            "mcp_tool": "confluence_search",
            "arguments": {
                "query": "autopilot for everyone",
                "limit": 3
            }
        }
        
        print(f"   Action: {action}")
        print("   Calling _execute_mcp_action_direct...")
        
        result = await orchestrator._execute_mcp_action_direct(action)
        
        print(f"\n📊 DIRECT MCP RESULT:")
        print("=" * 50)
        
        if result and result.get("success"):
            print(f"✅ Direct MCP execution successful")
            print(f"   Result type: {type(result.get('result', []))}")
            
            results = result.get("result", [])
            if isinstance(results, list) and len(results) > 0:
                print(f"   Found {len(results)} results:")
                for i, item in enumerate(results[:2]):
                    if isinstance(item, dict):
                        title = item.get("title", "No title")
                        url = item.get("url", "No URL")
                        print(f"     {i+1}. {title}")
                        print(f"        URL: {url}")
            else:
                print(f"   No valid results found")
            
            return True
        else:
            print(f"❌ Direct MCP execution failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_mcp_bypass())
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")