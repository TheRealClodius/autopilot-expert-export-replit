"""
Test access to design-related channels and look for genai content.
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from slack_sdk import WebClient
from config import settings

def test_design_channels():
    """Test access to design-related channels."""
    try:
        print("Testing access to design-related channels...")
        
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Channels that might contain genai design system content
        candidate_channels = [
            {'name': 'design-system-development', 'id': 'CN5H7K04T'},
            {'name': 'team-product-design', 'id': 'CMA54SH0Q'},
            {'name': 'team-webproductdesign', 'id': 'CMJ5789A9'}
        ]
        
        accessible_channels = []
        
        for channel in candidate_channels:
            channel_id = channel['id']
            channel_name = channel['name']
            
            print(f"\nTesting {channel_name} ({channel_id})...")
            time.sleep(1)  # Rate limit protection
            
            try:
                response = client.conversations_history(
                    channel=channel_id,
                    limit=10
                )
                
                if response['ok']:
                    messages = response['messages']
                    print(f"  ✅ Access granted! {len(messages)} recent messages")
                    
                    # Check if any messages mention genai or AI
                    genai_mentions = 0
                    for msg in messages:
                        text = msg.get('text', '').lower()
                        if 'genai' in text or 'gen ai' in text or 'generative ai' in text:
                            genai_mentions += 1
                    
                    if genai_mentions > 0:
                        print(f"  🤖 Found {genai_mentions} messages mentioning GenAI!")
                    
                    accessible_channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'message_count': len(messages),
                        'genai_mentions': genai_mentions
                    })
                    
                else:
                    error = response.get('error', 'unknown')
                    print(f"  ❌ No access: {error}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Also search for private channels or groups
        print(f"\nChecking for private groups with 'genai' in name...")
        time.sleep(1)
        
        try:
            # Get private channels
            response = client.conversations_list(
                types="private_channel,mpim,im",
                limit=1000
            )
            
            if response['ok']:
                private_channels = response['channels']
                genai_privates = []
                
                for channel in private_channels:
                    name = channel.get('name', '')
                    if 'genai' in name.lower() or 'gen-ai' in name.lower():
                        genai_privates.append(channel)
                
                if genai_privates:
                    print(f"Found {len(genai_privates)} private channels with 'genai':")
                    for ch in genai_privates:
                        print(f"  {ch['name']} (ID: {ch['id']})")
                else:
                    print("No private channels with 'genai' found")
                    
        except Exception as e:
            print(f"Error checking private channels: {e}")
        
        # Summary
        print(f"\n=== SUMMARY ===")
        if accessible_channels:
            print("Accessible design channels:")
            for ch in accessible_channels:
                genai_note = f" ({ch['genai_mentions']} GenAI mentions)" if ch['genai_mentions'] > 0 else ""
                print(f"  ✅ {ch['name']} - {ch['message_count']} messages{genai_note}")
            
            # Recommend best channel
            best_channel = max(accessible_channels, key=lambda x: x['genai_mentions'])
            if best_channel['genai_mentions'] > 0:
                print(f"\n🎯 RECOMMENDATION: Use {best_channel['name']} (ID: {best_channel['id']})")
                print(f"   This channel has GenAI content and is accessible")
                return best_channel
            else:
                print(f"\n💡 SUGGESTION: Use {accessible_channels[0]['name']} (ID: {accessible_channels[0]['id']})")
                print(f"   No GenAI content found, but this design channel is accessible")
                return accessible_channels[0]
        else:
            print("❌ No accessible design channels found")
            print("   Bot needs to be added to design channels first")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    result = test_design_channels()
    
    if result:
        print(f"\n🚀 Ready to embed: #{result['name']} (ID: {result['id']})")
    else:
        print(f"\n⚠️  No suitable channels found for embedding")