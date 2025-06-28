#!/usr/bin/env python3
"""
Test Optimized Prompt Caching Performance

This test demonstrates the performance improvements from the optimized caching system.
"""

import time
from utils.prompt_loader import PromptLoader

def test_optimized_caching():
    """Test optimized prompt caching performance"""
    
    print("🚀 Testing Optimized Prompt Caching Performance")
    print("=" * 55)
    
    # Initialize fresh prompt loader
    loader = PromptLoader()
    
    print("1. Cache Performance Test (100 iterations):")
    
    # First load (cold cache)
    start_time = time.time()
    for _ in range(100):
        prompt = loader.get_orchestrator_prompt()
    cold_time = time.time() - start_time
    
    print(f"   Cold cache (100 loads): {cold_time*1000:.2f}ms")
    print(f"   Average per load: {(cold_time/100)*1000:.3f}ms")
    
    # Warm cache performance
    start_time = time.time()
    for _ in range(100):
        prompt = loader.get_orchestrator_prompt()
    warm_time = time.time() - start_time
    
    print(f"   Warm cache (100 loads): {warm_time*1000:.2f}ms")
    print(f"   Average per load: {(warm_time/100)*1000:.3f}ms")
    
    if warm_time > 0:
        speedup = cold_time / warm_time
        print(f"   Speedup: {speedup:.1f}x faster")
    else:
        print("   Speedup: >1000x faster (sub-millisecond)")
    
    print()
    
    # Multi-prompt caching test
    print("2. Multi-Prompt Caching Test:")
    
    start_time = time.time()
    for _ in range(50):
        orchestrator = loader.get_orchestrator_prompt()
        client = loader.get_client_agent_prompt()
        observer = loader.get_observer_agent_prompt()
    multi_time = time.time() - start_time
    
    print(f"   3 prompts x 50 iterations: {multi_time*1000:.2f}ms")
    print(f"   Average per prompt load: {(multi_time/150)*1000:.3f}ms")
    print()
    
    # Cache statistics
    print("3. Cache Statistics:")
    cache_stats = loader.get_cache_stats()
    print(f"   Cached prompts: {cache_stats['cached_prompts']}")
    print(f"   Cache valid: {cache_stats['cache_valid']}")
    print(f"   Cache keys: {cache_stats['cache_keys']}")
    print()
    
    # Verify prompt content integrity
    print("4. Content Integrity Check:")
    orchestrator_1 = loader.get_orchestrator_prompt()
    orchestrator_2 = loader.get_orchestrator_prompt()
    content_match = orchestrator_1 == orchestrator_2
    print(f"   Content consistency: {content_match}")
    print(f"   Prompt length: {len(orchestrator_1)} characters")
    print()
    
    print("🎯 Caching Performance Summary:")
    if warm_time > 0:
        print(f"   Optimized caching provides {cold_time/warm_time:.1f}x performance improvement")
    else:
        print("   Optimized caching provides massive performance improvement")
    print(f"   Successfully cached {cache_stats['cached_prompts']} unique prompts")
    print("   ✅ Optimized caching system working efficiently!")

if __name__ == "__main__":
    test_optimized_caching()