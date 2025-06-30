#!/usr/bin/env python3
"""
Test the new LLM-powered suggestion system to verify it generates
contextual, dynamic follow-up questions.
"""

import asyncio
import json
from agents.client_agent import ClientAgent

async def test_llm_suggestions():
    """Test LLM-powered suggestion generation with different scenarios."""
    
    print("🧪 Testing LLM-Powered Suggestion Generator")
    print("=" * 50)
    
    client_agent = ClientAgent()
    
    # Test scenario 1: Atlassian search query
    print("\n📋 Test 1: Project Management Query")
    state_stack_1 = {
        "query": "What's the status of the UiPath Autopilot project?",
        "user": {
            "first_name": "Sarah",
            "title": "Product Manager"
        },
        "orchestrator_findings": {
            "analysis": "User is asking about project status and needs current information",
            "tools_used": ["atlassian_search"],
            "atlassian_summary": "Found 3 Jira issues and 2 Confluence pages about UiPath Autopilot project status and roadmap",
            "search_summary": None,
            "web_summary": None
        }
    }
    
    suggestions_1 = await client_agent._generate_suggestions(state_stack_1)
    print(f"Generated suggestions: {suggestions_1}")
    
    # Test scenario 2: Technical documentation query
    print("\n📚 Test 2: Technical Documentation Query")
    state_stack_2 = {
        "query": "How do I integrate UiPath with Slack?",
        "user": {
            "first_name": "Alex",
            "title": "Software Engineer"
        },
        "orchestrator_findings": {
            "analysis": "User needs technical integration guidance",
            "tools_used": ["vector_search", "perplexity_search"],
            "search_summary": "Found internal documentation about UiPath Slack connector",
            "web_summary": "Found latest API documentation and integration examples",
            "atlassian_summary": None
        }
    }
    
    suggestions_2 = await client_agent._generate_suggestions(state_stack_2)
    print(f"Generated suggestions: {suggestions_2}")
    
    # Test scenario 3: General inquiry
    print("\n💬 Test 3: General Inquiry")
    state_stack_3 = {
        "query": "Tell me about the latest AI trends",
        "user": {
            "first_name": "Jordan",
            "title": "Director of Innovation"
        },
        "orchestrator_findings": {
            "analysis": "User wants information about current AI industry trends",
            "tools_used": ["perplexity_search"],
            "web_summary": "Found recent articles about AI trends, LLM developments, and industry forecasts",
            "search_summary": None,
            "atlassian_summary": None
        }
    }
    
    suggestions_3 = await client_agent._generate_suggestions(state_stack_3)
    print(f"Generated suggestions: {suggestions_3}")
    
    print("\n✅ LLM Suggestion Testing Complete")
    print("The system should now generate contextual, dynamic suggestions")
    print("instead of static keyword-based ones.")

if __name__ == "__main__":
    asyncio.run(test_llm_suggestions())