#!/usr/bin/env python3
"""
Test Autopilot Summary Generation
Find all Autopilot for Everyone pages and generate executive summary
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
from services.memory_service import MemoryService
from services.progress_tracker import ProgressTracker

async def test_autopilot_summary():
    """Test orchestrator finding Autopilot pages and generating executive summary"""
    
    print("🔍 TESTING AUTOPILOT FOR EVERYONE SUMMARY GENERATION")
    print("="*70)
    
    try:
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        print(f"✅ Orchestrator initialized")
        print(f"✅ Atlassian tool available: {orchestrator.atlassian_tool.available}")
        
        if not orchestrator.atlassian_tool.available:
            print("❌ Atlassian tool not available - missing credentials")
            print("   Please ensure ATLASSIAN_* environment variables are set")
            return
        
        # Create test message requesting Autopilot summary
        test_message = ProcessedMessage(
            channel_id="C087QKECFKQ",
            user_id="U12345TEST",
            text="Find all Autopilot for Everyone pages and summaries then create an executive summary",
            message_ts=f"{int(datetime.now().timestamp())}.001500",
            thread_ts=None,
            user_name="test_user",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Product Manager",
            user_department="Product",
            channel_name="general",
            is_dm=False,
            thread_context=""
        )
        
        print(f"\n📝 Query: {test_message.text}")
        print()
        
        print("🎯 Starting orchestrator processing...")
        print()
        
        # Process the query through orchestrator
        result = await orchestrator.process_query(test_message)
        
        print("\n" + "="*70)
        print("📊 FINAL RESULTS:")
        print("="*70)
        
        if result:
            print("✅ Orchestrator completed successfully")
            print(f"\n📄 Generated Response:")
            print("-" * 40)
            print(result.get('text', 'No response text'))
            print("-" * 40)
            
            # Show response metadata
            print(f"\n📋 Response Metadata:")
            print(f"   Channel: {result.get('channel_id')}")
            print(f"   Thread: {result.get('thread_ts')}")
            print(f"   Timestamp: {result.get('timestamp')}")
            
            if 'suggestions' in result:
                print(f"   Suggestions: {len(result['suggestions'])} provided")
        else:
            print("❌ Orchestrator processing failed - no result returned")
        
        print("\n🏁 Test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_autopilot_summary())