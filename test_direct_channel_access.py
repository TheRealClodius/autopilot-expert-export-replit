"""
Test direct access to autopilot-design-patterns channel.
"""

import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import settings

def test_direct_access():
    """Test direct access to specific channel."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Try multiple channel identifiers
        channel_identifiers = [
            "C087QKECFKQ",  # Channel ID
            "autopilot-design-patterns",  # Channel name
            "#autopilot-design-patterns"  # With hash
        ]
        
        print("=== TESTING DIRECT CHANNEL ACCESS ===")
        
        for channel_id in channel_identifiers:
            print(f"\nTesting channel: {channel_id}")
            
            # Test 1: Channel info
            try:
                info_response = client.conversations_info(channel=channel_id)
                if info_response['ok']:
                    channel = info_response['channel']
                    print(f"  ✅ Channel info accessible")
                    print(f"     Name: {channel['name']}")
                    print(f"     ID: {channel['id']}")
                    print(f"     Is Member: {channel.get('is_member', False)}")
                    print(f"     Is Private: {channel.get('is_private', False)}")
                    print(f"     Members: {channel.get('num_members', 0)}")
                    
                    # Test 2: Message history
                    try:
                        history_response = client.conversations_history(
                            channel=channel['id'],
                            limit=5
                        )
                        if history_response['ok']:
                            messages = history_response['messages']
                            print(f"  ✅ HISTORY ACCESSIBLE: {len(messages)} messages")
                            
                            if messages:
                                print(f"     Latest message timestamp: {messages[0]['ts']}")
                                if 'text' in messages[0]:
                                    preview = messages[0]['text'][:100].replace('\n', ' ')
                                    print(f"     Message preview: {preview}...")
                                
                                # SUCCESS - Channel is accessible
                                return {
                                    'accessible': True,
                                    'channel_id': channel['id'],
                                    'channel_name': channel['name'],
                                    'message_count': len(messages)
                                }
                            else:
                                print(f"  ⚠️  History accessible but no messages found")
                        else:
                            print(f"  ❌ History failed: {history_response.get('error')}")
                    except SlackApiError as e:
                        print(f"  ❌ History error: {e.response.get('error')}")
                        
                else:
                    print(f"  ❌ Channel info failed: {info_response.get('error')}")
            except SlackApiError as e:
                print(f"  ❌ Channel info error: {e.response.get('error')}")
        
        return {'accessible': False}
        
    except Exception as e:
        print(f"Error: {e}")
        return {'accessible': False}

if __name__ == "__main__":
    result = test_direct_access()
    
    if result['accessible']:
        print(f"\n🎉 SUCCESS! Channel {result['channel_name']} is accessible")
        print(f"   Channel ID: {result['channel_id']}")
        print(f"   Messages available: {result['message_count']}")
        print(f"\nReady to embed all conversation history!")
    else:
        print(f"\n❌ Channel not accessible yet")
        print(f"The app installation may need a few minutes to take effect")
        print(f"Try again in 2-3 minutes or check that the bot was added correctly")