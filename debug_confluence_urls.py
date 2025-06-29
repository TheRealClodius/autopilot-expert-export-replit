#!/usr/bin/env python3
"""
Debug Confluence URL structure to understand the API response
"""

import asyncio
import sys
import os
import json

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.atlassian_tool import AtlassianTool

async def debug_confluence_response():
    """Debug the raw Confluence API response to understand URL structure"""
    
    print("🔍 Debugging Confluence API response structure...")
    
    tool = AtlassianTool()
    
    if not tool.available:
        print("❌ Tool not available")
        return
    
    # Make a direct API call to see the raw structure
    print("\n📡 Making direct Confluence API call...")
    raw_result = await tool._make_confluence_request("/content/search", {
        "cql": 'text ~ "A4E"',
        "limit": 3
    })
    
    print("📄 RAW API RESPONSE:")
    print(json.dumps(raw_result, indent=2))
    
    print("\n🔍 Examining URL fields in first result...")
    if "results" in raw_result and raw_result["results"]:
        first_result = raw_result["results"][0]
        print(f"Title: {first_result.get('title')}")
        print(f"_links: {first_result.get('_links', {})}")
        print(f"webui: {first_result.get('_links', {}).get('webui')}")
        print(f"base: {first_result.get('_links', {}).get('base')}")
        print(f"context: {first_result.get('_links', {}).get('context')}")
        
        # Try to construct proper URL
        base_url = tool.confluence_url.rstrip('/wiki')
        webui_path = first_result.get('_links', {}).get('webui', '')
        
        print(f"\nBase URL: {base_url}")
        print(f"WebUI path: {webui_path}")
        
        if webui_path:
            if webui_path.startswith('/'):
                full_url = f"{base_url}/wiki{webui_path}"
            else:
                full_url = f"{base_url}/wiki/{webui_path}"
            
            print(f"Constructed URL: {full_url}")

if __name__ == "__main__":
    asyncio.run(debug_confluence_response())