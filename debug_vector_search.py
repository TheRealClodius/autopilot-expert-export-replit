#!/usr/bin/env python3
"""
Debug script to test vector search tool execution directly
"""

import asyncio
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage

async def test_vector_search_behavior():
    """Test what happens when orchestrator should use vector search"""
    
    print("🔍 Testing Vector Search Behavior...")
    
    try:
        # Initialize components
        memory_service = MemoryService()
        orchestrator = OrchestratorAgent(memory_service)
        
        # Test different types of queries to see when vector search is used
        test_queries = [
            "What is Autopilot?",  # Should be Atlassian first
            "How do I learn Python programming?",  # Should be vector search
            "Tell me about design patterns",  # Should be vector search  
            "What are the latest news?",  # Should be perplexity
            "Generic programming concepts",  # Should be vector search
            "UiPath project status",  # Should be Atlassian
        ]
        
        for query in test_queries:
            print(f"\n📝 Testing query: '{query}'")
            
            # Create test message
            test_message = ProcessedMessage(
                channel_id="C087QKECFKQ",
                user_id="U12345TEST", 
                text=query,
                message_ts="1640995200.001500",
                thread_ts=None,
                user_name="test_user",
                user_first_name="Test",
                user_display_name="Test User",
                user_title="Software Engineer",
                user_department="Engineering",
                channel_name="general",
                is_dm=False
            )
            
            # Test query analysis
            try:
                execution_plan = await asyncio.wait_for(
                    orchestrator._analyze_query_and_plan(test_message), 
                    timeout=30.0
                )
                
                if execution_plan:
                    tools_needed = execution_plan.get("tools_needed", [])
                    vector_queries = execution_plan.get("vector_queries", [])
                    atlassian_actions = execution_plan.get("atlassian_actions", [])
                    perplexity_queries = execution_plan.get("perplexity_queries", [])
                    
                    print(f"   Tools needed: {tools_needed}")
                    print(f"   Vector queries: {vector_queries}")
                    print(f"   Atlassian actions: {len(atlassian_actions)} actions")
                    print(f"   Perplexity queries: {perplexity_queries}")
                    print(f"   Analysis: {execution_plan.get('analysis', 'No analysis')}")
                    
                    # Check if vector search is being refused
                    if "vector_search" not in tools_needed and "programming" in query.lower():
                        print("   ⚠️  Vector search NOT selected for programming query!")
                    elif "vector_search" in tools_needed:
                        print("   ✅ Vector search correctly selected")
                        
                else:
                    print("   ❌ No execution plan returned")
                    
            except asyncio.TimeoutError:
                print("   ⏰ Query analysis timed out")
            except Exception as e:
                print(f"   ❌ Error in query analysis: {e}")
                
        # Test vector search tool directly
        print(f"\n🔧 Testing Vector Search Tool Directly...")
        
        try:
            vector_results = await orchestrator.vector_tool.search("Python programming concepts", top_k=3)
            print(f"   Direct vector search returned {len(vector_results)} results")
            if vector_results:
                print(f"   First result: {vector_results[0].get('content', '')[:100]}...")
            else:
                print("   ⚠️  No results from vector search - check Pinecone connection")
        except Exception as e:
            print(f"   ❌ Direct vector search failed: {e}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_search_behavior())