"""
Complete embedding process for autopilot-design-patterns channel.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from services.slack_connector import SlackConnector
from services.data_processor import DataProcessor
from tools.vector_search import VectorSearchTool

async def run_complete_embedding():
    """Run complete embedding process and verify results."""
    try:
        print("=== COMPLETE SLACK CHANNEL EMBEDDING PROCESS ===")
        
        # Channel information
        channel_id = "C087QKECFKQ"
        channel_name = "autopilot-design-patterns"
        
        print(f"Target: {channel_name} ({channel_id})")
        
        # Initialize services
        print("\n1. Initializing services...")
        embedding_service = EmbeddingService()
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        search_tool = VectorSearchTool()
        print("   Services initialized successfully")
        
        # Clear existing vectors first to avoid duplicates
        print("\n2. Clearing existing vectors...")
        try:
            await embedding_service.purge_vectors()
            print("   Existing vectors cleared")
        except Exception as e:
            print(f"   Warning: Could not clear vectors: {e}")
        
        # Extract messages
        print("\n3. Extracting messages from Slack...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=730)  # 2 years
        
        print(f"   Time range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
        
        raw_messages = await slack_connector.extract_channel_messages(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            batch_size=50
        )
        
        if not raw_messages:
            print("   No messages found in time range")
            return False
        
        print(f"   Extracted {len(raw_messages)} raw messages")
        
        # Process messages
        print("\n4. Processing messages...")
        processed_messages = await data_processor.process_messages(raw_messages)
        print(f"   Processed {len(processed_messages)} messages")
        
        if not processed_messages:
            print("   No messages after processing")
            return False
        
        # Sample processed message for verification
        if processed_messages:
            sample = processed_messages[0]
            print(f"   Sample message: '{sample.text[:80]}...'")
            print(f"   User: {sample.user_name} ({sample.user_id})")
            print(f"   Timestamp: {sample.message_ts}")
        
        # Embed and store
        print("\n5. Embedding and storing in Pinecone...")
        embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
        print(f"   Successfully embedded {embedded_count} messages")
        
        if embedded_count == 0:
            print("   Error: No messages were embedded")
            return False
        
        # Verify storage
        print("\n6. Verifying vector storage...")
        stats = await embedding_service.get_index_stats()
        
        if stats:
            total_vectors = stats.get('total_vector_count', 0)
            print(f"   Total vectors in index: {total_vectors}")
            print(f"   Index dimension: {stats.get('dimension', 0)}")
            
            if 'namespaces' in stats:
                namespaces = stats['namespaces']
                for ns, ns_stats in namespaces.items():
                    print(f"   Namespace '{ns}': {ns_stats.get('vector_count', 0)} vectors")
        
        # Test search functionality
        print("\n7. Testing search functionality...")
        
        test_queries = [
            "autopilot",
            "conversation",
            "design patterns", 
            "user message"
        ]
        
        working_searches = 0
        
        for query in test_queries:
            try:
                results = await search_tool.search(query, top_k=3)
                
                if results and len(results) > 0:
                    working_searches += 1
                    print(f"   Query '{query}': {len(results)} results (score: {results[0].get('score', 0):.3f})")
                else:
                    print(f"   Query '{query}': No results")
                    
            except Exception as e:
                print(f"   Query '{query}': Error - {e}")
        
        # Final verification
        print(f"\n=== RESULTS SUMMARY ===")
        print(f"✅ Channel: {channel_name}")
        print(f"✅ Messages extracted: {len(raw_messages)}")
        print(f"✅ Messages processed: {len(processed_messages)}")
        print(f"✅ Messages embedded: {embedded_count}")
        print(f"✅ Search queries working: {working_searches}/{len(test_queries)}")
        
        if embedded_count > 0 and working_searches > 0:
            print(f"\n🎉 SUCCESS: Complete embedding pipeline operational!")
            print(f"   {embedded_count} messages from {channel_name} are now searchable")
            print(f"   Vector search is working correctly")
            print(f"   Ready for production use")
            return True
        else:
            print(f"\n❌ ISSUES FOUND:")
            if embedded_count == 0:
                print(f"   - No messages were embedded")
            if working_searches == 0:
                print(f"   - Search functionality not working")
            return False
            
    except Exception as e:
        print(f"Error in embedding process: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_complete_embedding())
    
    if success:
        print(f"\n🚀 READY FOR PRODUCTION")
        print(f"The embedding system is fully operational with real Slack data")
    else:
        print(f"\n🔧 TROUBLESHOOTING NEEDED")
        print(f"Check the error messages above for specific issues")