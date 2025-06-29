#!/usr/bin/env python3
"""
Test Name Recognition Issue

This script tests how the agent processes and recognizes names in conversations
to identify why Sarah's name might not have been detected.
"""

import asyncio
import time
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
from utils.gemini_client import GeminiClient

async def test_name_recognition():
    """Test how the agent handles names in conversations"""
    print("=== TESTING NAME RECOGNITION ===")
    
    # Initialize services
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    client_agent = ClientAgent()
    gemini_client = GeminiClient()
    
    # Test messages with names
    test_messages = [
        "Hello Sarah, how are you today?",
        "Sarah mentioned she's working on the UiPath project",
        "Can you ask Sarah about the design requirements?",
        "I was talking to Sarah yesterday about Autopilot features",
        "Sarah's name is Sarah Johnson and she's on our team"
    ]
    
    for i, message_text in enumerate(test_messages):
        print(f"\n--- Test {i+1}: {message_text} ---")
        
        # Create test message
        message = ProcessedMessage(
            text=message_text,
            user_id="U_TEST_USER",
            user_name="TestUser", 
            user_first_name="John",
            user_display_name="John Doe",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=f"{int(time.time())}.{i:06d}",
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        try:
            # Test entity extraction directly
            entities = await gemini_client.extract_entities(message_text)
            print(f"Extracted entities: {entities}")
            
            # Test orchestrator analysis
            start_time = time.time()
            response = await orchestrator.process_query(message)
            processing_time = time.time() - start_time
            
            print(f"Processing time: {processing_time:.2f}s")
            print(f"Response: {response.get('text', 'No response')[:200]}...")
            
            # Check if Sarah is mentioned in response
            response_text = response.get('text', '').lower()
            if 'sarah' in response_text:
                print("✅ Sarah's name found in response")
            else:
                print("❌ Sarah's name NOT found in response")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
    
    print("\n=== TESTING COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_name_recognition())