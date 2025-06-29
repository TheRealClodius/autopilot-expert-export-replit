#!/usr/bin/env python3

"""
Test Orchestrator Jira Routing
Test if orchestrator correctly routes Jira queries and uses correct parameters
"""

import asyncio
import sys
sys.path.append('.')

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage

async def test_orchestrator_jira_routing():
    """Test orchestrator routing for Jira queries"""
    
    print("🔧 TESTING ORCHESTRATOR JIRA ROUTING")
    print("=" * 50)
    
    try:
        # Initialize services
        print("1️⃣ Initializing orchestrator...")
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        print("✅ Orchestrator initialized")
        
        # Test message for Jira query
        print("\n2️⃣ Testing Jira query routing...")
        message = ProcessedMessage(
            event_type="app_mention",
            text="Can you show me recent tickets from the DESIGN project?",
            channel="C_TEST_CHANNEL",
            user="U_TEST_USER",
            timestamp="1234567890.123",
            thread_ts=None,
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Designer",
            user_department="Product"
        )
        
        print(f"   Query: {message.text}")
        
        # Process through orchestrator
        result = await orchestrator.process_query(message)
        
        print(f"\n📊 ORCHESTRATOR ANALYSIS:")
        print("=" * 50)
        
        if result and result.get("execution_plan"):
            plan = result["execution_plan"]
            print(f"✅ Execution plan created")
            
            # Check for Atlassian actions
            atlassian_actions = plan.get("atlassian_actions", [])
            if atlassian_actions:
                print(f"   Found {len(atlassian_actions)} Atlassian actions:")
                for i, action in enumerate(atlassian_actions):
                    mcp_tool = action.get("mcp_tool", "unknown")
                    arguments = action.get("arguments", {})
                    print(f"     {i+1}. Tool: {mcp_tool}")
                    print(f"        Arguments: {arguments}")
                    
                    # Check if using correct parameter names
                    if mcp_tool == "jira_search":
                        if "limit" in arguments:
                            print(f"        ✅ Using correct 'limit' parameter")
                        elif "max_results" in arguments:
                            print(f"        ❌ Using wrong 'max_results' parameter")
                        else:
                            print(f"        ⚠️  No limit parameter found")
                            
                return True
            else:
                print(f"   ❌ No Atlassian actions found")
                
                # Check if it chose other tools instead
                vector_actions = plan.get("vector_search", [])
                perplexity_actions = plan.get("perplexity_search", [])
                print(f"   Vector search actions: {len(vector_actions)}")
                print(f"   Perplexity search actions: {len(perplexity_actions)}")
                
                return False
        else:
            print(f"❌ No execution plan generated")
            print(f"   Result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_orchestrator_jira_routing())
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")