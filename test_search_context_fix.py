#!/usr/bin/env python3
"""
Test Search Context Fix

Verify that search progress traces now show specific topics
instead of generic "knowledge base" text.
"""

import asyncio
import time
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

async def test_search_context_fix():
    """Test that search traces now show specific context"""
    
    print("Testing Search Context Fix")
    print("=" * 50)
    
    captured_traces = []
    
    async def capture_trace(message: str):
        captured_traces.append(message)
        print(f"TRACE: {message}")
    
    try:
        # Initialize components
        memory = MemoryService()
        tracker = ProgressTracker(update_callback=capture_trace)
        orchestrator = OrchestratorAgent(memory, tracker)
        
        # Test query that should trigger knowledge base search
        test_message = ProcessedMessage(
            channel_id="C_TEST_FIX",
            user_id="U_TEST_FIX", 
            text="How do I configure UiPath Autopilot for document processing workflows?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Alex",
            user_display_name="Alex Chen",
            user_title="RPA Developer",
            user_department="Automation",
            channel_name="testing",
            is_dm=False,
            thread_context=""
        )
        
        print(f"Query: {test_message.text}")
        print("\nCaptured Traces:")
        print("-" * 30)
        
        # Process with timeout
        try:
            await asyncio.wait_for(
                orchestrator.process_query(test_message),
                timeout=8.0
            )
        except asyncio.TimeoutError:
            print("Timeout reached, analyzing captured traces...")
        
        print("-" * 30)
        
        # Analyze traces
        search_traces = [t for t in captured_traces if "looking internally" in t.lower() or "searching" in t.lower()]
        
        print(f"\nAnalysis:")
        print(f"Total traces captured: {len(captured_traces)}")
        print(f"Search-related traces: {len(search_traces)}")
        
        # Check for the old bug
        generic_traces = [t for t in captured_traces if "knowledge base" in t.lower() and "about knowledge base" in t.lower()]
        
        # Check for proper contextual traces
        contextual_traces = [t for t in search_traces if any(word in t.lower() for word in ["autopilot", "document", "processing", "workflow", "configure"])]
        
        print(f"\nBug Check:")
        print(f"Generic 'knowledge base' traces: {len(generic_traces)}")
        if generic_traces:
            print("❌ STILL BROKEN: Found generic traces:")
            for trace in generic_traces:
                print(f"  - {trace}")
        else:
            print("✅ FIXED: No generic 'knowledge base' traces found")
        
        print(f"\nContextual traces: {len(contextual_traces)}")
        if contextual_traces:
            print("✅ SUCCESS: Found contextual traces:")
            for trace in contextual_traces:
                print(f"  - {trace}")
        else:
            print("⚠️  No contextual traces captured (may need longer timeout)")
        
        return len(generic_traces) == 0 and len(contextual_traces) > 0
        
    except Exception as e:
        print(f"Error testing search context fix: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_search_context_fix())
    print(f"\nFix Status: {'✅ SUCCESS' if success else '❌ NEEDS REVIEW'}")