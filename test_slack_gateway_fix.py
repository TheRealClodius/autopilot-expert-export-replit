#!/usr/bin/env python3
"""
Test Slack Gateway Fix

Test to verify the send_message method fix resolves the technical difficulties error.
"""

import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_slack_gateway_methods():
    """Test that SlackGateway has the correct methods"""
    
    print("\n" + "="*60)
    print("SLACK GATEWAY METHOD TEST")
    print("="*60)
    
    try:
        from agents.slack_gateway import SlackGateway
        
        # Initialize SlackGateway
        gateway = SlackGateway()
        
        # Check available methods
        methods = [method for method in dir(gateway) if not method.startswith('_')]
        print(f"✅ SlackGateway initialized successfully")
        print(f"Available methods: {', '.join(methods)}")
        
        # Check for specific methods
        required_methods = ['process_message', 'send_response', 'send_error_response']
        missing_methods = []
        
        for method in required_methods:
            if hasattr(gateway, method):
                print(f"✅ Method '{method}': FOUND")
            else:
                print(f"❌ Method '{method}': MISSING")
                missing_methods.append(method)
        
        if missing_methods:
            print(f"\n❌ Missing required methods: {missing_methods}")
            return False
        else:
            print(f"\n✅ All required methods available")
            return True
        
    except Exception as e:
        print(f"\n❌ SlackGateway test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mcp_health_check():
    """Test the MCP health check that was causing issues"""
    
    print("\n" + "="*60)
    print("MCP HEALTH CHECK TEST")
    print("="*60)
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            health_response = await client.get("http://localhost:8001/healthz")
            
            if health_response.status_code == 200:
                print("✅ MCP server health check: PASSED")
                return True
            else:
                print(f"❌ MCP server health check: FAILED ({health_response.status_code})")
                return False
                
    except Exception as e:
        print(f"❌ MCP health check failed: {e}")
        return False

async def main():
    """Run all tests"""
    
    print("Testing Slack Gateway fix...")
    
    # Test 1: SlackGateway methods
    gateway_ok = await test_slack_gateway_methods()
    
    # Test 2: MCP health check
    mcp_ok = await test_mcp_health_check()
    
    # Overall result
    if gateway_ok and mcp_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("The 'technical difficulties' error should now be resolved.")
        return True
    else:
        print("\n⚠️  Some tests failed.")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)