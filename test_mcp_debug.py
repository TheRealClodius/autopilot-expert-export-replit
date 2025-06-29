#!/usr/bin/env python3
"""
Debug MCP Connection - Test step by step to see where it hangs
"""

import asyncio
import subprocess
import time
from tools.atlassian_tool import AtlassianTool

async def test_mcp_step_by_step():
    """Test MCP connection step by step with timeouts"""
    print("🔧 DEBUGGING MCP CONNECTION")
    print("=" * 40)
    
    # Test 1: Check credentials
    print("Step 1: Checking credentials...")
    atlassian_tool = AtlassianTool()
    print(f"Credentials available: {atlassian_tool.available}")
    
    if not atlassian_tool.available:
        print("❌ No credentials - stopping test")
        return
    
    # Test 2: Check uvx command exists
    print("\nStep 2: Checking uvx command...")
    try:
        result = subprocess.run(["uvx", "--help"], capture_output=True, text=True, timeout=5)
        print(f"✅ uvx command available (exit code: {result.returncode})")
    except Exception as e:
        print(f"❌ uvx command failed: {e}")
        return
    
    # Test 3: Try to get session with timeout
    print("\nStep 3: Attempting MCP session with 15s timeout...")
    start_time = time.time()
    
    try:
        # Use asyncio.wait_for with timeout
        session = await asyncio.wait_for(
            atlassian_tool._get_session(),
            timeout=15.0
        )
        
        elapsed = time.time() - start_time
        print(f"✅ Session created in {elapsed:.2f}s: {session is not None}")
        
        if session:
            # Test 4: Try simple tool call
            print("\nStep 4: Testing simple MCP tool call...")
            try:
                result = await asyncio.wait_for(
                    session.call_tool("confluence_search", {"query": "test", "limit": 1}),
                    timeout=10.0
                )
                print(f"✅ Tool call successful: {type(result)}")
                
                # Extract content
                content_list = getattr(result, 'content', [])
                if content_list:
                    content = content_list[0]
                    if hasattr(content, 'text'):
                        print(f"📄 Got text response: {len(content.text)} chars")
                    else:
                        print(f"📄 Got content: {type(content)}")
                else:
                    print(f"📄 Result: {result}")
                    
            except asyncio.TimeoutError:
                print("❌ Tool call timed out after 10s")
            except Exception as e:
                print(f"❌ Tool call failed: {e}")
        
        # Cleanup
        await atlassian_tool._cleanup_session()
        print("\n✅ Cleanup completed")
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"❌ Session creation timed out after {elapsed:.2f}s")
        await atlassian_tool._cleanup_session()
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Session creation failed after {elapsed:.2f}s: {e}")
        await atlassian_tool._cleanup_session()

if __name__ == "__main__":
    asyncio.run(test_mcp_step_by_step())