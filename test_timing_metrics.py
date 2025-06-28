#!/usr/bin/env python3
"""
Test Timing Metrics

Tests the time measurement system to analyze delays between 
user message and first visual trace appearance.
"""

import asyncio
import time
from datetime import datetime
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

async def test_timing_metrics():
    """Test the timing measurement system with a simulated message"""
    
    print("🔍 Testing Timing Metrics System")
    print("=" * 60)
    
    # Capture timing events
    timing_events = []
    
    async def capture_timing_event(message: str):
        """Capture timing events with precise timestamps"""
        timestamp = time.time()
        timing_events.append((timestamp, message))
        print(f"[{timestamp:.3f}] {message}")
    
    try:
        print("Setting up timing measurement test...")
        
        # Initialize services
        memory = MemoryService()
        tracker = ProgressTracker(update_callback=capture_timing_event)
        orchestrator = OrchestratorAgent(memory, tracker)
        
        # Create test message simulating user input
        test_message = ProcessedMessage(
            text="What are the latest features in UiPath Autopilot?",
            user_id="U_TIMING_TEST",
            user_name="TimingTestUser",
            user_first_name="Timing",
            user_display_name="Timing Test User",
            user_title="Product Manager",
            user_department="Product",
            channel_id="C_TIMING_TEST",
            channel_name="timing-test-channel",
            message_ts=str(time.time()),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        print(f"\n📝 Test Query: '{test_message.text}'")
        print("=" * 60)
        
        # SIMULATE USER MESSAGE TIMING
        simulated_user_send_time = time.time()
        print(f"⏱️  SIMULATED USER SEND: {simulated_user_send_time:.3f}")
        
        # Start processing with timing measurements
        start_time = time.time()
        print(f"⏱️  PROCESSING START: {start_time:.3f}")
        
        # Process query (this will trigger the timing measurements)
        response = await orchestrator.process_query(test_message)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print(f"⏱️  PROCESSING END: {end_time:.3f}")
        print(f"⏱️  TOTAL PROCESSING TIME: {total_duration:.3f}s")
        
        # Analyze timing events
        print(f"\n📊 TIMING ANALYSIS")
        print("=" * 60)
        
        if timing_events:
            first_event_time = timing_events[0][0]
            first_trace_delay = first_event_time - start_time
            
            print(f"Time to First Progress Trace: {first_trace_delay:.3f}s")
            print(f"Total Progress Events: {len(timing_events)}")
            
            print(f"\n📋 Progress Event Timeline:")
            base_time = start_time
            for i, (timestamp, message) in enumerate(timing_events, 1):
                relative_time = timestamp - base_time
                print(f"  +{relative_time:.3f}s: {message}")
        else:
            print("No timing events captured")
        
        # Analyze response
        if response:
            response_text = response.get("text", "")
            print(f"\n✅ Response Generated: {len(response_text)} characters")
        else:
            print(f"\n❌ No response generated")
        
        # Performance Assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT")
        print("=" * 60)
        
        if timing_events and len(timing_events) > 0:
            first_trace_time = first_trace_delay
            
            if first_trace_time < 0.1:
                assessment = "EXCELLENT (< 0.1s)"
            elif first_trace_time < 0.5:
                assessment = "GOOD (< 0.5s)"
            elif first_trace_time < 1.0:
                assessment = "ACCEPTABLE (< 1.0s)"
            elif first_trace_time < 2.0:
                assessment = "SLOW (< 2.0s)"
            else:
                assessment = "VERY SLOW (> 2.0s)"
            
            print(f"First Trace Response Time: {assessment}")
            print(f"Total Processing Time: {total_duration:.3f}s")
            
            # Identify bottlenecks
            print(f"\n🔍 BOTTLENECK ANALYSIS:")
            if first_trace_time > 0.5:
                print(f"  - First trace delay is high ({first_trace_time:.3f}s)")
                print(f"  - Consider optimizing progress tracker initialization")
            
            if total_duration > 5.0:
                print(f"  - Total processing time is high ({total_duration:.3f}s)")
                print(f"  - Consider optimizing agent processing pipeline")
            
            if len(timing_events) < 3:
                print(f"  - Low number of progress events ({len(timing_events)})")
                print(f"  - Consider adding more progress indicators")
        
    except Exception as e:
        print(f"❌ Error in timing test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

async def main():
    """Run the timing metrics test"""
    await test_timing_metrics()

if __name__ == "__main__":
    asyncio.run(main())