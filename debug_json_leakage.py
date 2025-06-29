#!/usr/bin/env python3
"""
Debug JSON Leakage

This test specifically traces where raw JSON from orchestrator execution plans
leaks into client agent responses, causing the "limit": 10 issue.
"""

import asyncio
import json
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage

async def trace_json_leakage():
    """Trace where JSON fragments leak from orchestrator to client agent"""
    
    print("🔍 TRACING JSON LEAKAGE FROM ORCHESTRATOR TO CLIENT AGENT")
    print("=" * 70)
    
    # Create test instances
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service=memory_service)
    client_agent = ClientAgent()
    
    # Create test message that would trigger Atlassian search
    test_message = ProcessedMessage(
        text="What are the Autopilot features?",
        user_id="U123456",
        user_name="TestUser",
        user_first_name="Test",
        user_display_name="Test User",
        user_title="",
        user_department="",
        channel_id="C123456",
        channel_name="general",
        is_dm=False,
        is_mention=True,
        thread_ts=None,
        message_ts="1234567890.123456",
        thread_context=""
    )
    
    print("Step 1: Testing orchestrator analysis")
    print("-" * 40)
    
    # Get orchestrator analysis (this will contain JSON with "limit": 10)
    execution_plan = await orchestrator._analyze_query_and_plan(test_message)
    
    if execution_plan:
        print("✅ Orchestrator generated execution plan")
        print(f"📋 Plan keys: {list(execution_plan.keys())}")
        
        # Look for the problematic "limit": 10 in the execution plan
        plan_json = json.dumps(execution_plan, indent=2)
        if '"limit": 10' in plan_json:
            print("🚨 FOUND: 'limit': 10 in orchestrator execution plan JSON")
            print("🔍 This is the source of the JSON fragments!")
        else:
            print("✅ No 'limit': 10 found in execution plan")
        
        print(f"📄 Execution plan (first 500 chars):")
        print(plan_json[:500] + "..." if len(plan_json) > 500 else plan_json)
    else:
        print("❌ No execution plan generated")
        return
    
    print("\nStep 2: Testing plan execution")
    print("-" * 40)
    
    # Execute the plan to get gathered information
    gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
    
    if gathered_info:
        print("✅ Plan execution completed")
        print(f"📋 Gathered info keys: {list(gathered_info.keys())}")
        
        # Check if gathered_info contains raw JSON
        gathered_json = json.dumps(gathered_info, indent=2)
        if '"limit": 10' in gathered_json:
            print("🚨 FOUND: 'limit': 10 in gathered information!")
            print("🔍 Raw execution plan JSON is in gathered_info")
        else:
            print("✅ No 'limit': 10 in gathered information")
    else:
        print("❌ No gathered information")
        return
    
    print("\nStep 3: Testing state stack building")
    print("-" * 40)
    
    # Build state stack for client agent
    state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
    
    if state_stack:
        print("✅ State stack built")
        print(f"📋 State stack keys: {list(state_stack.keys())}")
        
        # Check if state stack contains raw JSON
        state_json = json.dumps(state_stack, indent=2)
        if '"limit": 10' in state_json:
            print("🚨 FOUND: 'limit': 10 in state stack!")
            print("🔍 This is where JSON leaks to the client agent")
            
            # Find which section contains the JSON
            orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
            analysis_json = json.dumps(orchestrator_analysis, indent=2)
            if '"limit": 10' in analysis_json:
                print("🎯 SPECIFIC LOCATION: orchestrator_analysis section")
        else:
            print("✅ No 'limit': 10 in state stack")
    else:
        print("❌ No state stack")
        return
    
    print("\nStep 4: Testing client agent context formatting")
    print("-" * 40)
    
    # Format the state stack for the client agent's Gemini prompt
    formatted_context = client_agent._format_state_stack_context(state_stack)
    
    if '"limit": 10' in formatted_context:
        print("🚨 FOUND: 'limit': 10 in client agent Gemini prompt!")
        print("🔍 This is the EXACT cause of JSON responses")
        print("💡 Gemini sees this JSON and echoes it back")
        
        # Show where in the context it appears
        lines = formatted_context.split('\n')
        for i, line in enumerate(lines):
            if '"limit": 10' in line:
                print(f"   Line {i}: {line}")
    else:
        print("✅ No 'limit': 10 in client agent context")
    
    print(f"\n📄 Context length: {len(formatted_context)} characters")
    print(f"📄 First 300 characters of context:")
    print(formatted_context[:300] + "..." if len(formatted_context) > 300 else formatted_context)
    
    print("\n" + "=" * 70)
    print("🎯 ROOT CAUSE ANALYSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(trace_json_leakage())