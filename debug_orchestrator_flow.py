#!/usr/bin/env python3
"""
Debug Orchestrator Flow - Step by Step Event Tracking
"""

import asyncio
import time
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

async def debug_step_by_step():
    """Debug orchestrator step by step to find where it hangs"""
    
    print("🔍 Debugging Orchestrator Flow Step by Step")
    print("=" * 50)
    
    events = []
    step_times = {}
    
    async def track_event(msg):
        timestamp = time.time()
        events.append((timestamp, msg))
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
    
    try:
        # Step 1: Initialize components
        print("Step 1: Initializing components...")
        start = time.time()
        
        memory = MemoryService()
        tracker = ProgressTracker(update_callback=track_event)
        orchestrator = OrchestratorAgent(memory, tracker)
        
        step_times["initialization"] = time.time() - start
        print(f"✅ Initialization complete ({step_times['initialization']:.2f}s)")
        
        # Step 2: Create test message
        print("\nStep 2: Creating test message...")
        msg = ProcessedMessage(
            channel_id="C_TEST",
            user_id="U_TEST", 
            text="What are the latest AI automation trends for 2025?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Alex",
            user_display_name="Alex Smith",
            user_title="Engineer",
            user_department="AI Research",
            channel_name="ai-trends",
            is_dm=False,
            thread_context=""
        )
        print(f"✅ Test message created: {msg.text}")
        
        # Step 3: Start processing with timeout
        print("\nStep 3: Starting orchestrator processing...")
        processing_start = time.time()
        
        # Add timeout to prevent hanging
        try:
            response = await asyncio.wait_for(
                orchestrator.process_query(msg), 
                timeout=15.0  # 15 second timeout
            )
            step_times["processing"] = time.time() - processing_start
            print(f"✅ Processing complete ({step_times['processing']:.2f}s)")
            
        except asyncio.TimeoutError:
            step_times["processing"] = time.time() - processing_start
            print(f"⏰ Processing timed out after {step_times['processing']:.2f}s")
            response = None
        
        # Step 4: Analyze results
        print(f"\nStep 4: Analyzing results...")
        print(f"Total events captured: {len(events)}")
        print(f"Response generated: {'Yes' if response else 'No'}")
        
        # Show event timeline
        if events:
            print(f"\nEvent Timeline:")
            base_time = events[0][0]
            for timestamp, message in events:
                relative_time = timestamp - base_time
                print(f"  +{relative_time:.2f}s: {message}")
        
        # Check for specific event types
        thinking_events = sum(1 for _, msg in events if "🤔" in msg)
        search_events = sum(1 for _, msg in events if "🔍" in msg)
        web_events = sum(1 for _, msg in events if "real-time" in msg.lower())
        
        print(f"\nEvent Analysis:")
        print(f"  Thinking events: {thinking_events}")
        print(f"  Search events: {search_events}")
        print(f"  Web search events: {web_events}")
        
        # Determine where the hang occurs
        if len(events) == 1 and "Analyzing" in events[0][1]:
            print(f"\n🚨 ISSUE: Hanging during query analysis (Gemini API call)")
        elif len(events) >= 2 and search_events == 0:
            print(f"\n🚨 ISSUE: Analysis completes but no searches triggered")
        elif web_events == 0 and "2025" in msg.text:
            print(f"\n🚨 ISSUE: Future query not routing to Perplexity")
        else:
            print(f"\n✅ Event flow appears normal")
        
        return {
            "events": len(events),
            "response": response is not None,
            "times": step_times
        }
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(debug_step_by_step())