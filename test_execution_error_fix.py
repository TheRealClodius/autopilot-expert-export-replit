#!/usr/bin/env python3
"""
Test the execution error fix for Atlassian MCP integration.
Verify orchestrator can now execute MCP actions without getting "execution error".
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

async def test_execution_error_fix():
    """Test the fixed execution error for Atlassian actions"""
    print("🔧 TESTING EXECUTION ERROR FIX")
    print("=" * 50)
    
    try:
        # Initialize services
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Create test message asking for Autopilot pages
        test_message = ProcessedMessage(
            text="Find Autopilot for Everyone pages",
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
        
        print(f"🎯 Test Query: '{test_message.text}'")
        print()
        
        # Test direct action execution that was previously failing
        print("1️⃣ Testing direct MCP action execution...")
        
        # This is the exact format the orchestrator now generates
        test_action = {
            "mcp_tool": "confluence_search",
            "arguments": {
                "query": "autopilot for everyone",
                "limit": 5
            }
        }
        
        print(f"   Action format: {test_action}")
        
        # Execute the action directly through the fixed method
        result = await orchestrator._execute_single_tool_action("atlassian", test_action)
        
        if result and not result.get("error"):
            print("✅ SUCCESS: Direct MCP action execution completed")
            
            # Check result structure
            if isinstance(result, dict) and result.get("success"):
                data = result.get("result", [])
                if isinstance(data, list) and len(data) > 0:
                    print(f"   Retrieved {len(data)} Autopilot pages")
                    for i, page in enumerate(data[:3], 1):
                        title = page.get("title", "No title") if isinstance(page, dict) else str(page)
                        print(f"   Page {i}: {title}")
                else:
                    print(f"   Result structure: {type(data)}")
            else:
                print(f"   Raw result: {str(result)[:200]}...")
            
            return True
            
        else:
            print(f"❌ EXECUTION ERROR STILL EXISTS: {result}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_execution_error_fix())
    if success:
        print("\n🎉 EXECUTION ERROR FIX VERIFIED")
        print("   The orchestrator can now execute Atlassian MCP actions successfully!")
    else:
        print("\n💥 EXECUTION ERROR STILL EXISTS")
        print("   Further investigation needed.")