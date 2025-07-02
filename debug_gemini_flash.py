#!/usr/bin/env python3
"""
Quick debug script to test Gemini Flash responses directly
"""
import asyncio
import logging
from utils.gemini_client import GeminiClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_gemini_flash():
    """Test Gemini Flash with simple prompts"""
    client = GeminiClient()
    
    # Test 1: Simple prompt
    print("=== Test 1: Simple prompt ===")
    system_prompt = "You are a helpful assistant."
    user_prompt = "Say hello!"
    
    response = await client.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=client.flash_model,
        max_tokens=100,
        temperature=0.7
    )
    
    print(f"Response: {response}")
    
    # Test 2: Complex prompt from prompts.yaml style
    print("\n=== Test 2: Complex prompt ===")
    complex_system = """You are an expert AI assistant with sophisticated personality and contextual adaptations.
Takes clean synthesized output from orchestrator and applies:
- Dynamic personality based on context (DM vs channel, user role, confidence level)
- Elegant source link integration
- Contextual intelligence and tone adaptation
- Enhanced user experience with engaging follow-ups"""
    
    complex_user = """Please enhance this response with your personality:

"Based on the search results, I found some relevant information about authentication systems."

User context: TestUser is asking in a public channel. Be thoughtful in your tone.

CONTEXT FOR PERSONALITY:
User: TestUser (Product Manager)
Setting: #test-channel (public)
Confidence: medium (some information found)
Execution: Completed multiple searches

GUIDELINES:
- Be professional but personable
- Adapt tone to user role (PM)
- Consider medium confidence level
- Format response for Slack"""

    response2 = await client.generate_response(
        system_prompt=complex_system,
        user_prompt=complex_user,
        model=client.flash_model,
        max_tokens=5000,
        temperature=1.0
    )
    
    print(f"Response: {response2}")

if __name__ == "__main__":
    asyncio.run(test_gemini_flash())