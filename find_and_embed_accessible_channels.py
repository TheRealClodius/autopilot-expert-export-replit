"""
Find channels where bot has access and embed all conversation history.
"""

import asyncio
import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from services.embedding_service import EmbeddingService
from services.slack_connector import SlackConnector
from services.data_processor import DataProcessor

async def find_accessible_channels():
    """Find all channels where bot has message access."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        print("🔍 Scanning for accessible channels...")
        
        # Get all conversations where bot might be a member
        conv_response = client.conversations_list(
            types="public_channel,private_channel", 
            exclude_archived=False,
            limit=500
        )
        channels = conv_response['channels']
        
        print(f"   Found {len(channels)} total channels")
        accessible_channels = []
        
        for channel in channels:
            channel_id = channel['id']
            channel_name = channel['name']
            is_member = channel.get('is_member', False)
            is_private = channel.get('is_private', False)
            member_count = channel.get('num_members', 0)
            
            # Only test channels where bot is a member
            if is_member:
                try:
                    # Test if we can actually read history
                    history_response = client.conversations_history(
                        channel=channel_id,
                        limit=1
                    )
                    
                    if history_response['ok']:
                        messages = history_response['messages']
                        channel_type = "Private" if is_private else "Public"
                        
                        accessible_channels.append({
                            'id': channel_id,
                            'name': channel_name,
                            'type': channel_type,
                            'member_count': member_count,
                            'has_messages': len(messages) > 0,
                            'latest_ts': messages[0]['ts'] if messages else None
                        })
                        
                        status = "✅ ACCESSIBLE" if messages else "⚠️  EMPTY"
                        print(f"   {status}: {channel_name} ({channel_type}, {member_count} members)")
                        
                except SlackApiError as e:
                    print(f"   ❌ {channel_name}: {e.response.get('error')}")
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        return accessible_channels
        
    except Exception as e:
        print(f"❌ Error scanning channels: {e}")
        return []

async def embed_channel_history(channel_info, embedding_service, slack_connector, data_processor):
    """Embed all history from a specific channel."""
    channel_id = channel_info['id']
    channel_name = channel_info['name']
    channel_type = channel_info['type']
    
    print(f"\n🚀 Processing {channel_name} ({channel_type})...")
    
    try:
        # Extract all messages (last 2 years to be comprehensive)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=730)  # 2 years back
        
        print("   📥 Extracting messages...")
        raw_messages = await slack_connector.extract_channel_messages(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            batch_size=200  # Larger batch for efficiency
        )
        
        if not raw_messages:
            print("   ⚠️  No messages found in time range")
            return {'channel': channel_name, 'messages': 0, 'embedded': 0, 'status': 'empty'}
        
        print(f"   ✅ Extracted {len(raw_messages)} messages")
        
        # Process messages
        print("   🔄 Processing messages...")
        processed_messages = await data_processor.process_messages(raw_messages)
        print(f"   ✅ Processed {len(processed_messages)} messages")
        
        # Embed and store
        print("   🧠 Embedding and storing...")
        embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
        print(f"   ✅ Embedded {embedded_count} messages")
        
        return {
            'channel': channel_name,
            'channel_type': channel_type,
            'messages_extracted': len(raw_messages),
            'messages_processed': len(processed_messages),
            'messages_embedded': embedded_count,
            'status': 'success'
        }
        
    except Exception as e:
        print(f"   ❌ Error processing {channel_name}: {e}")
        return {
            'channel': channel_name,
            'channel_type': channel_type,
            'status': 'error',
            'error': str(e)
        }

async def main():
    """Main function to find and embed all accessible channel history."""
    print("=== SLACK CHANNEL HISTORY EMBEDDING ===")
    
    # Initialize services
    print("🔧 Initializing services...")
    embedding_service = EmbeddingService()
    slack_connector = SlackConnector()
    data_processor = DataProcessor()
    print("   ✅ Services initialized")
    
    # Find accessible channels
    accessible_channels = await find_accessible_channels()
    
    if not accessible_channels:
        print("\n❌ No accessible channels found!")
        print("Make sure the bot has been added to channels using /invite @ap_slack_assistant")
        return
    
    print(f"\n📊 Found {len(accessible_channels)} accessible channels:")
    for ch in accessible_channels:
        msg_status = "with messages" if ch['has_messages'] else "empty"
        print(f"   • {ch['name']} ({ch['type']}, {ch['member_count']} members, {msg_status})")
    
    # Process each channel
    print(f"\n🚀 Starting embedding process for {len(accessible_channels)} channels...")
    results = []
    
    for i, channel_info in enumerate(accessible_channels, 1):
        print(f"\n[{i}/{len(accessible_channels)}] Processing channel: {channel_info['name']}")
        
        if not channel_info['has_messages']:
            print("   ⏭️  Skipping empty channel")
            results.append({
                'channel': channel_info['name'],
                'status': 'skipped_empty'
            })
            continue
        
        result = await embed_channel_history(
            channel_info, embedding_service, slack_connector, data_processor
        )
        results.append(result)
        
        # Brief pause between channels to avoid overwhelming APIs
        await asyncio.sleep(1)
    
    # Summary report
    print(f"\n=== EMBEDDING COMPLETE ===")
    
    total_embedded = 0
    successful_channels = 0
    
    for result in results:
        if result['status'] == 'success':
            successful_channels += 1
            total_embedded += result['messages_embedded']
            print(f"✅ {result['channel']} ({result['channel_type']}): {result['messages_embedded']} messages embedded")
        elif result['status'] == 'skipped_empty':
            print(f"⏭️  {result['channel']}: Skipped (empty)")
        else:
            print(f"❌ {result['channel']}: Failed ({result.get('error', 'Unknown error')})")
    
    print(f"\n📈 FINAL RESULTS:")
    print(f"   Channels processed: {len(accessible_channels)}")
    print(f"   Successful embeddings: {successful_channels}")
    print(f"   Total messages embedded: {total_embedded}")
    
    if total_embedded > 0:
        print(f"\n🎉 SUCCESS! {total_embedded} messages now searchable in vector database")
        print("   You can now search conversations using the /admin/search-vectors endpoint")
    else:
        print(f"\n⚠️  No messages were embedded. Check channel access and message content.")

if __name__ == "__main__":
    asyncio.run(main())