#!/usr/bin/env python3
"""
Debug script to test orchestrator agent behavior with different inputs
"""
import asyncio
import json
from models.slack_event import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_orchestrator():
    """Test orchestrator with simple greeting"""
    try:
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create a simple test message
        test_message = ProcessedMessage(
            text="Hey buddy",
            user_id="U123456789",
            user_name="TestUser",
            channel_id="C123456789",
            channel_name="test-channel",
            message_ts="1640995200.001500",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        print("Testing orchestrator with message: 'Hey buddy'")
        print("=" * 50)
        
        # Test the planning phase
        plan = await orchestrator._analyze_query_and_plan(test_message)
        print("Execution Plan:")
        print(json.dumps(plan, indent=2))
        print("=" * 50)
        
        # Test full processing
        if plan:
            gathered_info = await orchestrator._execute_plan(plan, test_message)
            print("Gathered Information:")
            print(json.dumps(gathered_info, indent=2))
            print("=" * 50)
            
            # Test response generation through client agent
            from agents.client_agent import ClientAgent
            client_agent = ClientAgent()
            response = await client_agent.generate_response(
                test_message, 
                gathered_info, 
                plan.get("context", {})
            )
            print("Final Response:")
            print(json.dumps(response, indent=2))
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator())