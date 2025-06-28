#!/usr/bin/env python3
"""
Quick test of tool flow - verify search results reach client agent
"""

import asyncio
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_quick():
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Create test message
    test_message = ProcessedMessage(
        channel_id="C087QKECFKQ",
        user_id="U12345TEST", 
        text="Autopilot is an AI, right?",
        message_ts="1640995200.001500",
        thread_ts=None,
        user_name="test_user",
        user_first_name="Test",
        user_display_name="Test User", 
        user_title="Engineer",
        user_department="Engineering",
        channel_name="general",
        is_dm=False,
        thread_context=""
    )
    
    print("Testing search results flow...")
    
    # Test orchestrator flow
    execution_plan = await orchestrator._analyze_query_and_plan(test_message)
    if not execution_plan:
        print("No execution plan")
        return
        
    gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
    vector_results = gathered_info.get("vector_results", [])
    print(f"Vector results found: {len(vector_results)}")
    
    state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
    orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
    search_results_in_state = orchestrator_analysis.get("search_results", [])
    print(f"Search results in state stack: {len(search_results_in_state)}")
    
    # Test client formatting
    client_agent = orchestrator.client_agent
    formatted_context = client_agent._format_state_stack_context(state_stack)
    
    # Check for search results in formatted context
    if "Vector Search Results:" in formatted_context:
        print("✅ Search results found in client context!")
        # Show relevant lines
        lines = formatted_context.split('\n')
        for i, line in enumerate(lines):
            if "Vector Search Results:" in line or (line.strip() and any(line.strip().startswith(f"{j}.") for j in range(1, 6))):
                print(f"  {line}")
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if next_line.strip():
                        print(f"  {next_line}")
    else:
        print("❌ No search results in client context")
        print("Context preview:")
        print(formatted_context[:500] + "...")

if __name__ == "__main__":
    asyncio.run(test_quick())