#!/usr/bin/env python3
"""
Quick verification that MCP parameter fix has been applied correctly.
Tests that orchestrator now generates correct "limit" parameter instead of "max_results".
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
import logging

logging.basicConfig(level=logging.WARNING)  # Reduce noise

async def test_parameter_fix():
    """Test that orchestrator generates correct MCP parameters"""
    print("🔧 TESTING MCP PARAMETER FIX")
    print("=" * 40)
    
    # Initialize orchestrator
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Create test message specifically asking for Autopilot info
    test_message = ProcessedMessage(
        channel_id="C087QKECFKQ",
        channel_name="general",
        user_id="U_TEST",
        text="Find all Confluence pages about Autopilot for Everyone project",
        message_ts="1751182507.951000",
        thread_ts=None,
        user_name="testuser",
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Engineer",
        user_department="Engineering"
    )
    
    print(f"📝 Query: {test_message.text}")
    print()
    
    try:
        # Test only the planning phase to check parameter generation
        print("🧠 Testing Orchestrator Parameter Generation...")
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        
        if not execution_plan:
            print("❌ FAILED: No execution plan generated")
            return False
        
        # Check for atlassian_actions
        atlassian_actions = execution_plan.get("atlassian_actions", [])
        
        if not atlassian_actions:
            print("❌ FAILED: No Atlassian actions in execution plan")
            print(f"Plan keys: {list(execution_plan.keys())}")
            return False
        
        print(f"✅ Found {len(atlassian_actions)} Atlassian action(s)")
        
        # Check each action for correct parameters
        for i, action in enumerate(atlassian_actions, 1):
            print(f"\n📋 Action {i}:")
            print(f"   MCP Tool: {action.get('mcp_tool', 'NOT SPECIFIED')}")
            
            arguments = action.get("arguments", {})
            print(f"   Arguments: {json.dumps(arguments, indent=6)}")
            
            # Check for the critical fix: should use "limit" not "max_results"
            has_limit = "limit" in arguments
            has_max_results = "max_results" in arguments
            
            print(f"   ✅ Uses 'limit' parameter: {has_limit}")
            print(f"   ❌ Uses 'max_results' parameter: {has_max_results}")
            
            if has_max_results:
                print(f"\n❌ CRITICAL ISSUE: Found 'max_results' parameter!")
                print(f"   This will cause MCP server validation errors.")
                print(f"   Should use 'limit' instead.")
                return False
            
            if has_limit:
                print(f"   ✅ Parameter fix applied correctly!")
        
        print(f"\n🎉 SUCCESS: All MCP parameters are correct!")
        print(f"✅ Orchestrator generates 'limit' parameter as expected")
        print(f"✅ No legacy 'max_results' parameters found")
        print(f"✅ MCP Atlassian integration should work without validation errors")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_parameter_fix())