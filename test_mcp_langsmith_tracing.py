#!/usr/bin/env python3
"""
Full End-to-End MCP LangSmith Tracing Test

Simulates complete Slack message processing flow with MCP tool execution
and comprehensive LangSmith tracing integration.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

# Import all necessary components
from services.memory_service import MemoryService
from services.trace_manager import TraceManager
from agents.slack_gateway import SlackGateway
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from models.schemas import ProcessedMessage
from tools.atlassian_tool import AtlassianTool

async def test_full_mcp_langsmith_flow():
    """Test complete end-to-end MCP tool execution with LangSmith tracing"""
    print("🚀 FULL END-TO-END MCP LANGSMITH TRACING TEST")
    print("=" * 60)
    
    # Initialize all services
    print("📋 Initializing Services...")
    memory_service = MemoryService()
    trace_manager = TraceManager()
    
    print(f"✅ Memory Service: {type(memory_service).__name__}")
    print(f"✅ Trace Manager: Enabled={trace_manager.is_enabled()}")
    
    # Initialize agents with trace manager
    print("\n🤖 Initializing AI Agents...")
    orchestrator = OrchestratorAgent(
        memory_service=memory_service, 
        trace_manager=trace_manager
    )
    client_agent = ClientAgent()
    
    print(f"✅ Orchestrator Agent: {type(orchestrator).__name__}")
    print(f"✅ Client Agent: {type(client_agent).__name__}")
    print(f"✅ Atlassian Tool: {type(orchestrator.atlassian_tool).__name__}")
    print(f"   - MCP Server URL: {orchestrator.atlassian_tool.mcp_server_url}")
    print(f"   - Trace Manager: {orchestrator.atlassian_tool.trace_manager is not None}")
    
    # Create a realistic Slack message for Autopilot query
    print("\n💬 Creating Test Slack Message...")
    test_message = ProcessedMessage(
        user_id="U123TEST456",
        channel_id="C987AUTOPILOT",
        text="Can you find documentation about Autopilot for Everyone and show me what it's trying to achieve?",
        timestamp="1735571400.123456",
        thread_ts=None,
        is_dm=False,
        is_mention=True,
        user_first_name="Sarah",
        user_display_name="Sarah Chen",
        user_title="Product Manager",
        user_department="Product"
    )
    
    print(f"✅ Test Message Created")
    print(f"   User: {test_message.user_display_name} ({test_message.user_title})")
    print(f"   Query: {test_message.text[:60]}...")
    
    # Start conversation trace
    print("\n📊 Starting LangSmith Conversation Trace...")
    session_id = await trace_manager.start_conversation_session(
        user_id=test_message.user_id,
        message=test_message.text,
        channel_id=test_message.channel_id,
        message_ts=test_message.timestamp
    )
    print(f"✅ Conversation Session: {session_id}")
    
    # Process message through orchestrator
    print("\n🧠 Processing Query through Orchestrator...")
    start_time = time.time()
    
    try:
        # This should trigger MCP tool execution with tracing
        response = await orchestrator.process_query(test_message)
        
        processing_time = time.time() - start_time
        print(f"✅ Orchestrator Processing Complete ({processing_time:.2f}s)")
        
        if response:
            print(f"   Response Type: {type(response)}")
            print(f"   Has Response Text: {'response' in response}")
            
            # Check if MCP tool was executed
            if 'state_stack' in response:
                state_stack = response['state_stack']
                orchestrator_analysis = state_stack.get('orchestrator_analysis', {})
                
                print(f"\n🔍 Orchestrator Analysis Results:")
                print(f"   Intent: {orchestrator_analysis.get('intent', 'Unknown')}")
                print(f"   Tools Used: {orchestrator_analysis.get('tools_used', [])}")
                
                # Check for Atlassian results
                if 'atlassian_results' in orchestrator_analysis:
                    atlassian_results = orchestrator_analysis['atlassian_results']
                    print(f"   Atlassian Success: {atlassian_results.get('success', False)}")
                    
                    if atlassian_results.get('success'):
                        result_data = atlassian_results.get('result', {})
                        if isinstance(result_data, dict) and 'result' in result_data:
                            pages = result_data['result']
                            print(f"   Found {len(pages)} Confluence pages")
                            for i, page in enumerate(pages[:3], 1):
                                title = page.get('title', 'Unknown')
                                space = page.get('space', {}).get('name', 'Unknown')
                                print(f"     {i}. {title} (Space: {space})")
                        else:
                            print(f"   Result Data: {str(result_data)[:100]}...")
                    else:
                        print(f"   Error: {atlassian_results.get('error', 'Unknown error')}")
            
            # Generate client response
            print(f"\n📝 Generating Client Response...")
            client_start = time.time()
            
            client_response = await client_agent.process_query(
                message=test_message,
                state_stack=response.get('state_stack', {})
            )
            
            client_time = time.time() - client_start
            print(f"✅ Client Response Generated ({client_time:.2f}s)")
            
            if client_response and 'response' in client_response:
                response_text = client_response['response']
                print(f"   Response Length: {len(response_text)} characters")
                print(f"   Response Preview: {response_text[:150]}...")
            else:
                print(f"   No response generated: {client_response}")
                
        else:
            print("❌ No response from orchestrator")
            
    except Exception as e:
        print(f"❌ Processing Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Complete conversation trace
    print(f"\n🏁 Completing LangSmith Trace...")
    await trace_manager.complete_conversation_session(
        final_response="End-to-end MCP tracing test completed"
    )
    
    total_time = time.time() - start_time
    print(f"✅ Test Completed ({total_time:.2f}s total)")
    
    # Summary
    print(f"\n📊 LangSmith Tracing Summary:")
    print(f"- Conversation Session: {session_id}")
    print(f"- Check LangSmith dashboard for complete trace hierarchy")
    print(f"- Expected traces:")
    print(f"  └─ Slack Conversation (session)")
    print(f"     ├─ Orchestrator Analysis")
    print(f"     ├─ MCP Atlassian Tool Execution")
    print(f"     │  └─ confluence_search tool call")
    print(f"     └─ Client Response Generation")
    print(f"- Processing time: {total_time:.2f}s")
    print(f"- MCP tool should show authentic UiPath data")

async def main():
    await test_full_mcp_langsmith_flow()

if __name__ == "__main__":
    asyncio.run(main())