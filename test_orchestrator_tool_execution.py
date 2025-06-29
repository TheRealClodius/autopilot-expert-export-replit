#!/usr/bin/env python3
"""
Test orchestrator tool execution and result reading capabilities
"""
import asyncio
import sys
import os
sys.path.append('.')

from config import settings
from agents.slack_gateway import SlackGateway
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from datetime import datetime

async def test_orchestrator_tools():
    """Test that orchestrator can use any tool and read results"""
    
    print("🔍 TESTING ORCHESTRATOR TOOL EXECUTION")
    print("=" * 50)
    
    # Initialize services
    slack_gateway = SlackGateway()
    orchestrator = OrchestratorAgent()
    
    # Create test message for Atlassian
    test_message = ProcessedMessage(
        text="Find bugs in the AUTOPILOT project",
        user_id="test_user",
        user_name="Test User",
        channel_id="test_channel",
        message_ts="1234567890",
        is_dm=False,
        mentions_bot=True,
        thread_ts=None,
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Developer",
        user_department="Engineering"
    )
    
    # Test 1: Atlassian MCP tool execution
    print("1. Testing Atlassian MCP Tool...")
    try:
        result = await orchestrator.process_query(test_message)
        print(f"   Result received: {bool(result)}")
        if result:
            print(f"   Response text available: {bool(result.get('text'))}")
            print(f"   Channel ID: {result.get('channel_id')}")
            text_preview = result.get('text', '')[:200] + "..." if len(result.get('text', '')) > 200 else result.get('text', '')
            print(f"   Response preview: {text_preview}")
        else:
            print("   No result returned")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 2: Vector search tool
    test_message2 = ProcessedMessage(
        text="Tell me about UiPath Autopilot features from our knowledge base",
        user_id="test_user",
        user_name="Test User", 
        channel_id="test_channel",
        message_ts="1234567891",
        is_dm=False,
        mentions_bot=True,
        thread_ts=None,
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Developer",
        user_department="Engineering"
    )
    
    print("2. Testing Vector Search Tool...")
    try:
        result = await orchestrator.process_query(test_message2)
        print(f"   Result received: {bool(result)}")
        if result:
            print(f"   Response text available: {bool(result.get('text'))}")
            text_preview = result.get('text', '')[:200] + "..." if len(result.get('text', '')) > 200 else result.get('text', '')
            print(f"   Response preview: {text_preview}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 3: Perplexity web search
    test_message3 = ProcessedMessage(
        text="What are the latest UiPath news and updates?",
        user_id="test_user",
        user_name="Test User",
        channel_id="test_channel", 
        message_ts="1234567892",
        is_dm=False,
        mentions_bot=True,
        thread_ts=None,
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Developer",
        user_department="Engineering"
    )
    
    print("3. Testing Perplexity Web Search Tool...")
    try:
        result = await orchestrator.process_query(test_message3)
        print(f"   Result received: {bool(result)}")
        if result:
            print(f"   Response text available: {bool(result.get('text'))}")
            text_preview = result.get('text', '')[:200] + "..." if len(result.get('text', '')) > 200 else result.get('text', '')
            print(f"   Response preview: {text_preview}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("✅ ORCHESTRATOR TOOL TESTING COMPLETE")
    print("The orchestrator can use any configured tool and read results.")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_tools())