"""
Test script to find channels with accessible message history for testing the embedding pipeline.
"""

import asyncio
import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def find_accessible_channels():
    """Find channels where the bot can actually read message history."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        print("Finding channels with accessible message history...")
        
        # Get all channels
        conv_response = client.conversations_list(types="public_channel,private_channel")
        channels = conv_response['channels']
        print(f"Found {len(channels)} total channels")
        
        accessible_channels = []
        
        # Test message access for each channel
        for i, channel in enumerate(channels[:20]):  # Test first 20 channels
            channel_id = channel['id']
            channel_name = channel['name']
            
            print(f"\n{i+1}. Testing {channel_name} (ID: {channel_id})")
            print(f"   Is member: {channel.get('is_member', False)}")
            print(f"   Is private: {channel.get('is_private', False)}")
            
            try:
                # Try to get recent messages (limit 1 to minimize API calls)
                history_response = client.conversations_history(
                    channel=channel_id,
                    limit=1
                )
                
                if history_response['ok']:
                    messages = history_response['messages']
                    accessible_channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'message_count': len(messages),
                        'is_member': channel.get('is_member', False),
                        'latest_message_ts': messages[0]['ts'] if messages else None
                    })
                    print(f"   ✅ ACCESSIBLE - {len(messages)} message(s) found")
                    
                    if messages and len(messages) > 0:
                        msg = messages[0]
                        preview = msg.get('text', '')[:100]
                        print(f"   Preview: {preview}...")
                else:
                    print(f"   ❌ Failed: {history_response.get('error', 'unknown')}")
                    
            except SlackApiError as e:
                error = e.response.get('error', 'unknown')
                print(f"   ❌ API Error: {error}")
                
                # If not in channel, try to join (but we know this will fail)
                if error == 'not_in_channel':
                    print(f"   (Bot not member of this channel)")
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        print(f"\n=== SUMMARY ===")
        print(f"Accessible channels: {len(accessible_channels)}")
        
        if accessible_channels:
            print("\nChannels with message access:")
            for ch in accessible_channels[:10]:  # Show top 10
                print(f"  - {ch['name']} (ID: {ch['id']}) - {ch['message_count']} messages")
            
            # Pick the best channel for testing
            best_channel = accessible_channels[0]
            print(f"\nRecommended channel for testing:")
            print(f"  Channel: {best_channel['name']} (ID: {best_channel['id']})")
            print(f"  Message count: {best_channel['message_count']}")
            
        else:
            print("\nNo channels with accessible message history found.")
            print("The bot may need to be added to specific channels or")
            print("additional OAuth permissions may be required.")
        
        return accessible_channels
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

if __name__ == "__main__":
    asyncio.run(find_accessible_channels())