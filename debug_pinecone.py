"""
Debug script to test Pinecone vector storage and retrieval.
"""

import asyncio
import sys
import os
import time

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from pinecone import Pinecone
from config import settings

async def debug_pinecone():
    """Debug Pinecone storage and search functionality."""
    try:
        print("1. Testing Pinecone connectivity...")
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        print("✅ Connected to Pinecone")
        
        print("2. Getting index description...")
        description = index.describe_index_stats()
        print(f"Index stats: {description}")
        
        print("3. Testing direct vector insertion...")
        test_vectors = [
            {
                "id": "test_vector_1",
                "values": [0.1] * 768,  # 768-dimensional test vector
                "metadata": {"test": "true", "source": "debug"}
            },
            {
                "id": "test_vector_2", 
                "values": [0.2] * 768,
                "metadata": {"test": "true", "source": "debug"}
            }
        ]
        
        upsert_response = index.upsert(vectors=test_vectors)
        print(f"Upsert response: {upsert_response}")
        
        print("4. Waiting for indexing (10 seconds)...")
        time.sleep(10)
        
        print("5. Checking index stats after upsert...")
        stats_after = index.describe_index_stats()
        print(f"Stats after upsert: {stats_after}")
        
        print("6. Testing query...")
        query_vector = [0.15] * 768  # Similar to test vectors
        query_response = index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True
        )
        print(f"Query response: {query_response}")
        
        print("7. Testing EmbeddingService...")
        embedding_service = EmbeddingService()
        
        # Test embedding generation
        test_text = "UiPath Autopilot integration test"
        embedding = await embedding_service.embed_text(test_text)
        print(f"Generated embedding length: {len(embedding) if embedding else 'None'}")
        
        if embedding:
            print("8. Testing search with real embedding...")
            search_response = index.query(
                vector=embedding,
                top_k=5,
                include_metadata=True
            )
            print(f"Search response: {search_response}")
        
        print("9. Cleaning up test vectors...")
        index.delete(ids=["test_vector_1", "test_vector_2"])
        print("✅ Cleanup complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_pinecone())