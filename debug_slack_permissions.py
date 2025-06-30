"""
Debug script to understand exact Slack API permissions and behavior.
"""

import asyncio
import sys
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

async def debug_slack_api():
    """Debug exact Slack API behavior for channel access."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        target_channel = "C087QKECFKQ"
        
        print("=== DEBUGGING SLACK API PERMISSIONS ===")
        
        # 1. Get auth info
        print("\n1. Bot Authentication Info:")
        auth_response = client.auth_test()
        print(f"   User: {auth_response['user']}")
        print(f"   User ID: {auth_response['user_id']}")
        print(f"   Team: {auth_response['team']}")
        print(f"   Team ID: {auth_response['team_id']}")
        
        # 2. Test channel info access
        print(f"\n2. Channel Info for {target_channel}:")
        try:
            info_response = client.conversations_info(channel=target_channel)
            if info_response['ok']:
                channel = info_response['channel']
                print(f"   Name: {channel['name']}")
                print(f"   Is Private: {channel.get('is_private', 'unknown')}")
                print(f"   Is Member: {channel.get('is_member', 'unknown')}")
                print(f"   Is Archived: {channel.get('is_archived', 'unknown')}")
                print(f"   Created: {channel.get('created', 'unknown')}")
                print(f"   Purpose: {channel.get('purpose', {}).get('value', 'No purpose')}")
        except SlackApiError as e:
            print(f"   ❌ Channel info failed: {e.response.get('error')}")
        
        # 3. Test conversations_list to see if channel appears
        print(f"\n3. Checking if {target_channel} appears in conversations list:")
        try:
            conv_response = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=False,
                limit=1000
            )
            channels = conv_response['channels']
            
            target_found = False
            for channel in channels:
                if channel['id'] == target_channel:
                    target_found = True
                    print(f"   ✅ Found in list: {channel['name']}")
                    print(f"   Is Member: {channel.get('is_member', False)}")
                    print(f"   Is Private: {channel.get('is_private', False)}")
                    print(f"   Is Archived: {channel.get('is_archived', False)}")
                    break
            
            if not target_found:
                print(f"   ❌ {target_channel} NOT found in conversations list")
                print(f"   Total channels visible: {len(channels)}")
        except SlackApiError as e:
            print(f"   ❌ Conversations list failed: {e.response.get('error')}")
        
        # 4. Try direct history access with different parameters
        print(f"\n4. Testing conversations_history with different approaches:")
        
        # Approach A: Basic call
        print("   Approach A: Basic conversations_history")
        try:
            history_response = client.conversations_history(
                channel=target_channel,
                limit=1
            )
            if history_response['ok']:
                messages = history_response['messages']
                print(f"   ✅ SUCCESS: {len(messages)} messages retrieved")
                if messages:
                    msg = messages[0]
                    print(f"   Latest message: {msg.get('ts')} - {msg.get('text', '')[:50]}...")
            else:
                print(f"   ❌ Failed: {history_response.get('error')}")
        except SlackApiError as e:
            print(f"   ❌ Exception: {e.response.get('error')}")
        
        # Approach B: With oldest parameter (wide range)
        print("   Approach B: With wide time range")
        try:
            history_response = client.conversations_history(
                channel=target_channel,
                limit=5,
                oldest="0",  # From beginning of time
                latest="9999999999"  # Far future
            )
            if history_response['ok']:
                messages = history_response['messages']
                print(f"   ✅ SUCCESS: {len(messages)} messages retrieved")
            else:
                print(f"   ❌ Failed: {history_response.get('error')}")
        except SlackApiError as e:
            print(f"   ❌ Exception: {e.response.get('error')}")
        
        # Approach C: Without time filters 
        print("   Approach C: No time filters, just recent")
        try:
            history_response = client.conversations_history(
                channel=target_channel,
                limit=10
            )
            if history_response['ok']:
                messages = history_response['messages']
                print(f"   ✅ SUCCESS: {len(messages)} messages retrieved")
                if messages:
                    print(f"   Message timestamps: {[m.get('ts') for m in messages[:3]]}")
            else:
                print(f"   ❌ Failed: {history_response.get('error')}")
        except SlackApiError as e:
            print(f"   ❌ Exception: {e.response.get('error')}")
        
        # 5. Check bot's current permissions in detail
        print(f"\n5. Detailed Permission Analysis:")
        try:
            # Try to get more info about the bot token permissions
            # Some tokens provide scope info in auth response
            if 'response_metadata' in auth_response:
                print(f"   Response metadata: {auth_response['response_metadata']}")
                
            # Look for any scope or permission information
            print("   Checking for additional permission details...")
            
            # Check if bot has access to users.list
            try:
                users_response = client.users_list(limit=1)
                print("   ✅ users:read permission confirmed")
            except:
                print("   ❌ users:read permission not available")
                
            # Check if bot can access team info
            try:
                team_response = client.team_info()
                print("   ✅ team:read permission confirmed")
            except:
                print("   ❌ team:read permission not available")
                
        except Exception as e:
            print(f"   Error checking permissions: {e}")
        
        print(f"\n=== DIAGNOSIS ===")
        print("If channel info is accessible but history is not:")
        print("- The bot might need to be explicitly added to the channel")
        print("- Channel might be private/restricted despite having channels:history")
        print("- There might be workspace-level restrictions")
        
        print("\nIf channel doesn't appear in conversations_list:")
        print("- Bot might not have visibility to this specific channel")
        print("- Channel might be archived or deleted")
        print("- Additional scopes might be needed")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_slack_api())