"""
Check bot membership status in channels.
"""

import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

def check_membership():
    """Check bot membership in channels."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        print("=== BOT MEMBERSHIP ANALYSIS ===")
        
        # Get bot info
        auth_response = client.auth_test()
        bot_user_id = auth_response['user_id']
        print(f"Bot ID: {bot_user_id}")
        print(f"Bot Name: {auth_response['user']}")
        
        # Get all conversations
        print("\nScanning all channels...")
        conv_response = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=False,
            limit=500
        )
        
        channels = conv_response['channels']
        print(f"Total channels visible: {len(channels)}")
        
        # Analyze membership
        member_channels = []
        accessible_channels = []
        
        for channel in channels:
            channel_id = channel['id']
            channel_name = channel['name']
            is_member = channel.get('is_member', False)
            is_private = channel.get('is_private', False)
            member_count = channel.get('num_members', 0)
            
            if is_member:
                member_channels.append(channel)
                
                # Test actual message access
                try:
                    history = client.conversations_history(channel=channel_id, limit=1)
                    if history['ok']:
                        messages = history['messages']
                        accessible_channels.append({
                            'id': channel_id,
                            'name': channel_name,
                            'type': 'private' if is_private else 'public',
                            'member_count': member_count,
                            'has_messages': len(messages) > 0
                        })
                except SlackApiError as e:
                    print(f"History access failed for {channel_name}: {e.response.get('error')}")
        
        print(f"\nChannels where bot is member: {len(member_channels)}")
        if member_channels:
            for ch in member_channels:
                ch_type = 'private' if ch.get('is_private') else 'public'
                print(f"  - {ch['name']} ({ch_type}, {ch.get('num_members', 0)} members)")
        
        print(f"\nChannels with message access: {len(accessible_channels)}")
        if accessible_channels:
            for ch in accessible_channels:
                msg_status = "with messages" if ch['has_messages'] else "empty"
                print(f"  - {ch['name']} ({ch['type']}, {ch['member_count']} members, {msg_status})")
        
        # Check specific channels mentioned
        target_channels = ["C087QKECFKQ", "autopilot-design-patterns"]
        print(f"\nChecking specific target channels:")
        
        for target in target_channels:
            found = False
            for ch in channels:
                if ch['id'] == target or ch['name'] == target:
                    found = True
                    is_member = ch.get('is_member', False)
                    is_private = ch.get('is_private', False)
                    member_count = ch.get('num_members', 0)
                    
                    print(f"  {ch['name']} ({ch['id']}):")
                    print(f"    Type: {'private' if is_private else 'public'}")
                    print(f"    Bot is member: {is_member}")
                    print(f"    Member count: {member_count}")
                    
                    # Test history access
                    try:
                        history = client.conversations_history(channel=ch['id'], limit=1)
                        if history['ok']:
                            messages = history['messages']
                            print(f"    History accessible: Yes ({len(messages)} messages in latest call)")
                        else:
                            print(f"    History accessible: No ({history.get('error')})")
                    except SlackApiError as e:
                        print(f"    History accessible: No ({e.response.get('error')})")
                    break
            
            if not found:
                print(f"  {target}: Not found in bot's channel list")
        
        if len(accessible_channels) == 0:
            print(f"\n❌ ISSUE: Bot is not a member of any channels with message access")
            print(f"To add bot to channels, use these commands in the target channels:")
            print(f"  /invite @{auth_response['user']}")
            print(f"  or")
            print(f"  /add @{auth_response['user']}")
        else:
            print(f"\n✅ Bot has access to {len(accessible_channels)} channels")
            return accessible_channels
            
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    accessible = check_membership()
    
    if accessible:
        print(f"\nReady to embed {len(accessible)} channels!")
        for ch in accessible:
            if ch['has_messages']:
                print(f"  • {ch['name']} ({ch['type']}) - ready for embedding")
    else:
        print(f"\nNo channels ready for embedding. Add bot to channels first.")