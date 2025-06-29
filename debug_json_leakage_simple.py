#!/usr/bin/env python3
"""
Debug JSON Leakage - Simple Version

Check if raw JSON from orchestrator execution plans could leak into client responses.
"""

import json
from agents.client_agent import ClientAgent

def test_json_leakage_in_client():
    """Test if client agent processes state stack with JSON correctly"""
    
    print("🔍 TESTING JSON LEAKAGE IN CLIENT AGENT STATE PROCESSING")
    print("=" * 60)
    
    # Create a mock state stack that would contain the problematic JSON
    # This simulates what the orchestrator would create
    mock_state_stack = {
        "query": "What are the Autopilot features?",
        "user": {"name": "TestUser", "first_name": "Test"},
        "context": {"channel": "general", "is_dm": False},
        "conversation_history": {"recent_exchanges": []},
        "orchestrator_analysis": {
            "intent": "User wants information about Autopilot features",
            "tools_used": ["atlassian_search"],
            "atlassian_results": [
                {
                    "mcp_tool": "confluence_search",
                    "arguments": {
                        "query": "Autopilot features",
                        "limit": 10  # THIS IS THE PROBLEMATIC JSON FRAGMENT
                    },
                    "success": True,
                    "result": {
                        "success": True,
                        "result": [
                            {"title": "Autopilot for Everyone", "url": "https://example.com"}
                        ]
                    }
                }
            ]
        }
    }
    
    print("Step 1: Checking if mock state stack contains 'limit': 10")
    state_json = json.dumps(mock_state_stack, indent=2)
    if '"limit": 10' in state_json:
        print("🚨 CONFIRMED: Mock state stack contains 'limit': 10")
    else:
        print("✅ No 'limit': 10 in mock state stack")
    
    print("\nStep 2: Testing client agent context formatting")
    client_agent = ClientAgent()
    
    # This is the critical test - does the client agent include raw JSON in the context?
    formatted_context = client_agent._format_state_stack_context(mock_state_stack)
    
    print(f"📄 Context length: {len(formatted_context)} characters")
    
    if '"limit": 10' in formatted_context:
        print("🚨 CRITICAL ISSUE: 'limit': 10 appears in client agent Gemini prompt!")
        print("💡 This means Gemini sees raw JSON and might echo it back")
        
        # Find the specific line
        lines = formatted_context.split('\n')
        for i, line in enumerate(lines):
            if '"limit": 10' in line:
                print(f"   🎯 Line {i+1}: {line.strip()}")
                
        # Show context around the problematic line
        print("\n📄 Context excerpt (looking for JSON fragments):")
        for i, line in enumerate(lines):
            if any(fragment in line for fragment in ['"limit"', '"mcp_tool"', '"arguments"']):
                print(f"   Line {i+1}: {line}")
                
    else:
        print("✅ Good: No 'limit': 10 in client agent context")
    
    # Check for other JSON fragments that could leak
    json_fragments = ['"mcp_tool"', '"arguments"', '"limit"', '"query"']
    found_fragments = []
    
    for fragment in json_fragments:
        if fragment in formatted_context:
            found_fragments.append(fragment)
    
    if found_fragments:
        print(f"\n🚨 OTHER JSON FRAGMENTS FOUND: {found_fragments}")
        print("💡 These could also cause JSON responses")
    else:
        print("\n✅ No other JSON fragments found")
    
    print("\n" + "=" * 60)
    print("🎯 ANALYSIS COMPLETE")
    if '"limit": 10' in formatted_context or found_fragments:
        print("❌ JSON LEAKAGE CONFIRMED - Client agent sees raw JSON")
        print("💡 Solution: Filter JSON from state stack before client processing")
    else:
        print("✅ NO JSON LEAKAGE - Client agent context is clean")
    print("=" * 60)

if __name__ == "__main__":
    test_json_leakage_in_client()