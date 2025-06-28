#!/usr/bin/env python3
"""
Test Perplexity Progress Tracking - Verify Slack progress events

This script tests the progress tracking for Perplexity searches to ensure
users see meaningful real-time updates during web searches.
"""

import asyncio
import time
from datetime import datetime
from services.progress_tracker import ProgressTracker, emit_thinking, emit_searching, emit_processing, emit_generating, emit_error, emit_warning

async def test_perplexity_progress_flow():
    """Test the complete progress flow for Perplexity integration"""
    
    print("🔍 Testing Perplexity Progress Tracking for Slack")
    print("="*60)
    
    # Capture progress messages
    progress_messages = []
    
    async def mock_slack_updater(message: str):
        """Mock Slack updater that captures progress messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        progress_messages.append(f"[{timestamp}] {message}")
        print(f"📱 Slack Message: {message}")
    
    # Initialize progress tracker
    progress_tracker = ProgressTracker(update_callback=mock_slack_updater)
    
    print("Simulating orchestrator process with Perplexity search...\n")
    
    # Step 1: Initial thinking
    await emit_thinking(progress_tracker, "analyzing", "your query for current information")
    await asyncio.sleep(0.5)
    
    # Step 2: Planning phase
    await emit_thinking(progress_tracker, "planning", "real-time web search strategy")
    await asyncio.sleep(0.3)
    
    # Step 3: Perplexity search events (exactly as in orchestrator)
    query = "latest AI automation trends 2025"
    search_context = f"real-time web search for '{query[:30]}...'" if len(query) > 30 else f"real-time web search for '{query}'"
    await emit_searching(progress_tracker, "perplexity_search", search_context)
    await asyncio.sleep(2.5)  # Simulate actual Perplexity API time
    
    # Step 4: Second search
    query2 = "AI RPA market developments"  
    search_context2 = f"real-time web search for '{query2}'"
    await emit_searching(progress_tracker, "perplexity_search", search_context2)
    await asyncio.sleep(2.2)  # Simulate second API call
    
    # Step 5: Processing results
    await emit_processing(progress_tracker, "analyzing_results", "web search findings")
    await asyncio.sleep(0.4)
    
    # Step 6: Response generation
    await emit_generating(progress_tracker, "response_generation", "comprehensive answer with web insights")
    await asyncio.sleep(1.0)
    
    print(f"\n📊 PROGRESS TRACKING ANALYSIS")
    print(f"Total progress messages: {len(progress_messages)}")
    print(f"Duration: ~{6.9}s simulated")
    print()
    
    # Analyze message quality
    print("📋 Message Content Analysis:")
    
    # Check for web search indicators
    web_search_messages = [msg for msg in progress_messages if "web search" in msg.lower()]
    print(f"Web search messages: {len(web_search_messages)}")
    
    # Check for perplexity-specific messages
    perplexity_messages = [msg for msg in progress_messages if "perplexity" in msg.lower()]
    print(f"Perplexity-specific messages: {len(perplexity_messages)}")
    
    # Check for emojis and natural language
    emoji_messages = [msg for msg in progress_messages if any(emoji in msg for emoji in ["🤔", "🔍", "⚡", "✨"])]
    print(f"Messages with emojis: {len(emoji_messages)}")
    
    # Check message progression
    thinking_msgs = [msg for msg in progress_messages if "🤔" in msg]
    searching_msgs = [msg for msg in progress_messages if "🔍" in msg] 
    processing_msgs = [msg for msg in progress_messages if "⚡" in msg]
    generating_msgs = [msg for msg in progress_messages if "✨" in msg]
    
    print(f"Thinking messages: {len(thinking_msgs)}")
    print(f"Searching messages: {len(searching_msgs)}")
    print(f"Processing messages: {len(processing_msgs)}")
    print(f"Generating messages: {len(generating_msgs)}")
    
    print(f"\n🎯 USER EXPERIENCE ANALYSIS:")
    print(f"Clear web search indication: {'✅' if len(web_search_messages) >= 2 else '❌'}")
    print(f"Real-time feedback: {'✅' if len(progress_messages) >= 6 else '❌'}")
    print(f"Natural language: {'✅' if len(emoji_messages) >= 4 else '❌'}")
    print(f"Logical progression: {'✅' if all([thinking_msgs, searching_msgs, generating_msgs]) else '❌'}")
    
    # Show example messages
    print(f"\n📱 EXAMPLE SLACK MESSAGES:")
    for i, msg in enumerate(progress_messages, 1):
        print(f"  {i}. {msg}")
    
    print(f"\n🚀 PERPLEXITY PROGRESS TRACKING: {'FULLY OPERATIONAL' if len(web_search_messages) >= 2 else 'NEEDS REVIEW'}")

if __name__ == "__main__":
    asyncio.run(test_perplexity_progress_flow())