"""
Find the genai-designsys channel ID and check bot access.
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.slack_connector import SlackConnector

async def find_genai_channel():
    """Find genai-designsys channel and check access."""
    try:
        print("Finding genai-designsys channel...")
        
        slack_connector = SlackConnector()
        
        # Get all channels
        channels = await slack_connector.get_all_channels()
        
        # Look for genai-designsys
        target_channel = None
        for channel in channels:
            name = channel.get('name', '')
            if 'genai' in name.lower() and 'design' in name.lower():
                target_channel = channel
                print(f"Found channel: {name} (ID: {channel['id']})")
                break
        
        if not target_channel:
            # Also check for similar names
            genai_channels = []
            for channel in channels:
                name = channel.get('name', '')
                if 'genai' in name.lower() or 'design' in name.lower():
                    genai_channels.append(f"  {name} (ID: {channel['id']})")
            
            print("genai-designsys not found exactly. Similar channels:")
            for ch in genai_channels[:10]:  # Show first 10
                print(ch)
            return None
        
        # Test access to the channel
        channel_id = target_channel['id']
        channel_name = target_channel['name']
        
        print(f"\nTesting access to {channel_name} ({channel_id})...")
        
        try:
            # Try to get recent messages
            from slack_sdk import WebClient
            from config import settings
            
            client = WebClient(token=settings.SLACK_BOT_TOKEN)
            
            response = client.conversations_history(
                channel=channel_id,
                limit=1
            )
            
            if response['ok']:
                messages = response['messages']
                print(f"✅ Bot has access! Found {len(messages)} recent messages")
                return {
                    'id': channel_id,
                    'name': channel_name,
                    'accessible': True
                }
            else:
                error = response.get('error', 'unknown')
                print(f"❌ Bot cannot access channel: {error}")
                return {
                    'id': channel_id,
                    'name': channel_name,
                    'accessible': False,
                    'error': error
                }
                
        except Exception as e:
            print(f"❌ Error testing access: {e}")
            return {
                'id': channel_id,
                'name': channel_name,
                'accessible': False,
                'error': str(e)
            }
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(find_genai_channel())
    
    if result:
        if result['accessible']:
            print(f"\n🎉 Ready to embed {result['name']} ({result['id']})")
        else:
            print(f"\n⚠️  Found {result['name']} but bot needs access")
            print(f"   Error: {result.get('error', 'unknown')}")
    else:
        print("\n❌ Could not find genai-designsys channel")