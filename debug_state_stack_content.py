#!/usr/bin/env python3
"""
Debug State Stack Content

This test will show exactly what's in the state stack and 
identify why the orchestrator analysis isn't appearing.
"""

import asyncio
import json
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def debug_state_stack():
    """Debug what's actually in the state stack"""
    
    print("Debugging State Stack Content")
    print("=" * 50)
    
    # Initialize services
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Create test message
    test_message = ProcessedMessage(
        text="Hello my dude",
        user_id="U_TEST_USER",
        user_name="TestUser",
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Software Engineer",
        user_department="Engineering",
        channel_id="C_TEST_CHANNEL",
        channel_name="test-channel",
        message_ts=str(int(datetime.now().timestamp())),
        thread_ts=None,
        is_dm=False,
        thread_context=None
    )
    
    print(f"Test Message: '{test_message.text}'")
    print()
    
    try:
        # Step 1: Get execution plan
        print("Step 1: Getting execution plan...")
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        print("Execution Plan:")
        print(json.dumps(execution_plan, indent=2))
        print()
        
        # Step 2: Execute plan
        print("Step 2: Executing plan...")
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        print("Gathered Info:")
        print(json.dumps(gathered_info, indent=2))
        print()
        
        # Step 3: Build state stack
        print("Step 3: Building state stack...")
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        print("Complete State Stack:")
        print(json.dumps(state_stack, indent=2))
        print()
        
        # Step 4: Check what client agent sees
        print("Step 4: Client agent view...")
        from agents.client_agent import ClientAgent
        client_agent = ClientAgent()
        formatted_context = client_agent._format_state_stack_context(state_stack)
        
        print("Formatted Context for Client Agent:")
        print("-" * 40)
        print(formatted_context)
        print("-" * 40)
        
        # Step 5: Identify issues
        print("Step 5: Analysis...")
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        intent = orchestrator_analysis.get("intent", "")
        
        print(f"Has orchestrator_analysis in state_stack: {bool(orchestrator_analysis)}")
        print(f"Has intent in orchestrator_analysis: {bool(intent)}")
        print(f"Intent content: '{intent}'")
        
        if "ORCHESTRATOR ANALYSIS & INSIGHTS:" in formatted_context:
            print("✓ Analysis section found in formatted context")
        else:
            print("✗ Analysis section MISSING from formatted context")
        
        # Check conversation history
        conv_history = state_stack.get("conversation_history", {})
        recent_exchanges = conv_history.get("recent_exchanges", [])
        print(f"Recent exchanges count: {len(recent_exchanges)}")
        for i, exchange in enumerate(recent_exchanges):
            print(f"  Exchange {i}: {exchange}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_state_stack())