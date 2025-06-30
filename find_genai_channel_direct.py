"""
Find genai-designsys channel using direct Slack API.
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from slack_sdk import WebClient
from config import settings

def find_genai_channel():
    """Find genai-designsys channel using direct API."""
    try:
        print("Searching for genai-designsys channel...")
        
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Get all conversations (channels)
        try:
            response = client.conversations_list(
                types="public_channel,private_channel",
                limit=1000
            )
            
            if not response['ok']:
                print(f"Error getting channels: {response.get('error')}")
                return None
                
            channels = response['channels']
            print(f"Found {len(channels)} total channels")
            
            # Look for genai-designsys or similar
            target_channel = None
            similar_channels = []
            
            for channel in channels:
                name = channel.get('name', '')
                
                # Exact match
                if name == 'genai-designsys':
                    target_channel = channel
                    break
                    
                # Similar matches
                if ('genai' in name.lower() and 'design' in name.lower()) or \
                   'genai-designsys' in name.lower():
                    similar_channels.append(channel)
            
            if target_channel:
                print(f"Found exact match: {target_channel['name']} (ID: {target_channel['id']})")
                channel_to_test = target_channel
            elif similar_channels:
                print("Found similar channels:")
                for ch in similar_channels:
                    print(f"  {ch['name']} (ID: {ch['id']})")
                channel_to_test = similar_channels[0]  # Use first match
                print(f"Using: {channel_to_test['name']} (ID: {channel_to_test['id']})")
            else:
                # Show any channels with 'genai' or 'design'
                genai_related = []
                for channel in channels:
                    name = channel.get('name', '')
                    if 'genai' in name.lower() or 'design' in name.lower():
                        genai_related.append(f"  {name} (ID: {channel['id']})")
                
                print("No exact match found. Related channels:")
                for ch in genai_related[:10]:
                    print(ch)
                return None
            
            # Test access to the found channel
            channel_id = channel_to_test['id']
            channel_name = channel_to_test['name']
            
            print(f"\nTesting access to {channel_name} ({channel_id})...")
            time.sleep(1)  # Rate limit protection
            
            try:
                response = client.conversations_history(
                    channel=channel_id,
                    limit=3
                )
                
                if response['ok']:
                    messages = response['messages']
                    print(f"✅ Bot has access! Found {len(messages)} recent messages")
                    
                    if messages:
                        sample_msg = messages[0]
                        print(f"   Sample message from: {sample_msg.get('user', 'unknown')}")
                        print(f"   Text preview: {sample_msg.get('text', 'No text')[:50]}...")
                    
                    return {
                        'id': channel_id,
                        'name': channel_name,
                        'accessible': True,
                        'message_count': len(messages)
                    }
                else:
                    error = response.get('error', 'unknown')
                    print(f"❌ Bot cannot access channel: {error}")
                    
                    if error == 'not_in_channel':
                        print("   Bot needs to be added to this channel")
                    
                    return {
                        'id': channel_id,
                        'name': channel_name,
                        'accessible': False,
                        'error': error
                    }
                    
            except Exception as e:
                print(f"❌ Error testing channel access: {e}")
                return {
                    'id': channel_id,
                    'name': channel_name,
                    'accessible': False,
                    'error': str(e)
                }
                
        except Exception as e:
            print(f"Error getting channel list: {e}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    result = find_genai_channel()
    
    if result:
        if result['accessible']:
            print(f"\n🎉 Ready to embed {result['name']} ({result['id']})")
            print(f"   Channel has {result.get('message_count', 0)} recent messages visible")
        else:
            print(f"\n⚠️  Found {result['name']} but bot needs access")
            print(f"   Error: {result.get('error', 'unknown')}")
            print(f"   Solution: Add bot to #{result['name']} channel")
    else:
        print("\n❌ Could not find genai-designsys channel")