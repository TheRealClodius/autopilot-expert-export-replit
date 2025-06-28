#!/usr/bin/env python3
"""
Complete Orchestrator Event Testing

This test captures EVERY progress event emitted by the orchestrator 
across different query types to verify complete Slack integration.
"""

import asyncio
import time
from datetime import datetime
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

class EventCapture:
    def __init__(self):
        self.events = []
        self.start_time = None
    
    async def capture_event(self, message: str):
        """Capture each progress event with timing"""
        if self.start_time is None:
            self.start_time = time.time()
        
        timestamp = time.time()
        relative_time = timestamp - self.start_time
        formatted_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        event = {
            "sequence": len(self.events) + 1,
            "timestamp": formatted_time,
            "relative_time": relative_time,
            "message": message
        }
        self.events.append(event)
        print(f"[{formatted_time}] Event #{event['sequence']}: {message}")

async def test_query_scenario(query_text: str, scenario_name: str, expected_tools: list):
    """Test a specific query scenario and capture all events"""
    
    print(f"\n{'='*60}")
    print(f"🎯 SCENARIO: {scenario_name}")
    print(f"📝 Query: {query_text}")
    print(f"🔧 Expected Tools: {', '.join(expected_tools)}")
    print(f"{'='*60}")
    
    # Initialize event capture
    capture = EventCapture()
    
    try:
        # Setup orchestrator with event tracking
        memory = MemoryService()
        tracker = ProgressTracker(update_callback=capture.capture_event)
        orchestrator = OrchestratorAgent(memory, tracker)
        
        # Create test message
        message = ProcessedMessage(
            channel_id="C_TEST_EVENTS",
            user_id="U_TEST_EVENTS", 
            text=query_text,
            message_ts=str(int(time.time() * 1000000)),
            thread_ts=None,
            user_name="test_user",
            user_first_name="Jordan",
            user_display_name="Jordan Kim",
            user_title="Product Manager",
            user_department="Strategy",
            channel_name="testing",
            is_dm=False,
            thread_context=""
        )
        
        print(f"\n📱 SLACK EVENT SEQUENCE:")
        print("-" * 60)
        
        # Process query with timeout
        start_time = time.time()
        try:
            response = await asyncio.wait_for(
                orchestrator.process_query(message), 
                timeout=25.0
            )
            processing_time = time.time() - start_time
            success = True
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            print(f"⏰ TIMEOUT after {processing_time:.1f}s")
            response = None
            success = False
        
        print("-" * 60)
        
        # Analyze captured events
        print(f"\n📊 EVENT ANALYSIS:")
        print(f"Total events: {len(capture.events)}")
        print(f"Processing time: {processing_time:.2f}s")
        print(f"Success: {'✅' if success else '❌'}")
        
        # Categorize events
        thinking_events = [e for e in capture.events if "🤔" in e["message"]]
        searching_events = [e for e in capture.events if "🔍" in e["message"]]
        processing_events = [e for e in capture.events if "⚙️" in e["message"]]
        generating_events = [e for e in capture.events if "✨" in e["message"]]
        warning_events = [e for e in capture.events if "⚡" in e["message"]]
        error_events = [e for e in capture.events if "⚠️" in e["message"]]
        
        # Tool-specific events
        vector_events = [e for e in capture.events if "knowledge base" in e["message"].lower()]
        perplexity_events = [e for e in capture.events if "real-time web" in e["message"].lower() or "perplexity" in e["message"].lower()]
        
        print(f"\n🏷️ EVENT CATEGORIES:")
        print(f"  Thinking/Planning: {len(thinking_events)}")
        print(f"  Searching: {len(searching_events)}")
        print(f"  Processing: {len(processing_events)}")
        print(f"  Generating: {len(generating_events)}")
        print(f"  Warnings: {len(warning_events)}")
        print(f"  Errors: {len(error_events)}")
        print(f"  Vector Search: {len(vector_events)}")
        print(f"  Perplexity Search: {len(perplexity_events)}")
        
        # Verify expected tools were used
        print(f"\n🔧 TOOL VERIFICATION:")
        for tool in expected_tools:
            if tool == "vector_search":
                found = len(vector_events) > 0
                print(f"  Vector Search: {'✅' if found else '❌'}")
            elif tool == "perplexity_search":
                found = len(perplexity_events) > 0
                print(f"  Perplexity Search: {'✅' if found else '❌'}")
            elif tool == "none":
                no_searches = len(vector_events) == 0 and len(perplexity_events) == 0
                print(f"  No Tools (Direct Response): {'✅' if no_searches else '❌'}")
        
        # Check event flow completeness
        print(f"\n✅ FLOW COMPLETENESS:")
        flow_checks = {
            "Analysis Started": len(thinking_events) > 0,
            "Planning Completed": len(capture.events) > 1,
            "Tools Executed": len(searching_events) > 0 or "none" in expected_tools,
            "Results Processed": len(processing_events) > 0 or len(capture.events) >= 3,
            "Response Generated": len(generating_events) > 0 or success
        }
        
        for check, passed in flow_checks.items():
            print(f"  {check}: {'✅' if passed else '❌'}")
        
        # Response analysis
        if response and success:
            print(f"\n📝 RESPONSE ANALYSIS:")
            response_text = response.get("text", "")
            print(f"  Length: {len(response_text)} characters")
            print(f"  Preview: {response_text[:100]}...")
        
        return {
            "scenario": scenario_name,
            "query": query_text,
            "events": capture.events,
            "event_count": len(capture.events),
            "processing_time": processing_time,
            "success": success,
            "response": response,
            "categories": {
                "thinking": len(thinking_events),
                "searching": len(searching_events),
                "processing": len(processing_events),
                "generating": len(generating_events),
                "warnings": len(warning_events),
                "errors": len(error_events),
                "vector": len(vector_events),
                "perplexity": len(perplexity_events)
            }
        }
        
    except Exception as e:
        print(f"❌ Error in scenario {scenario_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

async def run_complete_event_test():
    """Run comprehensive test of all orchestrator events"""
    
    print("🚀 COMPLETE ORCHESTRATOR EVENT TESTING")
    print("Testing ALL progress events across different query types")
    print("=" * 80)
    
    # Test scenarios covering different orchestrator behaviors
    scenarios = [
        {
            "query": "Hi there! How are you today?",
            "name": "Simple Greeting",
            "expected_tools": ["none"]
        },
        {
            "query": "What features does UiPath Autopilot have?",
            "name": "Knowledge Base Query",
            "expected_tools": ["vector_search"]
        },
        {
            "query": "What are the latest AI automation trends in 2025?",
            "name": "Current Events Query",
            "expected_tools": ["perplexity_search"]
        },
        {
            "query": "How do I set up UiPath Autopilot and what are the current best practices?",
            "name": "Mixed Query (Knowledge + Current)",
            "expected_tools": ["vector_search", "perplexity_search"]
        }
    ]
    
    results = []
    total_start = time.time()
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎬 RUNNING SCENARIO {i}/{len(scenarios)}")
        result = await test_query_scenario(
            scenario["query"], 
            scenario["name"], 
            scenario["expected_tools"]
        )
        if result:
            results.append(result)
        
        # Brief pause between scenarios
        await asyncio.sleep(1)
    
    total_time = time.time() - total_start
    
    # Overall analysis
    print(f"\n{'='*80}")
    print(f"🏁 COMPLETE TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total scenarios tested: {len(results)}")
    print(f"Total test time: {total_time:.1f}s")
    print(f"Average time per scenario: {total_time/len(results):.1f}s")
    
    # Aggregate statistics
    total_events = sum(r["event_count"] for r in results)
    successful_scenarios = sum(1 for r in results if r["success"])
    
    print(f"\n📊 AGGREGATE STATISTICS:")
    print(f"Total events captured: {total_events}")
    print(f"Successful scenarios: {successful_scenarios}/{len(results)}")
    print(f"Average events per scenario: {total_events/len(results):.1f}")
    
    # Event type breakdown across all scenarios
    print(f"\n🏷️ TOTAL EVENT BREAKDOWN:")
    for event_type in ["thinking", "searching", "processing", "generating", "warnings", "errors"]:
        count = sum(r["categories"][event_type] for r in results)
        print(f"  {event_type.title()}: {count}")
    
    # Tool usage analysis
    vector_scenarios = sum(1 for r in results if r["categories"]["vector"] > 0)
    perplexity_scenarios = sum(1 for r in results if r["categories"]["perplexity"] > 0)
    
    print(f"\n🔧 TOOL USAGE ANALYSIS:")
    print(f"Scenarios using Vector Search: {vector_scenarios}/{len(results)}")
    print(f"Scenarios using Perplexity Search: {perplexity_scenarios}/{len(results)}")
    
    # Final assessment
    all_successful = successful_scenarios == len(results)
    good_event_coverage = total_events >= len(results) * 3  # At least 3 events per scenario
    
    print(f"\n🎯 ORCHESTRATOR EVENT EMISSION ASSESSMENT:")
    print(f"All scenarios successful: {'✅' if all_successful else '❌'}")
    print(f"Good event coverage: {'✅' if good_event_coverage else '❌'}")
    print(f"Vector search working: {'✅' if vector_scenarios > 0 else '❌'}")
    print(f"Perplexity search working: {'✅' if perplexity_scenarios > 0 else '❌'}")
    
    overall_grade = "EXCELLENT" if all_successful and good_event_coverage else "GOOD" if successful_scenarios >= len(results) * 0.8 else "NEEDS IMPROVEMENT"
    print(f"\nOverall Grade: {overall_grade}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_complete_event_test())