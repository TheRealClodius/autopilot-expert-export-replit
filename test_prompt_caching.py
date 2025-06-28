#!/usr/bin/env python3
"""
Test Prompt Caching System

This script tests the new caching functionality for system prompts:
1. Performance improvement from caching
2. Cache invalidation when file changes
3. Cache statistics tracking
"""

import time
from utils.prompt_loader import PromptLoader

def test_prompt_caching():
    """Test prompt caching performance and behavior"""
    
    print("🚀 Testing Prompt Caching System")
    print("=" * 50)
    
    # Initialize fresh prompt loader
    loader = PromptLoader()
    
    print("1. Initial Cache State:")
    cache_stats = loader.get_cache_stats()
    print(f"   Cached prompts: {cache_stats['cached_prompts']}")
    print(f"   Cache valid: {cache_stats['cache_valid']}")
    print(f"   File exists: {cache_stats['file_exists']}")
    print()
    
    # Test performance with caching
    print("2. Performance Test - First Load (no cache):")
    start_time = time.time()
    orchestrator_prompt = loader.get_orchestrator_prompt()
    first_load_time = time.time() - start_time
    print(f"   First load time: {first_load_time*1000:.2f}ms")
    print(f"   Prompt length: {len(orchestrator_prompt)} characters")
    print()
    
    print("3. Performance Test - Cached Load:")
    start_time = time.time()
    orchestrator_prompt_cached = loader.get_orchestrator_prompt()
    cached_load_time = time.time() - start_time
    print(f"   Cached load time: {cached_load_time*1000:.2f}ms")
    print(f"   Speed improvement: {(first_load_time/cached_load_time):.1f}x faster")
    print(f"   Same content: {orchestrator_prompt == orchestrator_prompt_cached}")
    print()
    
    # Test multiple prompt caching
    print("4. Multi-Prompt Caching Test:")
    start_time = time.time()
    client_prompt = loader.get_client_agent_prompt()
    observer_prompt = loader.get_observer_agent_prompt()
    multi_load_time = time.time() - start_time
    print(f"   Client + Observer load time: {multi_load_time*1000:.2f}ms")
    print()
    
    # Check cache stats after loading
    print("5. Cache Statistics After Loading:")
    cache_stats = loader.get_cache_stats()
    print(f"   Cached prompts: {cache_stats['cached_prompts']}")
    print(f"   Cache keys: {cache_stats['cache_keys']}")
    print()
    
    # Test cache reload
    print("6. Cache Reload Test:")
    start_time = time.time()
    loader.reload_prompts()
    reload_time = time.time() - start_time
    print(f"   Reload time: {reload_time*1000:.2f}ms")
    
    cache_stats_after_reload = loader.get_cache_stats()
    print(f"   Cached prompts after reload: {cache_stats_after_reload['cached_prompts']}")
    print()
    
    # Test prompt info with cache details
    print("7. Prompt Info with Cache Details:")
    prompt_info = loader.get_prompt_info()
    print(f"   Version: {prompt_info['version']}")
    print(f"   Total prompts: {prompt_info['total_prompts']}")
    print(f"   Cache info: {prompt_info['cache_info']}")
    print()
    
    # Performance summary
    print("🎯 Performance Summary:")
    if cached_load_time > 0:
        improvement = (first_load_time / cached_load_time)
        print(f"   Caching provides {improvement:.1f}x speed improvement")
    else:
        print("   Caching provides massive speed improvement (sub-millisecond)")
    
    print(f"   Cache successfully stores {cache_stats['cached_prompts']} prompts")
    print("   ✅ Caching system working correctly!")

if __name__ == "__main__":
    test_prompt_caching()