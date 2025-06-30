#!/usr/bin/env python3
"""
Test script to verify MCP tools caching functionality
"""
import asyncio
import time
from tools.atlassian_tool import AtlassianTool

async def test_cache():
    """Test the caching functionality directly"""
    
    print("🧪 Testing MCP Tools Caching Functionality\n")
    
    # Test 1: Check initial cache state
    print("1. Initial cache state:")
    initial_stats = AtlassianTool.get_cache_stats()
    print(f"   Cache status: {initial_stats['cache_status']}")
    print(f"   Tools count: {initial_stats['tools_count']}")
    print(f"   Is expired: {initial_stats['is_expired']}")
    
    # Test 2: First discovery (should hit MCP server)
    print("\n2. First discovery (cache miss):")
    tool1 = AtlassianTool()
    start_time = time.time()
    tools1 = await tool1.discover_available_tools()
    duration1 = (time.time() - start_time) * 1000
    print(f"   Duration: {duration1:.2f}ms")
    print(f"   Tools discovered: {len(tools1)}")
    
    # Check cache state after first discovery
    cache_stats_after_first = AtlassianTool.get_cache_stats()
    print(f"   Cache status after: {cache_stats_after_first['cache_status']}")
    print(f"   Cache age: {cache_stats_after_first['cache_age_seconds']}")
    
    await tool1.close()
    
    # Test 3: Second discovery (should use cache)
    print("\n3. Second discovery (cache hit):")
    tool2 = AtlassianTool()
    start_time = time.time()
    tools2 = await tool2.discover_available_tools()
    duration2 = (time.time() - start_time) * 1000
    print(f"   Duration: {duration2:.2f}ms")
    print(f"   Tools discovered: {len(tools2)}")
    
    # Check cache state after second discovery
    cache_stats_after_second = AtlassianTool.get_cache_stats()
    print(f"   Cache status after: {cache_stats_after_second['cache_status']}")
    print(f"   Cache age: {cache_stats_after_second['cache_age_seconds']}")
    
    await tool2.close()
    
    # Test 4: Performance comparison
    print("\n4. Performance Analysis:")
    improvement = ((duration1 - duration2) / duration1 * 100) if duration2 > 0 else 0
    print(f"   First request: {duration1:.2f}ms (cache miss)")
    print(f"   Second request: {duration2:.2f}ms (cache hit)")
    print(f"   Performance improvement: {improvement:.1f}%")
    print(f"   Latency reduction: {duration1 - duration2:.2f}ms")
    
    # Test 5: Cache clearing
    print("\n5. Cache clearing test:")
    AtlassianTool.clear_tools_cache()
    cache_stats_after_clear = AtlassianTool.get_cache_stats()
    print(f"   Cache status after clear: {cache_stats_after_clear['cache_status']}")
    
    # Test 6: Third discovery after clear (should hit server again)
    print("\n6. Third discovery after cache clear:")
    tool3 = AtlassianTool()
    start_time = time.time()
    tools3 = await tool3.discover_available_tools()
    duration3 = (time.time() - start_time) * 1000
    print(f"   Duration: {duration3:.2f}ms")
    print(f"   Tools discovered: {len(tools3)}")
    
    await tool3.close()
    
    # Summary
    print("\n📊 Summary:")
    print(f"   Cache is working: {duration2 < duration1 and duration2 < 50}")
    print(f"   Average server hit time: {(duration1 + duration3) / 2:.2f}ms")
    print(f"   Cache hit time: {duration2:.2f}ms")
    print(f"   Cache effectiveness: {'Excellent' if improvement > 50 else 'Good' if improvement > 20 else 'Poor'}")

if __name__ == "__main__":
    asyncio.run(test_cache())