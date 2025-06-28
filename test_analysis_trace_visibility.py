#!/usr/bin/env python3
"""
Test Analysis Trace Visibility

This test runs a complete message flow to generate visible traces
in LangSmith showing the orchestrator analysis being passed to client agent.
"""

import asyncio
import json
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_trace_visibility():
    """Test complete flow with trace visibility for analysis"""
    
    print("Testing Analysis Trace Visibility")
    print("=" * 50)
    
    # Initialize services
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Test cases that should show clear analysis
    test_cases = [
        {
            "text": "What is Autopilot and how does it work?",
            "description": "Information request - should trigger vector search and detailed analysis"
        },
        {
            "text": "Thanks for the explanation!",
            "description": "Gratitude - should show simple analysis without tools"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['description']}")
        print(f"Message: '{test_case['text']}'")
        print("-" * 50)
        
        # Create test message with unique timestamp
        test_message = ProcessedMessage(
            text=test_case["text"],
            user_id="U_TRACE_TEST",
            user_name="TraceTestUser",
            user_first_name="Trace",
            user_display_name="Trace Test User",
            user_title="Product Manager",
            user_department="Product",
            channel_id="C_TRACE_TEST",
            channel_name="trace-test-channel",
            message_ts=str(int(datetime.now().timestamp()) + i * 10),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        try:
            print(f"🔄 Processing through orchestrator...")
            
            # Process through full orchestrator pipeline
            response = await orchestrator.process_query(test_message)
            
            if response:
                print(f"✅ Response generated: {response.get('text', '')[:100]}...")
                print(f"📊 Check LangSmith for trace ID containing: {test_message.message_ts}")
                print()
            else:
                print("❌ No response generated")
                print()
                
        except Exception as e:
            print(f"❌ Error: {e}")
            print()

if __name__ == "__main__":
    asyncio.run(test_trace_visibility())