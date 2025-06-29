#!/usr/bin/env python3

"""
Test Production MCP Flow
Test the exact flow used in production to identify the disconnect
"""

import asyncio
import sys
sys.path.append('.')

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage
from datetime import datetime

async def test_production_mcp_flow():
    """Test the exact production flow that's failing"""
    
    print("🔧 TESTING PRODUCTION MCP FLOW")
    print("=" * 50)
    
    try:
        # Initialize exactly like production
        print("1️⃣ Initializing services like production...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Verify Atlassian tool is available
        if not orchestrator.atlassian_tool.available:
            print("❌ Atlassian tool not available")
            return False
        
        print("✅ Orchestrator initialized with available Atlassian tool")
        
        # Create exact message like production
        test_message = ProcessedMessage(
            text="Can you make me understand what autopilot for everyone is trying to achieve for 24.10?",
            user_id="U_TEST_USER",
            user_name="TestUser", 
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Software Engineer",
            user_department="Engineering",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts=str(int(datetime.now().timestamp())),
            thread_ts=None,
            is_dm=False,
            thread_context=None
        )
        
        print(f"\n2️⃣ Testing with production query: '{test_message.text}'")
        
        # Process through orchestrator exactly like production
        print("\n3️⃣ Processing through orchestrator...")
        result = await orchestrator.process_query(test_message)
        
        print(f"\n📊 PRODUCTION FLOW RESULT:")
        print("=" * 50)
        
        if result:
            print(f"✅ Orchestrator returned result")
            print(f"   Type: {type(result)}")
            
            # Check if we have Atlassian results
            if "gathered_information" in result:
                gathered = result["gathered_information"]
                if "atlassian_results" in gathered:
                    atlassian_results = gathered["atlassian_results"]
                    print(f"   Atlassian results count: {len(atlassian_results)}")
                    
                    for i, ar in enumerate(atlassian_results):
                        print(f"   Result {i+1}: success={ar.get('success', False)}")
                        if ar.get('success'):
                            print(f"     Data found: {type(ar.get('result', 'None'))}")
                        else:
                            print(f"     Error: {ar.get('error', 'Unknown')}")
                else:
                    print("   No atlassian_results in gathered_information")
            else:
                print("   No gathered_information in result")
            
            return True
        else:
            print("❌ Orchestrator returned None")
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_production_mcp_flow())
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")