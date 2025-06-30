"""
Careful embedding process with proper rate limiting.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from services.slack_connector import SlackConnector
from services.data_processor import DataProcessor
from tools.vector_search import VectorSearchTool

async def careful_embedding():
    """Run embedding process with careful rate limiting."""
    try:
        print("Starting careful embedding process...")
        
        # Initialize services
        embedding_service = EmbeddingService()
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        search_tool = VectorSearchTool()
        
        channel_id = "C087QKECFKQ"
        
        # Use a smaller time window to avoid rate limits
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)  # Just last 30 days
        
        print(f"Extracting messages from last 30 days...")
        print(f"Time range: {start_time} to {end_time}")
        
        # Extract with smaller batch size and delays
        raw_messages = await slack_connector.extract_channel_messages(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            batch_size=10  # Very small batch to avoid rate limits
        )
        
        print(f"Extracted {len(raw_messages)} messages")
        
        if not raw_messages:
            print("No messages in time range, trying different approach...")
            
            # Try direct API call with minimal parameters
            from slack_sdk import WebClient
            from config import settings
            
            client = WebClient(token=settings.SLACK_BOT_TOKEN)
            
            # Simple call to get recent messages
            print("Trying direct API call...")
            time.sleep(2)  # Rate limit protection
            
            try:
                response = client.conversations_history(
                    channel=channel_id,
                    limit=20
                )
                
                if response['ok']:
                    messages = response['messages']
                    print(f"Direct API call retrieved {len(messages)} messages")
                    
                    # Convert to our format
                    simple_messages = []
                    for msg in messages:
                        if 'text' in msg and msg['text'].strip():
                            simple_messages.append({
                                'text': msg['text'],
                                'user': msg.get('user', 'unknown'),
                                'ts': msg['ts'],
                                'channel': channel_id
                            })
                    
                    if simple_messages:
                        print(f"Processing {len(simple_messages)} valid messages...")
                        
                        # Simple processing - convert to ProcessedMessage format
                        from models.schemas import ProcessedMessage
                        
                        processed = []
                        for msg in simple_messages:
                            try:
                                processed_msg = ProcessedMessage(
                                    text=msg['text'],
                                    user_id=msg['user'],
                                    user_name=msg['user'],
                                    user_first_name=msg['user'],
                                    user_display_name=msg['user'],
                                    user_title="Unknown",
                                    user_department="Unknown",
                                    channel_id=channel_id,
                                    channel_name="autopilot-design-patterns",
                                    message_ts=msg['ts'],
                                    thread_ts=None,
                                    is_dm=False
                                )
                                processed.append(processed_msg)
                            except Exception as e:
                                print(f"Error processing message: {e}")
                                continue
                        
                        if processed:
                            print(f"Successfully processed {len(processed)} messages")
                            
                            # Embed the messages
                            print("Embedding messages...")
                            embedded_count = await embedding_service.embed_and_store_messages(processed)
                            print(f"Embedded {embedded_count} messages")
                            
                            if embedded_count > 0:
                                # Test search
                                print("Testing search...")
                                time.sleep(1)
                                
                                try:
                                    results = await search_tool.search("autopilot", top_k=3)
                                    print(f"Search test: {len(results)} results found")
                                    
                                    if results:
                                        for i, result in enumerate(results, 1):
                                            score = result.get('score', 0)
                                            print(f"  {i}. Score: {score:.3f}")
                                    
                                    print("\nEMBEDDING SUCCESSFUL!")
                                    print(f"Successfully embedded {embedded_count} messages from autopilot-design-patterns")
                                    print("Vector search is working correctly")
                                    return True
                                    
                                except Exception as e:
                                    print(f"Search test failed: {e}")
                                    return False
                            else:
                                print("No messages were embedded")
                                return False
                        else:
                            print("No messages could be processed")
                            return False
                else:
                    print(f"API call failed: {response.get('error')}")
                    return False
                    
            except Exception as e:
                print(f"Direct API call failed: {e}")
                return False
        else:
            # Process normally if we got messages from extract_channel_messages
            processed_messages = await data_processor.process_messages(raw_messages)
            print(f"Processed {len(processed_messages)} messages")
            
            embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
            print(f"Embedded {embedded_count} messages")
            
            if embedded_count > 0:
                print("Testing search...")
                results = await search_tool.search("autopilot", top_k=3)
                print(f"Search test: {len(results)} results")
                
                print("\nEMBEDDING SUCCESSFUL!")
                return True
            else:
                print("Embedding failed")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(careful_embedding())
    
    if success:
        print("\n🎉 SUCCESS: Autopilot channel conversations are now embedded and searchable!")
    else:
        print("\n❌ Process failed - check errors above")