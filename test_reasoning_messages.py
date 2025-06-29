#!/usr/bin/env python3
"""
Quick test script to verify reasoning message formatting
"""
import asyncio
import sys
import os
sys.path.append('.')

from services.progress_tracker import ProgressTracker, emit_considering, emit_reasoning, emit_analyzing

async def test_new_reasoning_messages():
    """Test the new reasoning-specific progress messages"""
    
    captured_messages = []
    
    async def mock_slack_updater(message: str):
        """Mock Slack updater to capture messages"""
        captured_messages.append(message)
        print(f"SLACK MESSAGE: {message}")
    
    # Create progress tracker
    tracker = ProgressTracker(update_callback=mock_slack_updater)
    
    print("Testing new reasoning-specific progress messages:")
    print("=" * 60)
    
    # Test the messages we're now using in orchestrator
    await emit_considering(tracker, "requirements", "how to best approach: test query...")
    await emit_reasoning(tracker, "evaluating", "different approaches to solve this effectively")
    await emit_analyzing(tracker, "complexity", "this request")
    
    print("\nCaptured messages:")
    for i, msg in enumerate(captured_messages, 1):
        print(f"{i}. {msg}")
    
    print("\nChecking if messages use 'I am' format:")
    for msg in captured_messages:
        uses_i_am = "I am" in msg
        print(f"  '{msg[:50]}...' -> {'✅ Uses I am format' if uses_i_am else '❌ Generic format'}")
    
    return captured_messages

if __name__ == "__main__":
    messages = asyncio.run(test_new_reasoning_messages())
    
    if all("I am" in msg for msg in messages):
        print("\n✅ SUCCESS: All messages use the new 'I am considering...' format!")
    else:
        print("\n❌ ISSUE: Some messages still use generic format")