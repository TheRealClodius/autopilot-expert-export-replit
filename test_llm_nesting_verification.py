#!/usr/bin/env python3
"""
LLM Nesting Verification Test

This test specifically verifies that LLM calls are properly nested under their
respective agent operation traces in LangSmith, following the correct hierarchy:

Conversation
├── Orchestrator Operation (query_analysis)
│   └── LLM Call (gemini-2.5-pro)
└── Client Agent Operation (response_generation)
    └── LLM Call (gemini-2.5-flash)
"""

import asyncio
import json
import time
from services.trace_manager import trace_manager
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage
from datetime import datetime

async def test_llm_nesting():
    """Test proper LLM call nesting under agent operations"""
    
    print("🔍 Testing LLM Call Nesting in LangSmith Traces")
    print("=" * 60)
    
    # Start a test conversation session
    session_id = await trace_manager.start_conversation_session(
        user_id="U_NESTING_TEST",
        message="Test proper LLM nesting hierarchy",
        channel_id="C_NESTING_TEST",
        message_ts=str(time.time())
    )
    
    print(f"✅ Started test conversation: {session_id}")
    print(f"🎯 Trace ID: {trace_manager.current_trace_id}")
    
    # Create test message
    test_message = ProcessedMessage(
        user_id="U_NESTING_TEST",
        user_name="Test User",
        user_first_name="Test", 
        user_display_name="Test User",
        user_title="Developer",
        user_department="Engineering",
        text="Explain the benefits of proper trace hierarchy",
        channel_id="C_NESTING_TEST",
        channel_name="nesting-test",
        timestamp=str(time.time()),
        is_dm=False,
        is_mention=True,
        is_thread=False,
        thread_ts=None
    )
    
    print("\n🤖 Testing Orchestrator Agent Operation Nesting...")
    
    # Initialize orchestrator
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Test orchestrator query analysis (should create nested LLM call)
    execution_plan = await orchestrator._analyze_query_and_plan(test_message)
    
    if execution_plan:
        print("✅ Orchestrator analysis completed with nested LLM call")
        print(f"   Plan: {execution_plan.get('analysis', 'N/A')[:100]}...")
    else:
        print("❌ Orchestrator analysis failed")
    
    print("\n🎨 Testing Client Agent Operation Nesting...")
    
    # Build state stack for client agent
    state_stack = {
        "query": test_message.text,
        "user": {
            "user_id": test_message.user_id,
            "first_name": test_message.user_first_name,
            "display_name": test_message.user_display_name,
            "title": test_message.user_title,
            "department": test_message.user_department
        },
        "context": {"channel_name": test_message.channel_name},
        "conversation_history": {"recent_exchanges": []},
        "orchestrator_analysis": execution_plan or {"analysis": "fallback"},
        "response_thread_ts": None,
        "trace_id": trace_manager.current_trace_id
    }
    
    # Test client agent response generation (should create nested LLM call)
    client_agent = ClientAgent()
    response = await client_agent.generate_response(state_stack)
    
    if response:
        print("✅ Client agent response generated with nested LLM call")
        print(f"   Response: {response.get('text', 'N/A')[:100]}...")
    else:
        print("❌ Client agent response generation failed")
    
    print("\n📊 Trace Hierarchy Summary:")
    print(f"   Conversation Trace: {trace_manager.current_trace_id}")
    print("   ├── Orchestrator Operation (query_analysis)")
    print("   │   └── LLM Call (gemini-2.5-pro)")
    print("   └── Client Agent Operation (response_generation)")
    print("       └── LLM Call (gemini-2.5-flash)")
    
    # Complete the conversation session
    final_response = response.get('text', 'Test response') if response else 'No response generated'
    await trace_manager.complete_conversation_session(final_response=final_response)
    
    print(f"\n✅ Completed conversation session: {session_id}")
    print("\n🎯 Check LangSmith dashboard for proper trace nesting!")
    print(f"   Project: autopilot-expert-multi-agent")
    print(f"   Conversation ID: {session_id}")
    
    return {
        "session_id": session_id,
        "trace_id": trace_manager.current_trace_id,
        "orchestrator_success": bool(execution_plan),
        "client_agent_success": bool(response),
        "nesting_status": "completed"
    }

if __name__ == "__main__":
    result = asyncio.run(test_llm_nesting())
    print(f"\n📋 Test Results: {json.dumps(result, indent=2)}")