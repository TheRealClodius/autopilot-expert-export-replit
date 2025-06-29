#!/usr/bin/env python3
"""
Simple Name Recognition Test - Quick diagnostic
"""

import asyncio
from utils.gemini_client import GeminiClient

async def quick_test():
    """Quick test of entity extraction"""
    gemini_client = GeminiClient()
    
    test_messages = [
        "Hello Sarah, how are you today?",
        "Sarah is working on the project",
        "Can you tell Sarah about this?",
        "I spoke with Sarah yesterday",
        "Sarah mentioned the UiPath features"
    ]
    
    for msg in test_messages:
        print(f"Testing: {msg}")
        entities = await gemini_client.extract_entities(msg)
        
        # Check if Sarah was found
        sarah_found = any(e.get('text', '').lower() == 'sarah' for e in entities)
        print(f"  Sarah detected: {sarah_found}")
        print(f"  All entities: {entities}")
        print()

if __name__ == "__main__":
    asyncio.run(quick_test())