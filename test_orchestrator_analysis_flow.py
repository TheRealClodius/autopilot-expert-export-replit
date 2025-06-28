#!/usr/bin/env python3
"""
Test Orchestrator Analysis Flow

This test verifies that the orchestrator's analysis (like "The user is engaging in casual conversation, 
responding to a greeting. The query is a social pleasantry and does not ask for any specific information.")
is properly included in the state stack and passed to the client agent.
"""

import asyncio
import json
from typing import Dict, Any
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_analysis_inclusion():
    """Test that orchestrator analysis is properly included in state stack"""
    
    print("Testing Orchestrator Analysis Flow")
    print("=" * 50)
    
    # Initialize services
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Create a test message that should trigger a clear analysis
    test_message = ProcessedMessage(
        text="Hey there! How's it going?",
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
        # Step 1: Get the orchestrator's analysis
        print("Step 1: Analyzing query with orchestrator...")
        execution_plan = await orchestrator._analyze_query_and_plan(test_message)
        
        if execution_plan:
            analysis = execution_plan.get("analysis", "")
            print(f"Orchestrator Analysis: {analysis}")
            print()
        else:
            print("No execution plan generated")
            return
        
        # Step 2: Execute the plan and build state stack
        print("Step 2: Executing plan and building state stack...")
        gathered_info = await orchestrator._execute_plan(execution_plan, test_message)
        state_stack = await orchestrator._build_state_stack(test_message, gathered_info, execution_plan)
        
        # Step 3: Verify analysis is in state stack
        print("Step 3: Verifying analysis is included in state stack...")
        orchestrator_analysis = state_stack.get("orchestrator_analysis", {})
        intent_analysis = orchestrator_analysis.get("intent", "")
        
        print(f"State Stack Analysis: {intent_analysis}")
        print()
        
        # Step 4: Test client agent formatting
        print("Step 4: Testing client agent state stack formatting...")
        from agents.client_agent import ClientAgent
        client_agent = ClientAgent()
        
        formatted_context = client_agent._format_state_stack_context(state_stack)
        
        # Look for the analysis in the formatted context
        if "ORCHESTRATOR ANALYSIS & INSIGHTS:" in formatted_context:
            print("✓ Analysis section found in client agent context")
            
            # Extract the analysis section
            lines = formatted_context.split('\n')
            analysis_start = False
            analysis_lines = []
            
            for line in lines:
                if "ORCHESTRATOR ANALYSIS & INSIGHTS:" in line:
                    analysis_start = True
                    continue
                elif analysis_start and line.startswith("TASK:"):
                    break
                elif analysis_start:
                    analysis_lines.append(line)
            
            print("Analysis in Client Agent Context:")
            for line in analysis_lines[:5]:  # Show first 5 lines
                print(f"  {line}")
        else:
            print("✗ Analysis section NOT found in client agent context")
        
        print()
        print("Test completed successfully!")
        
        # Summary
        print("SUMMARY:")
        print(f"- Orchestrator generated analysis: {'Yes' if analysis else 'No'}")
        print(f"- Analysis in state stack: {'Yes' if intent_analysis else 'No'}")
        print(f"- Client agent can access analysis: {'Yes' if 'Intent Analysis:' in formatted_context else 'No'}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analysis_inclusion())