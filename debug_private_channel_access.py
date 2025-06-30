"""
Debug script to understand private channel invitation limitations.
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

async def debug_private_channel_access():
    """Debug private channel access and invitation capabilities."""
    try:
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        print("=== DEBUGGING PRIVATE CHANNEL INVITATION LIMITATIONS ===")
        
        # 1. Check bot permissions and scopes
        print("\n1. Bot Authentication & Scopes:")
        auth_response = client.auth_test()
        print(f"   Bot User: {auth_response['user']}")
        print(f"   Bot ID: {auth_response['user_id']}")
        print(f"   Team: {auth_response['team']}")
        
        # 2. Get bot user info to see detailed permissions
        print("\n2. Bot User Details:")
        try:
            bot_info = client.users_info(user=auth_response['user_id'])
            if bot_info['ok']:
                user = bot_info['user']
                print(f"   Real Name: {user.get('real_name', 'N/A')}")
                print(f"   Is Bot: {user.get('is_bot', 'N/A')}")
                print(f"   Is App User: {user.get('is_app_user', 'N/A')}")
                print(f"   Team ID: {user.get('team_id', 'N/A')}")
                
                # Check if there are any restrictions
                if 'profile' in user:
                    profile = user['profile']
                    print(f"   Bot Profile: {profile.get('bot_id', 'N/A')}")
                    
        except SlackApiError as e:
            print(f"   ❌ Bot info failed: {e.response.get('error')}")
        
        # 3. Test access to private channels
        print("\n3. Private Channel Visibility:")
        try:
            # Get all conversations including private channels
            conv_response = client.conversations_list(
                types="private_channel",
                exclude_archived=False,
                limit=50
            )
            
            private_channels = conv_response['channels']
            print(f"   Private channels visible: {len(private_channels)}")
            
            if private_channels:
                print("   Sample private channels:")
                for i, channel in enumerate(private_channels[:5]):
                    is_member = channel.get('is_member', False)
                    member_status = "MEMBER" if is_member else "NOT MEMBER"
                    print(f"     - {channel['name']} ({channel['id']}) - {member_status}")
            else:
                print("   ❌ No private channels visible to bot")
                
        except SlackApiError as e:
            print(f"   ❌ Private channel list failed: {e.response.get('error')}")
        
        # 4. Test what happens when trying to join a private channel
        print("\n4. Testing Private Channel Join Capabilities:")
        
        # First, let's see if we can get info about any private channel
        try:
            # Try to get a list of all channels to find a private one
            all_convs = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=False,
                limit=200
            )
            
            # Find a private channel that bot is not a member of
            test_private_channel = None
            for channel in all_convs['channels']:
                if channel.get('is_private', False) and not channel.get('is_member', False):
                    test_private_channel = channel
                    break
            
            if test_private_channel:
                channel_id = test_private_channel['id']
                channel_name = test_private_channel['name']
                
                print(f"   Testing with private channel: {channel_name} ({channel_id})")
                
                # Test 1: Can we get channel info?
                try:
                    info_response = client.conversations_info(channel=channel_id)
                    print(f"   ✅ Channel info accessible")
                except SlackApiError as e:
                    print(f"   ❌ Channel info failed: {e.response.get('error')}")
                
                # Test 2: Can we join the private channel?
                try:
                    join_response = client.conversations_join(channel=channel_id)
                    if join_response['ok']:
                        print(f"   ✅ Successfully joined private channel")
                    else:
                        print(f"   ❌ Join failed: {join_response.get('error')}")
                except SlackApiError as e:
                    error = e.response.get('error')
                    print(f"   ❌ Join failed: {error}")
                    
                    # Explain common errors
                    if error == 'channel_not_found':
                        print("     → Bot cannot see this private channel")
                    elif error == 'is_archived':
                        print("     → Channel is archived")
                    elif error == 'not_authed':
                        print("     → Bot lacks permission to join private channels")
                    elif error == 'access_denied':
                        print("     → Workspace admin has restricted bot access to private channels")
                    elif error == 'method_not_supported_for_channel_type':
                        print("     → Bots cannot self-join private channels")
            else:
                print("   ℹ️  No private channels found that bot is not already a member of")
                
        except SlackApiError as e:
            print(f"   ❌ Channel listing failed: {e.response.get('error')}")
        
        # 5. Check OAuth scopes in detail
        print("\n5. OAuth Scope Analysis:")
        
        # Try to determine what scopes the bot actually has
        scope_tests = {
            'channels:read': lambda: client.conversations_list(types="public_channel", limit=1),
            'groups:read': lambda: client.conversations_list(types="private_channel", limit=1),
            'groups:history': lambda: client.conversations_list(types="private_channel", limit=1),
            'channels:history': lambda: client.conversations_list(types="public_channel", limit=1),
            'users:read': lambda: client.users_list(limit=1),
            'team:read': lambda: client.team_info(),
        }
        
        for scope, test_func in scope_tests.items():
            try:
                test_func()
                print(f"   ✅ {scope}: Available")
            except SlackApiError as e:
                error = e.response.get('error')
                if error == 'missing_scope':
                    print(f"   ❌ {scope}: Missing")
                elif error == 'not_authed':
                    print(f"   ❌ {scope}: Not authorized")
                else:
                    print(f"   ⚠️  {scope}: Uncertain ({error})")
            except Exception as e:
                print(f"   ⚠️  {scope}: Test error ({e})")
        
        # 6. Workspace-level restrictions analysis
        print("\n6. Potential Workspace Restrictions:")
        print("   Common reasons bots cannot join private channels:")
        print("   • Missing 'groups:read' or 'groups:write' OAuth scopes")
        print("   • Workspace admin disabled bot access to private channels")
        print("   • Bot app not approved for private channel access")
        print("   • Enterprise Grid restrictions")
        print("   • Bot was installed with limited permissions")
        
        print("\n=== SOLUTION RECOMMENDATIONS ===")
        print("To enable private channel access:")
        print("1. Check Slack app OAuth scopes in app management")
        print("2. Ensure 'groups:read', 'groups:write', 'groups:history' are enabled")
        print("3. Reinstall bot with updated permissions")
        print("4. Contact workspace admin to verify bot permissions")
        print("5. Check if workspace has Enterprise Grid restrictions")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_private_channel_access())