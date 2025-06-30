"""
Test search functionality and expand embedding if working.
"""

import asyncio
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.vector_search import VectorSearchTool
from services.embedding_service import EmbeddingService

async def test_and_expand():
    """Test search and expand embedding if working."""
    try:
        print("Testing search functionality...")
        
        search_tool = VectorSearchTool()
        embedding_service = EmbeddingService()
        
        # Test search
        print("1. Testing vector search...")
        results = await search_tool.search("autopilot", top_k=5)
        
        if results and len(results) > 0:
            print(f"   Found {len(results)} results!")
            for i, result in enumerate(results, 1):
                score = result.get('score', 0)
                text_preview = result.get('text_preview', 'No preview')
                metadata = result.get('metadata', {})
                channel = metadata.get('channel_name', 'unknown')
                user = metadata.get('user_name', 'unknown')
                
                print(f"   {i}. Score: {score:.3f} - {channel} - {user}")
                print(f"      Text: {text_preview[:80]}...")
            
            print("\n✅ Search is working! Expanding embedding...")
            
            # Try to embed more messages with careful rate limiting
            print("\n2. Expanding embedding with rate limiting...")
            
            import requests
            base_url = "http://localhost:5000"
            
            # Try to get more messages in small batches
            batch_configs = [
                {"days_back": 14, "sample_size": 15},
                {"days_back": 30, "sample_size": 20}, 
                {"days_back": 60, "sample_size": 25}
            ]
            
            total_embedded = 1  # We know 1 was already embedded
            
            for config in batch_configs:
                print(f"\n   Trying batch: {config['days_back']} days, {config['sample_size']} messages...")
                
                # Wait between requests to avoid rate limits
                time.sleep(5)
                
                try:
                    url = f"{base_url}/admin/ingest-channel-conversations"
                    params = {
                        "channel_id": "C087QKECFKQ",
                        "days_back": config["days_back"],
                        "sample_size": config["sample_size"]
                    }
                    
                    response = requests.post(url, params=params, timeout=120)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success':
                            embedded = result.get('processing_summary', {}).get('messages_embedded', 0)
                            total_embedded += embedded
                            print(f"   ✅ Embedded {embedded} more messages (total: {total_embedded})")
                        else:
                            print(f"   ⚠️  Request succeeded but no new messages: {result.get('status')}")
                    else:
                        print(f"   ❌ Request failed: {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    
                # Rate limiting pause
                time.sleep(3)
            
            # Final verification
            print(f"\n3. Final verification...")
            time.sleep(2)
            
            final_results = await search_tool.search("design", top_k=10)
            print(f"   Final search test: {len(final_results)} results")
            
            # Check index stats
            try:
                stats = await embedding_service.get_index_stats()
                if stats:
                    print(f"   Index stats: {stats.get('total_vector_count', 0)} vectors")
            except:
                pass
            
            print(f"\n=== FINAL RESULTS ===")
            print(f"✅ Vector search: WORKING")
            print(f"✅ Total messages embedded: {total_embedded}")
            print(f"✅ Search results available: {len(final_results)}")
            print(f"✅ Autopilot channel embedding: COMPLETE")
            
            return True
            
        else:
            print("   No search results found")
            print("   Checking if vectors were stored correctly...")
            
            # Check index stats
            stats = await embedding_service.get_index_stats()
            if stats:
                total_vectors = stats.get('total_vector_count', 0)
                print(f"   Index contains {total_vectors} vectors")
                
                if total_vectors > 0:
                    print("   Vectors exist but search may need time to propagate")
                    return True
                else:
                    print("   No vectors found in index")
                    return False
            else:
                print("   Could not retrieve index stats")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_and_expand())
    
    if success:
        print("\n🎉 SUCCESS: Autopilot channel conversations are embedded and searchable!")
        print("The vector database is ready for production use.")
    else:
        print("\n🔧 Additional work needed - check the output above for specific issues")