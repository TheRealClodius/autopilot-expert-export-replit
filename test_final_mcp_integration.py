#!/usr/bin/env python3
"""
Final MCP Integration Test

Tests the complete end-to-end MCP integration with the orchestrator
to verify the multi-agent system can successfully use Atlassian tools.
"""

import asyncio
import logging
import sys
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_final_mcp_integration():
    """Test complete MCP integration through orchestrator"""
    print("🔧 TESTING FINAL MCP INTEGRATION")
    print("=" * 50)
    
    try:
        # Initialize services
        memory_service = MemoryService()
        progress_tracker = ProgressTracker()
        
        # Initialize orchestrator agent
        orchestrator = OrchestratorAgent(
            memory_service=memory_service,
            progress_tracker=progress_tracker
        )
        
        print("✅ Orchestrator initialized")
        
        # Create test message for Atlassian search
        test_message = ProcessedMessage(
            text="Who owns the UX Audit Evaluation Template?",
            user_id="U_TEST_USER",
            user_name="testuser",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Developer",
            user_department="Engineering",
            channel_id="C_TEST_CHANNEL",
            channel_name="test-channel",
            message_ts="1640995200.000100",
            thread_ts=None,
            message_type="channel_message"
        )
        
        print(f"📝 Testing query: {test_message.text}")
        
        # Mock progress updater
        progress_events = []
        async def mock_progress_updater(message: str):
            progress_events.append(message)
            print(f"📊 Progress: {message}")
        
        # Execute orchestrator analysis
        print("🤖 Running orchestrator analysis...")
        result = await orchestrator.process_message(
            message=test_message,
            progress_updater=mock_progress_updater
        )
        
        print(f"✅ Orchestrator completed")
        print(f"📊 Progress events: {len(progress_events)}")
        
        # Check if Atlassian tool was used
        if result and "orchestrator_analysis" in result:
            analysis = result["orchestrator_analysis"]
            tools_used = analysis.get("tools_used", [])
            
            if "atlassian_search" in tools_used:
                print("✅ Atlassian MCP tool successfully executed!")
                
                # Check for search results
                if "search_results" in analysis:
                    results = analysis["search_results"]
                    print(f"📄 Found {len(results) if isinstance(results, list) else 1} result(s)")
                else:
                    print("⚠️ No search results in analysis")
            else:
                print(f"❌ Atlassian tool not used. Tools used: {tools_used}")
        else:
            print("❌ No orchestrator analysis in result")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_final_mcp_integration())
    print(f"\n🏁 Final result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")