"""
Quick script to find accessible channels and embed their history.
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

async def quick_embed():
    """Quickly find and embed accessible channels."""
    try:
        print("Starting quick embed process...")
        
        # Initialize Slack client
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Get conversations where bot is a member
        print("Finding accessible channels...")
        conv_response = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=False,
            limit=100
        )
        
        accessible_channels = []
        for channel in conv_response['channels']:
            if channel.get('is_member', False):
                channel_id = channel['id']
                channel_name = channel['name']
                is_private = channel.get('is_private', False)
                
                # Quick test for message access
                try:
                    history = client.conversations_history(channel=channel_id, limit=1)
                    if history['ok'] and history['messages']:
                        accessible_channels.append({
                            'id': channel_id,
                            'name': channel_name,
                            'type': 'private' if is_private else 'public'
                        })
                        channel_type = 'private' if is_private else 'public'
                        print(f"  Found: {channel_name} ({channel_type})")
                except SlackApiError:
                    continue
        
        print(f"\nFound {len(accessible_channels)} accessible channels with messages")
        
        if not accessible_channels:
            print("No accessible channels found. Make sure bot is added to channels.")
            return
        
        # Initialize embedding services
        print("Initializing embedding services...")
        embedding_service = EmbeddingService()
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        
        # Process each channel
        total_embedded = 0
        for i, channel in enumerate(accessible_channels, 1):
            channel_id = channel['id']
            channel_name = channel['name']
            channel_type = channel['type']
            
            print(f"\n[{i}/{len(accessible_channels)}] Processing {channel_name} ({channel_type})...")
            
            try:
                # Extract messages from last year
                end_time = datetime.now()
                start_time = end_time - timedelta(days=365)
                
                print(f"  Extracting messages...")
                raw_messages = await slack_connector.extract_channel_messages(
                    channel_id=channel_id,
                    start_time=start_time,
                    end_time=end_time,
                    batch_size=100
                )
                
                if not raw_messages:
                    print(f"  No messages found in date range")
                    continue
                
                print(f"  Extracted {len(raw_messages)} messages")
                
                # Process messages
                print(f"  Processing messages...")
                processed_messages = await data_processor.process_messages(raw_messages)
                print(f"  Processed {len(processed_messages)} messages")
                
                # Embed and store
                print(f"  Embedding and storing...")
                embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
                print(f"  Embedded {embedded_count} messages successfully")
                
                total_embedded += embedded_count
                
            except Exception as e:
                print(f"  Error processing {channel_name}: {e}")
                continue
        
        print(f"\n=== EMBEDDING COMPLETE ===")
        print(f"Channels processed: {len(accessible_channels)}")
        print(f"Total messages embedded: {total_embedded}")
        
        if total_embedded > 0:
            print(f"\nSuccess! {total_embedded} messages are now searchable in the vector database.")
            print("You can test search with: curl -X POST 'http://localhost:5000/admin/search-vectors?query=test'")
        else:
            print("No messages were embedded. Check channel access and content.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(quick_embed())