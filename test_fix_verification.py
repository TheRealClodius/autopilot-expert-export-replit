#!/usr/bin/env python3
"""
Quick test to verify the fix for tool results flow
"""

import asyncio
from models.schemas import ProcessedMessage
from agents.client_agent import ClientAgent

async def test_fix():
    """Test that client agent can access search results from state stack"""
    
    # Mock state stack as created by orchestrator
    mock_state_stack = {
        "query": "Autopilot is an AI, right?",
        "user": {
            "name": "test_user",
            "first_name": "Test",
            "display_name": "Test User",
            "title": "Engineer",
            "department": "Engineering"
        },
        "context": {
            "channel": "general",
            "is_dm": False,
            "thread_ts": None
        },
        "conversation_history": {
            "recent_exchanges": [
                {"role": "user", "text": "Autopilot is an AI, right?", "timestamp": "1640995200.001500"}
            ]
        },
        "orchestrator_analysis": {
            "intent": "The user is asking a factual question about Autopilot being an AI.",
            "tools_used": ["vector_search"],
            "search_results": [
                {
                    "content": "UiPath Autopilot is an AI-powered assistant that helps with automation development.",
                    "source": "documentation.md",
                    "score": 0.89
                },
                {
                    "content": "Autopilot leverages artificial intelligence to provide intelligent suggestions for RPA workflows.",
                    "source": "product_overview.md", 
                    "score": 0.85
                }
            ]
        },
        "response_thread_ts": "1640995200.001500",
        "trace_id": "test-trace-123"
    }
    
    print("Testing client agent access to search results...")
    
    # Test client agent formatting
    client_agent = ClientAgent()
    formatted_context = client_agent._format_state_stack_context(mock_state_stack)
    
    # Check if search results are visible
    has_search_results = "Vector Search Results:" in formatted_context
    
    print(f"Search results visible: {has_search_results}")
    
    if has_search_results:
        print("✅ FIX WORKING - Client agent can access search results!")
        
        # Show the relevant lines
        lines = formatted_context.split('\n')
        showing = False
        for line in lines:
            if "COLLATED ANSWERS FROM ORCHESTRATOR:" in line:
                showing = True
            elif showing and line.strip() == "":
                break
            
            if showing:
                print(f"  {line}")
    else:
        print("❌ FIX NOT WORKING - Client agent cannot access search results")
        print("\nFormatted context preview:")
        print(formatted_context[:800])

if __name__ == "__main__":
    asyncio.run(test_fix())