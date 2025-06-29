#!/usr/bin/env python3
"""
Test script to search for UX Audit Evaluation Template in Confluence
and find its owner (should be Mausam Jain)
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent
from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
from services.trace_manager import TraceManager
from config import Settings

async def test_ux_audit_template_search():
    """Test searching for UX Audit Evaluation Template owner"""
    
    print("🔍 Testing UX Audit Evaluation Template search...")
    
    # Initialize services
    settings = Settings()
    memory_service = MemoryService()
    trace_manager = TraceManager()
    
    # Initialize agents
    orchestrator = OrchestratorAgent(memory_service, trace_manager)
    client_agent = ClientAgent(memory_service, trace_manager)
    
    # Create test message
    test_message = ProcessedMessage(
        channel_id="C_TEST",
        user_id="U_TEST",
        message_id="msg_test",
        thread_ts=None,
        message_ts="1234567890.123456",
        text="Who owns the UX Audit Evaluation Template document in Confluence?",
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Tester",
        user_department="Testing"
    )
    
    print(f"📝 Query: {test_message.text}")
    
    try:
        # Step 1: Orchestrator analysis
        print("\n🧠 Running orchestrator analysis...")
        
        def mock_progress_callback(message: str):
            print(f"   💭 {message}")
        
        orchestrator_result = await orchestrator.analyze_query(
            test_message, 
            progress_callback=mock_progress_callback
        )
        
        if orchestrator_result:
            print(f"✅ Orchestrator analysis complete")
            print(f"   Intent: {orchestrator_result.get('intent', 'Not specified')}")
            print(f"   Tools needed: {orchestrator_result.get('tools_needed', [])}")
            
            # Check for Atlassian results
            atlassian_results = orchestrator_result.get('atlassian_results', [])
            if atlassian_results:
                print(f"🏢 Atlassian search results found: {len(atlassian_results)} items")
                for i, result in enumerate(atlassian_results, 1):
                    print(f"   Result {i}:")
                    print(f"      Title: {result.get('title', 'N/A')}")
                    print(f"      Type: {result.get('type', 'N/A')}")
                    print(f"      Author: {result.get('author', 'N/A')}")
                    print(f"      Creator: {result.get('creator', 'N/A')}")
                    print(f"      Space: {result.get('space', 'N/A')}")
                    if 'url' in result:
                        print(f"      URL: {result['url']}")
            else:
                print("❌ No Atlassian results found")
            
            # Step 2: Client agent response
            print("\n🎯 Generating client response...")
            
            client_response = await client_agent.generate_response(
                orchestrator_result,
                progress_callback=mock_progress_callback
            )
            
            if client_response:
                print("✅ Client response generated:")
                print(f"   Response: {client_response.get('response', 'No response')}")
                
                # Check if Mausam Jain is mentioned
                response_text = client_response.get('response', '').lower()
                if 'mausam jain' in response_text or 'mausam' in response_text:
                    print("🎉 SUCCESS: Found Mausam Jain as owner!")
                else:
                    print("⚠️  Owner information may not match expected result")
            else:
                print("❌ No client response generated")
        else:
            print("❌ Orchestrator analysis failed")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ux_audit_template_search())