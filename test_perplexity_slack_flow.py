#!/usr/bin/env python3
"""
Test Complete Perplexity Slack Flow - End-to-End Progress Verification

This tests the complete flow from Slack query through Perplexity search 
to final response, focusing on what users actually see in Slack.
"""

import asyncio
import time
from datetime import datetime
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

async def test_complete_perplexity_slack_flow():
    """Test the complete Slack flow with Perplexity integration"""
    
    print("📱 Testing Complete Perplexity Slack Flow")
    print("="*55)
    
    # Capture Slack messages as they would appear to user
    slack_messages = []
    
    async def mock_slack_updater(message: str):
        """Simulate Slack progress message updates"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        slack_messages.append(f"[{timestamp}] {message}")
        print(f"📱 Slack: {message}")
    
    try:
        # Initialize components with progress tracking
        memory_service = MemoryService()
        progress_tracker = ProgressTracker(update_callback=mock_slack_updater)
        orchestrator = OrchestratorAgent(memory_service, progress_tracker)
        
        # Create test message for current trends (should trigger Perplexity)
        test_message = ProcessedMessage(
            channel_id="C_TEST",
            user_id="U_TEST", 
            text="What are the latest AI automation trends for 2025?",
            message_ts="1640995200.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Sarah",
            user_display_name="Sarah Chen",
            user_title="Product Manager", 
            user_department="Product",
            channel_name="ai-discussion",
            is_dm=False,
            thread_context=""
        )
        
        print(f"👤 User Query: {test_message.text}")
        print(f"📍 Channel: #{test_message.channel_name}")
        print()
        
        # Run complete orchestrator flow with timing
        start_time = time.time()
        
        print("🚀 Starting orchestrator process...")
        response = await orchestrator.process_query(test_message)
        
        total_time = time.time() - start_time
        
        print(f"\n⏱️ TIMING ANALYSIS:")
        print(f"Total processing time: {total_time:.2f}s")
        print(f"Progress messages sent: {len(slack_messages)}")
        print(f"Message frequency: {len(slack_messages) / total_time:.1f} per second")
        
        print(f"\n📊 SLACK MESSAGE ANALYSIS:")
        
        # Categorize messages
        thinking_msgs = [msg for msg in slack_messages if "🤔" in msg]
        searching_msgs = [msg for msg in slack_messages if "🔍" in msg]
        processing_msgs = [msg for msg in slack_messages if "⚙️" in msg or "⚡" in msg]
        generating_msgs = [msg for msg in slack_messages if "✨" in msg]
        
        print(f"Thinking/Planning: {len(thinking_msgs)}")
        print(f"Searching: {len(searching_msgs)}")
        print(f"Processing: {len(processing_msgs)}")
        print(f"Generating: {len(generating_msgs)}")
        
        # Check for Perplexity-specific indicators
        web_search_msgs = [msg for msg in slack_messages if "real-time web" in msg.lower()]
        perplexity_indicators = [msg for msg in slack_messages if any(keyword in msg.lower() for keyword in ["web", "real-time", "current"])]
        
        print(f"Web search indicators: {len(web_search_msgs)}")
        print(f"Perplexity-related: {len(perplexity_indicators)}")
        
        print(f"\n📱 COMPLETE SLACK MESSAGE SEQUENCE:")
        for i, msg in enumerate(slack_messages, 1):
            print(f"  {i}. {msg}")
        
        # Analyze response quality
        if response:
            response_text = response.get("text", "")
            print(f"\n✅ FINAL RESPONSE ANALYSIS:")
            print(f"Response generated: {'✅' if response_text else '❌'}")
            print(f"Response length: {len(response_text)} characters")
            print(f"Contains current info: {'✅' if any(keyword in response_text.lower() for keyword in ['2025', 'current', 'latest', 'trend']) else '❌'}")
            print(f"Response preview: {response_text[:150]}...")
        else:
            print(f"\n❌ NO RESPONSE GENERATED")
        
        # User experience assessment
        print(f"\n🎯 USER EXPERIENCE ASSESSMENT:")
        
        ux_checks = {
            "Clear progress indication": len(slack_messages) >= 3,
            "Web search transparency": len(web_search_msgs) > 0,
            "Logical message flow": len(thinking_msgs) > 0 and len(searching_msgs) > 0,
            "Timely updates": total_time < 15.0,  # Reasonable for web search
            "Final response": response is not None,
            "Current information": response and any(keyword in response.get("text", "").lower() for keyword in ['2025', 'current', 'latest'])
        }
        
        for check, passed in ux_checks.items():
            print(f"  {check}: {'✅' if passed else '❌'}")
        
        overall_score = sum(ux_checks.values()) / len(ux_checks) * 100
        print(f"\nOverall UX Score: {overall_score:.0f}%")
        
        # Final status
        perplexity_working = len(web_search_msgs) > 0 and response is not None
        print(f"\n🚀 PERPLEXITY SLACK INTEGRATION: {'FULLY OPERATIONAL' if perplexity_working else 'NEEDS REVIEW'}")
        
        return {
            "total_time": total_time,
            "message_count": len(slack_messages),
            "web_search_indicators": len(web_search_msgs),
            "response_generated": response is not None,
            "ux_score": overall_score,
            "slack_messages": slack_messages
        }
        
    except Exception as e:
        print(f"❌ Error during complete flow test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_complete_perplexity_slack_flow())