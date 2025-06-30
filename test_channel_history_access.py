"""
Test if bot can read history from different types of channels without being invited.
"""

import asyncio
import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def test_channel_history_access():
    """Test different channels to see if bot can read history without being invited."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        print("=== TESTING CHANNEL HISTORY ACCESS WITHOUT INVITATION ===")
        
        # Get list of public channels
        conv_response = client.conversations_list(
            types="public_channel",
            exclude_archived=False,
            limit=100
        )
        
        channels = conv_response['channels']
        print(f"Found {len(channels)} public channels to test")
        
        accessible_channels = []
        test_count = 0
        max_tests = 20  # Test first 20 channels
        
        for channel in channels[:max_tests]:
            test_count += 1
            channel_id = channel['id']
            channel_name = channel['name']
            is_member = channel.get('is_member', False)
            member_count = channel.get('num_members', 0)
            
            print(f"\n{test_count}. Testing channel: {channel_name}")
            print(f"   ID: {channel_id}")
            print(f"   Bot is member: {is_member}")
            print(f"   Total members: {member_count}")
            
            # Test 1: Can we get channel info?
            try:
                info_response = client.conversations_info(channel=channel_id)
                print(f"   ✅ Channel info accessible")
            except SlackApiError as e:
                print(f"   ❌ Channel info failed: {e.response.get('error')}")
                continue
            
            # Test 2: Can we read message history?
            try:
                history_response = client.conversations_history(
                    channel=channel_id,
                    limit=1
                )
                
                if history_response['ok']:
                    messages = history_response['messages']
                    print(f"   ✅ HISTORY ACCESSIBLE: {len(messages)} messages")
                    
                    if messages:
                        latest_msg = messages[0]
                        print(f"   Latest message timestamp: {latest_msg['ts']}")
                        if 'text' in latest_msg:
                            preview = latest_msg['text'][:50].replace('\n', ' ')
                            print(f"   Message preview: {preview}...")
                        
                        accessible_channels.append({
                            'id': channel_id,
                            'name': channel_name,
                            'is_member': is_member,
                            'member_count': member_count,
                            'message_count': len(messages)
                        })
                    else:
                        print(f"   ⚠️  History accessible but no messages found")
                else:
                    print(f"   ❌ History failed: {history_response.get('error')}")
                    
            except SlackApiError as e:
                error_code = e.response.get('error')
                print(f"   ❌ History failed: {error_code}")
                
                if error_code == 'ratelimited':
                    print("   ⏸️  Rate limited, waiting...")
                    await asyncio.sleep(2)
            
            # Rate limiting
            await asyncio.sleep(0.2)
            
            # Stop if we found some accessible channels
            if len(accessible_channels) >= 3:
                print(f"\n✅ Found enough accessible channels, stopping early...")
                break
        
        print(f"\n=== RESULTS SUMMARY ===")
        print(f"Tested {test_count} channels")
        print(f"Found {len(accessible_channels)} channels with accessible history")
        
        if accessible_channels:
            print("\nChannels where bot CAN read history without being invited:")
            for ch in accessible_channels:
                membership_status = "MEMBER" if ch['is_member'] else "NOT MEMBER"
                print(f"  - {ch['name']} (ID: {ch['id']}) - {membership_status} - {ch['member_count']} members")
            
            return accessible_channels
        else:
            print("\n❌ NO channels found where bot can read history without being invited")
            print("\nThis confirms that:")
            print("1. channels:history permission requires bot membership or invitation")
            print("2. Bot cannot read history from arbitrary public channels")
            print("3. Bot must be explicitly added to target channel C087QKECFKQ")
            
            return []
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

async def test_specific_approach():
    """Try different API approaches to access channel history."""
    client = WebClient(token=settings.SLACK_BOT_TOKEN)
    target_channel = "C087QKECFKQ"
    
    print(f"\n=== TESTING SPECIFIC API APPROACHES FOR {target_channel} ===")
    
    # Approach 1: Basic conversations_history
    print("1. Basic conversations_history:")
    try:
        response = client.conversations_history(channel=target_channel, limit=1)
        print(f"   ✅ SUCCESS: {len(response['messages'])} messages")
    except SlackApiError as e:
        print(f"   ❌ FAILED: {e.response.get('error')}")
    
    # Approach 2: With include_all_metadata
    print("2. With include_all_metadata:")
    try:
        response = client.conversations_history(
            channel=target_channel, 
            limit=1,
            include_all_metadata=True
        )
        print(f"   ✅ SUCCESS: {len(response['messages'])} messages")
    except SlackApiError as e:
        print(f"   ❌ FAILED: {e.response.get('error')}")
    
    # Approach 3: Try conversations_replies (in case it's different)
    print("3. conversations_replies (if any threads exist):")
    try:
        # First try to get any message to get a timestamp
        response = client.conversations_history(channel=target_channel, limit=1)
        if response['messages']:
            ts = response['messages'][0]['ts']
            replies_response = client.conversations_replies(
                channel=target_channel,
                ts=ts
            )
            print(f"   ✅ SUCCESS: {len(replies_response['messages'])} replies")
    except SlackApiError as e:
        print(f"   ❌ FAILED: {e.response.get('error')}")
    
    # Approach 4: Check if search works
    print("4. Search messages in channel:")
    try:
        search_response = client.search_messages(
            query=f"in:#{target_channel}",
            count=1
        )
        if search_response['ok']:
            print(f"   ✅ SUCCESS: Found {len(search_response['messages']['matches'])} matches")
        else:
            print(f"   ❌ FAILED: {search_response.get('error')}")
    except SlackApiError as e:
        print(f"   ❌ FAILED: {e.response.get('error')}")
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")

if __name__ == "__main__":
    # Test if bot can access any channels without invitation
    accessible_channels = asyncio.run(test_channel_history_access())
    
    # Test specific approaches for target channel
    asyncio.run(test_specific_approach())
    
    if accessible_channels:
        print(f"\n🎉 GOOD NEWS: Found {len(accessible_channels)} accessible channels!")
        print("The bot CAN read history from some channels without invitation.")
    else:
        print(f"\n📋 CONCLUSION: Bot cannot read history from ANY channels without being invited.")
        print("This confirms that explicit invitation to C087QKECFKQ is required.")