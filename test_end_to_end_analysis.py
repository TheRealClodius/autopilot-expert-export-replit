#!/usr/bin/env python3
"""
End-to-End Analysis Test

Test the complete flow from message input to final response,
verifying that orchestrator analysis influences the client agent response.
"""

import asyncio
import json
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_end_to_end_with_analysis():
    """Test complete flow including orchestrator analysis influence on response"""
    
    print("End-to-End Analysis Flow Test")
    print("=" * 50)
    
    # Initialize services
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Test different types of messages to see how analysis changes
    test_cases = [
        {
            "text": "Hey buddy, how's it going?",
            "description": "Casual greeting"
        },
        {
            "text": "Can you explain what Autopilot is?",
            "description": "Information request"
        },
        {
            "text": "Thanks for the help!",
            "description": "Gratitude expression"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['description']}")
        print(f"Message: '{test_case['text']}'")
        print("-" * 30)
        
        # Create test message
        test_message = ProcessedMessage(
            text=test_case["text"],
            user_id="U_TEST_USER",
            user_name="TestUser",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Software Engineer",
            user_department="Engineering",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=str(int(datetime.now().timestamp()) + i),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        try:
            # Process through orchestrator
            response = await orchestrator.process_query(test_message)
            
            if response:
                print(f"✓ Generated response: {response.get('text', '')[:100]}...")
                print()
            else:
                print("✗ No response generated")
                print()
                
        except Exception as e:
            print(f"✗ Error: {e}")
            print()

if __name__ == "__main__":
    asyncio.run(test_end_to_end_with_analysis())