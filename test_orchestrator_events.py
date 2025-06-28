#!/usr/bin/env python3
"""
Test Complete Orchestrator Event Emission

This test captures every single progress event emitted by the orchestrator
during a Perplexity search to verify complete Slack integration.
"""

import asyncio
import time
from datetime import datetime
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

async def test_complete_orchestrator_events():
    """Test and capture every orchestrator progress event"""
    
    print("📊 Testing Complete Orchestrator Event Emission")
    print("="*60)
    
    # Capture ALL events with timestamps
    all_events = []
    event_count = 0
    
    async def capture_all_events(message: str):
        """Capture every single progress event"""
        nonlocal event_count
        event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        event_data = {
            "sequence": event_count,
            "timestamp": timestamp,
            "message": message,
            "relative_time": time.time()
        }
        all_events.append(event_data)
        print(f"[{timestamp}] Event #{event_count}: {message}")
    
    try:
        # Initialize with complete progress tracking
        memory_service = MemoryService()
        progress_tracker = ProgressTracker(update_callback=capture_all_events)
        orchestrator = OrchestratorAgent(memory_service, progress_tracker)
        
        # Create message that will trigger Perplexity search
        test_message = ProcessedMessage(
            channel_id="C_SLACK_TEST",
            user_id="U_SLACK_TEST", 
            text="What are the latest AI developments in 2025?",  # Forces Perplexity
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Jordan",
            user_display_name="Jordan Kim",
            user_title="Head of AI",
            user_department="Research",
            channel_name="ai-research",
            is_dm=False,
            thread_context=""
        )
        
        print(f"🎯 Test Query: {test_message.text}")
        print(f"📍 Expected: Perplexity search with multiple progress events")
        print()
        print("📱 SLACK EVENT SEQUENCE:")
        print("-" * 60)
        
        # Run complete orchestrator process
        start_time = time.time()
        response = await orchestrator.process_query(test_message)
        total_time = time.time() - start_time
        
        print("-" * 60)
        print()
        
        # Analyze captured events
        print("📊 EVENT ANALYSIS:")
        print(f"Total events captured: {len(all_events)}")
        print(f"Total processing time: {total_time:.2f}s")
        print(f"Event frequency: {len(all_events) / total_time:.1f} events/second")
        print()
        
        # Categorize events by type
        thinking_events = [e for e in all_events if "🤔" in e["message"]]
        searching_events = [e for e in all_events if "🔍" in e["message"]]
        processing_events = [e for e in all_events if "⚙️" in e["message"]]
        generating_events = [e for e in all_events if "✨" in e["message"]]
        warning_events = [e for e in all_events if "⚡" in e["message"]]
        error_events = [e for e in all_events if "⚠️" in e["message"]]
        
        print("📋 EVENT BREAKDOWN:")
        print(f"  Thinking/Planning: {len(thinking_events)}")
        print(f"  Searching: {len(searching_events)}")
        print(f"  Processing: {len(processing_events)}")
        print(f"  Generating: {len(generating_events)}")
        print(f"  Warnings: {len(warning_events)}")
        print(f"  Errors: {len(error_events)}")
        print()
        
        # Check for Perplexity-specific events
        perplexity_events = [e for e in all_events if "real-time web" in e["message"].lower()]
        web_events = [e for e in all_events if any(word in e["message"].lower() for word in ["web", "perplexity", "real-time"])]
        
        print("🌐 PERPLEXITY-SPECIFIC EVENTS:")
        print(f"  Real-time web search events: {len(perplexity_events)}")
        print(f"  Web-related events: {len(web_events)}")
        
        for event in perplexity_events:
            print(f"    #{event['sequence']}: {event['message']}")
        print()
        
        # Check event timing and gaps
        if len(all_events) > 1:
            print("⏱️ EVENT TIMING:")
            first_time = all_events[0]["relative_time"]
            for i, event in enumerate(all_events):
                relative_time = event["relative_time"] - first_time
                gap = event["relative_time"] - all_events[i-1]["relative_time"] if i > 0 else 0
                print(f"  #{event['sequence']}: +{relative_time:.2f}s (gap: {gap:.2f}s)")
        print()
        
        # Verify response quality
        print("✅ RESPONSE ANALYSIS:")
        if response:
            response_text = response.get("text", "")
            print(f"  Response generated: ✅")
            print(f"  Response length: {len(response_text)} characters")
            
            # Check if response contains web-sourced information
            current_indicators = ["2025", "latest", "recent", "current", "new"]
            has_current_info = any(word in response_text.lower() for word in current_indicators)
            print(f"  Contains current information: {'✅' if has_current_info else '❌'}")
            
            print(f"  Response preview: {response_text[:150]}...")
        else:
            print(f"  Response generated: ❌")
        print()
        
        # Final assessment
        print("🎯 SLACK INTEGRATION ASSESSMENT:")
        
        checks = {
            "Events captured": len(all_events) > 0,
            "Perplexity events present": len(perplexity_events) > 0,
            "Complete flow": len(thinking_events) > 0 and len(generating_events) > 0,
            "Web search indicated": len(web_events) > 0,
            "Response generated": response is not None,
            "No missing events": len(all_events) >= 4  # Minimum expected
        }
        
        for check, passed in checks.items():
            print(f"  {check}: {'✅' if passed else '❌'}")
        
        overall_score = sum(checks.values()) / len(checks) * 100
        print(f"\nOverall Integration Score: {overall_score:.0f}%")
        
        # Show complete message sequence as it appears in Slack
        print(f"\n📱 COMPLETE SLACK MESSAGE SEQUENCE:")
        print("=" * 60)
        for event in all_events:
            print(f"{event['sequence']:2d}. [{event['timestamp']}] {event['message']}")
        
        status = "FULLY OPERATIONAL" if overall_score >= 85 else "NEEDS REVIEW"
        print(f"\n🚀 ORCHESTRATOR EVENT EMISSION: {status}")
        
        return {
            "total_events": len(all_events),
            "perplexity_events": len(perplexity_events),
            "processing_time": total_time,
            "overall_score": overall_score,
            "events": all_events
        }
        
    except Exception as e:
        print(f"❌ Error during event capture test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_complete_orchestrator_events())