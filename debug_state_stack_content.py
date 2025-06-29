#!/usr/bin/env python3
"""
Debug State Stack Content

This test will show exactly what's in the state stack and 
identify why the orchestrator analysis isn't appearing.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO)

async def debug_state_stack():
    """Debug what's actually in the state stack"""
    print("🔍 DEBUGGING STATE STACK CONTENT")
    print("=" * 50)
    
    try:
        # Initialize services
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create simple test message  
        test_message = ProcessedMessage(
            text="Find Autopilot for Everyone documentation",
            user_id="U_TEST_USER",
            user_name="TestUser",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Engineer",
            user_department="Engineering",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=str(int(datetime.now().timestamp())),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        print(f"🎯 Test Query: '{test_message.text}'")
        print()
        
        # Create a simple mock gathered_info with atlassian results
        mock_gathered_info = {
            "vector_results": [],
            "perplexity_results": [],
            "atlassian_results": [
                {
                    "action_type": "confluence_search",
                    "result": {
                        "success": True,
                        "result": [
                            {"title": "Autopilot for Everyone", "url": "https://example.com/page1"},
                            {"title": "Autopilot Framework", "url": "https://example.com/page2"}
                        ]
                    },
                    "success": True
                }
            ]
        }
        
        mock_execution_plan = {
            "analysis": "User is asking for Autopilot documentation",
            "tools_needed": ["atlassian_search"]
        }
        
        print("1️⃣ Building state stack with mock Atlassian results...")
        
        # Test state stack building directly
        state_stack = await orchestrator._build_state_stack(test_message, mock_gathered_info, mock_execution_plan)
        
        print("✅ State stack built successfully")
        print(f"   State stack keys: {list(state_stack.keys())}")
        print()
        
        print("2️⃣ Examining orchestrator_analysis in state stack...")
        
        if "orchestrator_analysis" in state_stack:
            orch_analysis = state_stack["orchestrator_analysis"]
            print(f"   Orchestrator analysis keys: {list(orch_analysis.keys())}")
            
            if "atlassian_results" in orch_analysis:
                atlassian_results = orch_analysis["atlassian_results"]
                print(f"   ✅ Found atlassian_results: {len(atlassian_results)} items")
                
                for i, result in enumerate(atlassian_results):
                    print(f"   Result {i+1}:")
                    print(f"      Action type: {result.get('action_type')}")
                    print(f"      Success: {result.get('success')}")
                    if result.get("result") and isinstance(result["result"], dict):
                        result_data = result["result"].get("result", [])
                        if isinstance(result_data, list):
                            print(f"      Pages found: {len(result_data)}")
                            for j, page in enumerate(result_data):
                                title = page.get("title", "No title") if isinstance(page, dict) else str(page)
                                print(f"         Page {j+1}: {title}")
                        else:
                            print(f"      Result type: {type(result_data)}")
                    else:
                        print(f"      Raw result: {result.get('result')}")
                
                return True
            else:
                print("   ❌ No atlassian_results in orchestrator_analysis")
                print(f"   Available keys: {list(orch_analysis.keys())}")
                return False
        else:
            print("   ❌ No orchestrator_analysis in state stack")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_state_stack())
    if success:
        print("\n🎉 STATE STACK CONTENT VERIFIED")
        print("   Atlassian results are properly flowing through state stack")
    else:
        print("\n💥 STATE STACK ISSUE IDENTIFIED")
        print("   Atlassian results are not appearing in state stack")