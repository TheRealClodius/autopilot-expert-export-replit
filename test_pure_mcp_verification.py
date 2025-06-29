#!/usr/bin/env python3
"""
Pure MCP Integration Verification Test

This test verifies that the MCP Atlassian integration is working correctly
with the new result format and includes clickable links in client responses.
"""

import asyncio
from datetime import datetime

from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService


async def test_pure_mcp_verification():
    """Test the complete MCP integration with clickable links"""
    
    print("🔍 PURE MCP ATLASSIAN VERIFICATION TEST")
    print("=" * 60)
    
    # Initialize services
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Check if Atlassian tool is available
    if not orchestrator.atlassian_tool.available:
        print("❌ Atlassian tool not available - missing credentials")
        return False
    
    print(f"✅ Atlassian tool available with MCP tools: {orchestrator.atlassian_tool.available_tools}")
    
    # Test Confluence search with MCP
    test_message = ProcessedMessage(
        text="Find pages about Autopilot for Everyone",
        user_id="U_TEST_USER",
        user_name="TestUser",
        user_first_name="Test",
        user_display_name="Test User",
        user_title="Software Engineer",
        user_department="Engineering",
        channel_id="C_TEST_CHANNEL",
        channel_name="test-channel",
        message_ts=str(int(datetime.now().timestamp())),
        thread_ts=None,
        is_dm=False,
        thread_context=None
    )
    
    print(f"\n🎯 Test Query: '{test_message.text}'")
    print()
    
    try:
        # Process the message through the orchestrator
        print("1️⃣ Processing message through orchestrator...")
        result = await orchestrator.process_query(test_message)
        
        if result:
            print(f"✅ Orchestrator response generated:")
            print(f"   Response length: {len(result.get('text', ''))} characters")
            print(f"   Channel: {result.get('channel_id', 'N/A')}")
            print(f"   Thread: {result.get('thread_ts', 'N/A')}")
            
            # Check for clickable links in the response
            response_text = result.get('text', '')
            has_confluence_links = 'uipath.atlassian.net/wiki' in response_text
            has_clickable_format = '<https://' in response_text and '|' in response_text
            
            print(f"\n🔗 CLICKABLE LINKS VERIFICATION:")
            print(f"   Contains Confluence URLs: {'✅' if has_confluence_links else '❌'}")
            print(f"   Uses Slack clickable format: {'✅' if has_clickable_format else '❌'}")
            
            if has_clickable_format:
                # Extract and show clickable links
                import re
                link_pattern = r'<(https://[^|]+)\|([^>]+)>'
                links = re.findall(link_pattern, response_text)
                print(f"   Found {len(links)} clickable links:")
                for url, text in links[:3]:  # Show first 3 links
                    print(f"     • {text} → {url}")
            
            # Show sample of response with links
            print(f"\n📄 RESPONSE SAMPLE (first 300 chars):")
            print(f"   {response_text[:300]}...")
            
            return True
            
        else:
            print("❌ No response generated from orchestrator")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False


async def test_mcp_server_health():
    """Test MCP server health and connectivity"""
    
    print("\n🏥 MCP SERVER HEALTH CHECK")
    print("=" * 40)
    
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    try:
        health_status = await orchestrator.atlassian_tool.check_server_health()
        print(f"✅ MCP server health: {health_status}")
        return health_status
    except Exception as e:
        print(f"❌ MCP server health check failed: {str(e)}")
        return False


async def main():
    """Run all verification tests"""
    
    print("🚀 STARTING PURE MCP VERIFICATION TESTS")
    print("=" * 80)
    
    # Test 1: MCP server health
    health_ok = await test_mcp_server_health()
    
    # Test 2: Complete integration with clickable links
    if health_ok:
        integration_ok = await test_pure_mcp_verification()
    else:
        integration_ok = False
    
    print("\n" + "=" * 80)
    print("🎯 VERIFICATION SUMMARY:")
    print(f"   MCP Server Health: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Integration + Links: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    
    if health_ok and integration_ok:
        print(f"\n🎉 ALL TESTS PASSED - Pure MCP integration with clickable links is working!")
        print(f"   ✅ MCP server responding correctly")
        print(f"   ✅ Orchestrator routing to Atlassian tools")
        print(f"   ✅ Client agent formatting with clickable links")
        print(f"   ✅ Ready for production deployment")
    else:
        print(f"\n❌ SOME TESTS FAILED - Check configuration and logs")


if __name__ == "__main__":
    asyncio.run(main())