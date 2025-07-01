#!/usr/bin/env python3
"""
Test the AtlassianToolbelt class directly
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.atlassian_guru import AtlassianToolbelt

async def test_toolbelt():
    """Test AtlassianToolbelt functionality"""
    
    print("🔧 Testing AtlassianToolbelt...")
    
    try:
        # Initialize toolbelt
        async with AtlassianToolbelt() as toolbelt:
            print("\n1. Getting capabilities...")
            capabilities = await toolbelt.get_capabilities()
            print(f"   Available tools: {capabilities.get('available_tools', [])}")
            print(f"   Server URL: {capabilities.get('server_url')}")
            print(f"   Has dynamic prompt: {capabilities.get('has_dynamic_prompt')}")
            
            # Test health check
            print("\n2. Health check...")
            health = await toolbelt.health_check()
            print(f"   Health status: {'✅ Healthy' if health else '❌ Unhealthy'}")
            
            # Test task execution
            print("\n3. Testing task execution...")
            task = "Search for AUTOPILOT issues in Jira"
            result = await toolbelt.execute_task(task)
            print(f"   Status: {result.get('status')}")
            print(f"   Message: {result.get('message')}")
            if result.get('status') == 'success':
                data = result.get('data')
                if data and 'content' in data and 'issues' in data['content']:
                    issues = data['content']['issues']
                    print(f"   Found {len(issues)} issues")
                    if issues:
                        first_issue = issues[0]
                        print(f"   First issue: {first_issue.get('key')} - {first_issue.get('summary')}")
                else:
                    print(f"   Data structure: {type(data)}")
            else:
                print(f"   Error details: {result}")
                
    except Exception as e:
        print(f"❌ Error testing toolbelt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_toolbelt())