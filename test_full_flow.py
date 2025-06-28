#!/usr/bin/env python3
"""
Test the full message processing flow to ensure greeting responses work properly
"""
import asyncio
import json
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService

async def test_full_greeting_flow():
    """Test full message flow with greeting"""
    try:
        # Initialize services
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        client_agent = ClientAgent()
        
        # Create test message
        test_message = ProcessedMessage(
            text="Hey buddy",
            user_id="U_TEST_USER",
            user_name="TestUser", 
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts="1735000000.000001",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        print("Testing Full Flow: 'Hey buddy'")
        print("=" * 50)
        
        # Step 1: Orchestrator analysis
        print("1. Orchestrator Analysis:")
        plan = await orchestrator._analyze_query_and_plan(test_message)
        print(json.dumps(plan, indent=2))
        print()
        
        # Step 2: Execute plan
        print("2. Plan Execution:")
        gathered_info = await orchestrator._execute_plan(plan, test_message)
        print(json.dumps(gathered_info, indent=2))
        print()
        
        # Step 3: Client agent response
        print("3. Client Agent Response:")
        response = await client_agent.generate_response(
            test_message,
            gathered_info,
            plan.get("context", {})
        )
        print(json.dumps(response, indent=2))
        print()
        
        # Step 4: Full orchestrator process (what actually happens in production)
        print("4. Full Orchestrator Process:")
        full_response = await orchestrator.process_query(test_message)
        print(json.dumps(full_response, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_greeting_flow())