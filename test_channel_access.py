"""
Test script to check what Slack data is accessible with current bot permissions.
"""

import asyncio
import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def test_slack_access():
    """Test various Slack API endpoints to see what data is accessible."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        print("Testing Slack API access with current bot permissions...")
        
        # Test 1: Basic auth test
        print("\n1. Testing auth...")
        try:
            auth_response = client.auth_test()
            print(f"✅ Auth successful: {auth_response['user']} in team {auth_response['team']}")
            bot_user_id = auth_response['user_id']
            print(f"   Bot User ID: {bot_user_id}")
        except SlackApiError as e:
            print(f"❌ Auth failed: {e}")
            return
        
        # Test 2: List conversations/channels
        print("\n2. Testing conversations list...")
        try:
            conv_response = client.conversations_list(types="public_channel,private_channel")
            channels = conv_response['channels']
            print(f"✅ Found {len(channels)} accessible channels")
            
            # Look for our target channel
            target_channel = None
            for channel in channels:
                if channel['id'] == 'C087QKECFKQ':
                    target_channel = channel
                    print(f"   Found target channel: {channel['name']} (ID: {channel['id']})")
                    print(f"   Channel info: is_member={channel.get('is_member', False)}, is_private={channel.get('is_private', False)}")
                    break
            
            if not target_channel:
                print("   Target channel C087QKECFKQ not found in accessible channels")
                print("   Available channels:")
                for channel in channels[:5]:  # Show first 5
                    print(f"     - {channel['name']} (ID: {channel['id']}) - member: {channel.get('is_member', False)}")
                    
        except SlackApiError as e:
            print(f"❌ Conversations list failed: {e}")
        
        # Test 3: Direct channel info
        print("\n3. Testing direct channel info...")
        try:
            channel_info = client.conversations_info(channel="C087QKECFKQ")
            if channel_info['ok']:
                channel = channel_info['channel']
                print(f"✅ Channel info accessible: {channel['name']}")
                print(f"   Members: {channel.get('num_members', 'unknown')}")
                print(f"   Is member: {channel.get('is_member', False)}")
                print(f"   Is private: {channel.get('is_private', False)}")
        except SlackApiError as e:
            print(f"❌ Channel info failed: {e}")
        
        # Test 4: Try conversations_history with different approaches
        print("\n4. Testing message history access...")
        try:
            # Method A: Direct history call
            history_response = client.conversations_history(
                channel="C087QKECFKQ",
                limit=5
            )
            if history_response['ok']:
                messages = history_response['messages']
                print(f"✅ Direct history access successful: {len(messages)} messages")
                if messages:
                    latest_msg = messages[0]
                    print(f"   Latest message timestamp: {latest_msg.get('ts', 'unknown')}")
                    print(f"   Message preview: {latest_msg.get('text', '')[:100]}...")
            else:
                print(f"❌ Direct history failed: {history_response.get('error', 'unknown')}")
                
        except SlackApiError as e:
            print(f"❌ History access failed: {e}")
            
            # Method B: Try to join first
            print("   Attempting to join channel...")
            try:
                join_response = client.conversations_join(channel="C087QKECFKQ")
                if join_response['ok']:
                    print("   ✅ Successfully joined channel")
                    
                    # Try history again
                    history_response = client.conversations_history(
                        channel="C087QKECFKQ",
                        limit=5
                    )
                    if history_response['ok']:
                        messages = history_response['messages']
                        print(f"   ✅ History after join: {len(messages)} messages")
                    else:
                        print(f"   ❌ History still failed: {history_response.get('error', 'unknown')}")
                else:
                    print(f"   ❌ Join failed: {join_response.get('error', 'unknown')}")
            except SlackApiError as join_error:
                print(f"   ❌ Join attempt failed: {join_error}")
        
        # Test 5: Check bot permissions/scopes  
        print("\n5. Testing bot permissions...")
        try:
            # This might not work with all bot tokens, but worth trying
            scopes_response = client.auth_test()
            print(f"   Response keys: {list(scopes_response.keys())}")
        except Exception as e:
            print(f"   Scope check not available: {e}")
        
        print("\n=== Summary ===")
        print("If all tests passed, channel data ingestion should work.")
        print("If history access failed, additional OAuth scopes may be needed:")
        print("  - channels:history (read messages from public channels)")
        print("  - channels:read (list public channels)")
        print("  - channels:join (join public channels)")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_slack_access())