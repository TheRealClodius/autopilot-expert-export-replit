#!/usr/bin/env python3
"""
Test User Mention Fix - Verify that @user mentions are preserved
"""

import asyncio
from agents.slack_gateway import SlackGateway

async def test_mention_processing():
    """Test the new mention processing functionality"""
    print("=== TESTING USER MENTION PROCESSING ===")
    
    gateway = SlackGateway()
    
    # Test cases with Slack mention format
    test_messages = [
        "Hey <@U123456789> how are you?",
        "Can you ask <@U987654321> about the project?",
        "<@U555555555> mentioned the design requirements",
        "I was talking to <@U111111111> yesterday about features",
        "Both <@U222222222> and <@U333333333> are working on this"
    ]
    
    for i, raw_message in enumerate(test_messages):
        print(f"\n--- Test {i+1} ---")
        print(f"Raw Slack format: {raw_message}")
        
        try:
            cleaned_message = await gateway._clean_message_text(raw_message)
            print(f"Cleaned message: {cleaned_message}")
            
            # Check if mentions were preserved
            if "@" in cleaned_message:
                print("✅ User mentions preserved")
            else:
                print("❌ User mentions lost")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_mention_processing())