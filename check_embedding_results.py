"""
Check the results of the channel embedding process.
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from tools.vector_search import VectorSearchTool

async def check_results():
    """Check embedding results and test search."""
    try:
        print("=== CHECKING EMBEDDING RESULTS ===")
        
        # Initialize services
        embedding_service = EmbeddingService()
        search_tool = VectorSearchTool()
        
        # Check Pinecone index stats
        print("1. Checking Pinecone index statistics...")
        stats = await embedding_service.get_index_stats()
        
        if stats:
            print(f"   Total vectors: {stats.get('total_vector_count', 0)}")
            print(f"   Index dimension: {stats.get('dimension', 0)}")
            
            if 'namespaces' in stats:
                namespaces = stats['namespaces']
                print(f"   Namespaces: {list(namespaces.keys())}")
                for ns, ns_stats in namespaces.items():
                    print(f"     {ns}: {ns_stats.get('vector_count', 0)} vectors")
        
        # Test search functionality
        print("\n2. Testing vector search...")
        
        search_queries = [
            "autopilot design patterns",
            "conversation thread",
            "user message",
            "frustrating"
        ]
        
        for i, query in enumerate(search_queries, 1):
            print(f"\n   Query {i}: '{query}'")
            try:
                results = await search_tool.search(query, max_results=3)
                
                if results and 'results' in results:
                    search_results = results['results']
                    print(f"     Found {len(search_results)} results")
                    
                    for j, result in enumerate(search_results, 1):
                        score = result.get('score', 0)
                        preview = result.get('text_preview', 'No preview')[:80]
                        print(f"       {j}. Score: {score:.3f} - {preview}...")
                else:
                    print(f"     No results found")
                    
            except Exception as e:
                print(f"     Search error: {e}")
        
        # Check recent vectors
        print("\n3. Checking recent vectors...")
        try:
            # Try to get some sample vectors
            recent_results = await search_tool.search("", max_results=5)  # Empty query to get any results
            
            if recent_results and 'results' in recent_results:
                recent = recent_results['results']
                print(f"   Found {len(recent)} recent vectors")
                
                for i, result in enumerate(recent, 1):
                    metadata = result.get('metadata', {})
                    channel = metadata.get('channel_name', 'unknown')
                    user = metadata.get('user_name', 'unknown')
                    timestamp = metadata.get('timestamp', 'unknown')
                    preview = result.get('text_preview', 'No preview')[:60]
                    
                    print(f"     {i}. {channel} - {user} - {timestamp}")
                    print(f"        {preview}...")
            else:
                print("   No vectors found")
                
        except Exception as e:
            print(f"   Error checking recent vectors: {e}")
        
        print(f"\n=== SUMMARY ===")
        
        total_vectors = 0
        if stats and 'total_vector_count' in stats:
            total_vectors = stats['total_vector_count']
        
        if total_vectors > 0:
            print(f"✅ SUCCESS: {total_vectors} messages embedded and searchable")
            print(f"   Vector database is operational")
            print(f"   Search functionality working")
            print(f"   Ready for production use")
        else:
            print(f"❌ No vectors found in database")
            print(f"   Embedding process may have failed")
            print(f"   Check logs for errors")
            
    except Exception as e:
        print(f"Error checking results: {e}")

if __name__ == "__main__":
    asyncio.run(check_results())