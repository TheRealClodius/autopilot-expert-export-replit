"""
Find channels where the bot has actual message access for testing the embedding pipeline.
"""

import asyncio
import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def find_usable_channels():
    """Find channels where bot can actually read messages for pipeline testing."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        print("Searching for channels with accessible message history...")
        
        # Get all conversations where bot might be a member
        conv_response = client.conversations_list(
            types="public_channel,private_channel", 
            exclude_archived=False,
            limit=200
        )
        channels = conv_response['channels']
        
        print(f"Testing {len(channels)} channels for message access...")
        accessible_channels = []
        
        for i, channel in enumerate(channels[:50]):  # Test first 50 to avoid rate limits
            channel_id = channel['id']
            channel_name = channel['name']
            is_member = channel.get('is_member', False)
            
            if i % 10 == 0:
                print(f"  Progress: {i}/50 channels tested...")
            
            # Only test channels where bot is a member (likely to work)
            if is_member:
                try:
                    history_response = client.conversations_history(
                        channel=channel_id,
                        limit=1
                    )
                    
                    if history_response['ok']:
                        messages = history_response['messages']
                        if messages:  # Has actual messages
                            accessible_channels.append({
                                'id': channel_id,
                                'name': channel_name,
                                'message_count': len(messages),
                                'latest_ts': messages[0]['ts'],
                                'is_member': is_member
                            })
                            print(f"  ✅ {channel_name}: {len(messages)} messages accessible")
                            
                            # Stop after finding a few good channels
                            if len(accessible_channels) >= 3:
                                break
                except SlackApiError as e:
                    if e.response.get('error') == 'ratelimited':
                        print("  ⏸️  Rate limited, waiting...")
                        await asyncio.sleep(2)
                    continue
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        print(f"\n=== RESULTS ===")
        if accessible_channels:
            print(f"Found {len(accessible_channels)} channels with message access:")
            for ch in accessible_channels:
                print(f"  - {ch['name']} (ID: {ch['id']}) - Latest: {ch['latest_ts']}")
            
            # Test embedding pipeline with the first accessible channel
            best_channel = accessible_channels[0]
            print(f"\n🚀 Testing embedding pipeline with: {best_channel['name']}")
            
            return best_channel
        else:
            print("❌ No channels with accessible message history found.")
            print("\nNext steps:")
            print("1. Add the bot to channel C087QKECFKQ using: /invite @ap_slack_assistant")
            print("2. Or choose a different channel where bot is already a member")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def test_with_accessible_channel(channel_info):
    """Test the embedding pipeline with an accessible channel."""
    if not channel_info:
        return None
        
    channel_id = channel_info['id']
    channel_name = channel_info['name']
    
    print(f"\n🧪 Testing complete embedding pipeline with {channel_name}...")
    
    # Import the services
    from services.embedding_service import EmbeddingService
    from services.slack_connector import SlackConnector
    from services.data_processor import DataProcessor
    from datetime import datetime, timedelta
    
    try:
        # Initialize services
        embedding_service = EmbeddingService()
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        
        # Extract recent messages
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # Last week
        
        print("1. Extracting messages...")
        raw_messages = await slack_connector.extract_channel_messages(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            batch_size=10
        )
        
        if not raw_messages:
            print("   ❌ No messages found")
            return None
        
        print(f"   ✅ Extracted {len(raw_messages)} messages")
        
        # Process messages  
        print("2. Processing messages...")
        processed_messages = await data_processor.process_messages(raw_messages)
        print(f"   ✅ Processed {len(processed_messages)} messages")
        
        # Embed and store
        print("3. Embedding and storing...")
        embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
        print(f"   ✅ Embedded {embedded_count} messages")
        
        # Test search
        print("4. Testing search...")
        from tools.vector_search import VectorSearchTool
        search_tool = VectorSearchTool()
        
        results = await search_tool.search("test message", max_results=3)
        print(f"   ✅ Search returned {len(results['results'])} results")
        
        if results['results']:
            print("   Top result preview:", results['results'][0]['text_preview'][:100] + "...")
        
        return {
            'channel': channel_name,
            'messages_embedded': embedded_count,
            'search_working': len(results['results']) > 0,
            'status': 'success'
        }
        
    except Exception as e:
        print(f"   ❌ Pipeline test failed: {e}")
        return None

if __name__ == "__main__":
    # Find accessible channels
    channel_info = asyncio.run(find_usable_channels())
    
    # Test pipeline if we found a channel
    if channel_info:
        result = asyncio.run(test_with_accessible_channel(channel_info))
        if result:
            print(f"\n🎉 SUCCESS: Embedding pipeline working with {result['messages_embedded']} messages!")
            print("Ready to use with target channel once bot is added.")
        else:
            print("\n❌ Pipeline test failed")
    else:
        print("\n📋 ACTION REQUIRED: Add bot to target channel to proceed")