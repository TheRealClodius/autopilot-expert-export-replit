"""
Embed genai-designsys channel with rate limiting protection.
"""

import asyncio
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from services.data_processor import DataProcessor
from tools.vector_search import VectorSearchTool
from models.schemas import ProcessedMessage
from slack_sdk import WebClient
from config import settings

async def embed_genai_channel():
    """Embed genai-designsys channel with careful rate limiting."""
    try:
        print("=== EMBEDDING GENAI-DESIGNSYS CHANNEL ===")
        
        channel_id = "C08STCP2YUA"
        channel_name = "genai-designsys"
        
        print(f"Target: {channel_name} ({channel_id})")
        
        # Initialize services
        embedding_service = EmbeddingService()
        data_processor = DataProcessor()
        search_tool = VectorSearchTool()
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        print("Services initialized")
        
        # Try to get recent messages with rate limiting
        print("Extracting messages...")
        time.sleep(3)  # Initial delay
        
        try:
            response = client.conversations_history(
                channel=channel_id,
                limit=15  # Small batch to avoid rate limits
            )
            
            if not response['ok']:
                error = response.get('error', 'unknown')
                if error == 'not_in_channel':
                    print(f"❌ Bot is not a member of #{channel_name}")
                    print(f"   To fix: Add bot (@ap_slack_assistant) to #{channel_name}")
                    print(f"   Command: /invite @ap_slack_assistant in #{channel_name}")
                    return False
                else:
                    print(f"❌ Slack API error: {error}")
                    return False
            
            messages = response['messages']
            print(f"Found {len(messages)} recent messages")
            
            if not messages:
                print("No messages found")
                return False
            
            # Convert to ProcessedMessage format
            processed = []
            for msg in messages:
                if 'text' in msg and msg['text'].strip():
                    try:
                        processed_msg = ProcessedMessage(
                            text=msg['text'],
                            user_id=msg.get('user', 'unknown'),
                            user_name=msg.get('user', 'unknown'),
                            user_first_name=msg.get('user', 'unknown'),
                            user_display_name=msg.get('user', 'unknown'),
                            user_title="Unknown",
                            user_department="Unknown",
                            channel_id=channel_id,
                            channel_name=channel_name,
                            message_ts=msg['ts'],
                            thread_ts=msg.get('thread_ts'),
                            is_dm=False
                        )
                        processed.append(processed_msg)
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        continue
            
            print(f"Processed {len(processed)} valid messages")
            
            if not processed:
                print("No valid messages to embed")
                return False
            
            # Sample message preview
            sample = processed[0]
            print(f"Sample: '{sample.text[:60]}...' from {sample.user_name}")
            
            # Embed messages
            print("Embedding messages...")
            time.sleep(2)
            
            embedded_count = await embedding_service.embed_and_store_messages(processed)
            print(f"Successfully embedded {embedded_count} messages")
            
            if embedded_count == 0:
                print("No messages were embedded")
                return False
            
            # Test search
            print("Testing search functionality...")
            time.sleep(1)
            
            try:
                results = await search_tool.search("genai", top_k=5)
                
                if results and len(results) > 0:
                    print(f"Search test successful: {len(results)} results")
                    
                    for i, result in enumerate(results, 1):
                        score = result.get('score', 0)
                        metadata = result.get('metadata', {})
                        channel = metadata.get('channel_name', 'unknown')
                        user = metadata.get('user_name', 'unknown')
                        
                        print(f"  {i}. Score: {score:.3f} - {channel} - {user}")
                    
                    print(f"\n✅ SUCCESS: {channel_name} embedded and searchable!")
                    print(f"   Embedded {embedded_count} messages")
                    print(f"   Search functionality working")
                    print(f"   GenAI design system conversations now available")
                    return True
                    
                else:
                    print("Search test failed - no results")
                    return False
                    
            except Exception as e:
                print(f"Search test error: {e}")
                return False
                
        except Exception as e:
            if "ratelimited" in str(e).lower():
                print("❌ Rate limited by Slack API")
                print("   Please wait a few minutes and try again")
            else:
                print(f"❌ Error accessing channel: {e}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(embed_genai_channel())
    
    if success:
        print("\n🎉 GenAI Design System channel successfully embedded!")
        print("Vector database now contains both autopilot and genai-designsys conversations")
    else:
        print("\n🔧 Embedding failed - see output above for details")