#!/usr/bin/env python3
"""
Simple test to check vector search tool directly without orchestrator complications
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.vector_search import VectorSearchTool

async def test_vector_tool_directly():
    """Test vector search tool directly"""
    
    print("🔍 Testing Vector Search Tool Directly...")
    
    try:
        # Initialize vector search tool
        vector_tool = VectorSearchTool()
        print("✅ Vector search tool initialized")
        
        # Test search queries
        test_queries = [
            "Python programming",
            "design patterns", 
            "autopilot features",
            "UiPath automation"
        ]
        
        for query in test_queries:
            print(f"\n📝 Searching for: '{query}'")
            
            try:
                results = await vector_tool.search(query, top_k=3)
                print(f"   Found {len(results)} results")
                
                if results:
                    for i, result in enumerate(results):
                        score = result.get('score', 0)
                        content = result.get('content', '')[:100]
                        print(f"   {i+1}. Score: {score:.3f} - {content}...")
                else:
                    print("   No results found")
                    
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
    
    except Exception as e:
        print(f"❌ Tool initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_tool_directly())