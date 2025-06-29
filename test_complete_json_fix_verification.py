#!/usr/bin/env python3
"""
Complete JSON Fix Verification

Test both JSON detection functions to ensure they catch all problematic patterns
and identify any scenarios where JSON fragments could still leak through.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import both detection functions
from agents.client_agent import ClientAgent

def _contains_json_fragments_main(text: str) -> bool:
    """Main pipeline JSON detection function"""
    json_patterns = ['"limit"', '": 10', '": {', '"}', '"arguments"', '"mcp_tool"']
    return any(pattern in text for pattern in json_patterns) or text.strip().startswith(('{', '[', '"'))

def _contains_raw_json_client(text: str) -> bool:
    """Client agent JSON detection function"""
    client = ClientAgent()
    return client._contains_raw_json(text)

def test_comprehensive_json_detection():
    """Test both JSON detection functions comprehensively"""
    
    print("🔍 COMPREHENSIVE JSON DETECTION VERIFICATION")
    print("=" * 70)
    
    # Test cases based on user reports and possible edge cases
    test_cases = [
        # Direct user reports
        '"limit": 10',
        
        # Variations that could appear
        '"limit":10',
        '"limit": 10,',
        '{"limit": 10}',
        '{"limit": 10, "query": "test"}',
        
        # MCP tool patterns
        '"mcp_tool": "confluence_search"',
        '"arguments": {"query": "test", "limit": 10}',
        
        # Embedded in responses
        'Based on your query, I found "limit": 10 results.',
        'The search used parameters: "limit": 10',
        'Here are the results: {"limit": 10, "query": "autopilot"}',
        
        # Edge cases
        'The word limit appears 10 times',  # Should NOT be detected
        'There is a 10 result limit',        # Should NOT be detected
        'I limited the search to 10 items',  # Should NOT be detected
        
        # Other JSON fragments
        '"confluence_search"',
        '"jira_search"',
        '"success": true',
        '": {',
        '"}',
        
        # Complex JSON
        '{"mcp_tool": "confluence_search", "arguments": {"query": "autopilot", "limit": 10}}',
        
        # Natural language that should pass
        'I found 10 results about Autopilot features.',
        'Let me search for information about that.',
        'Here are the Confluence pages I found:',
    ]
    
    print("Testing both detection functions:")
    print("-" * 70)
    
    mismatches = []
    
    for i, test_case in enumerate(test_cases, 1):
        main_detected = _contains_json_fragments_main(test_case)
        client_detected = _contains_raw_json_client(test_case)
        
        if main_detected == client_detected:
            status = "✅ DETECTED" if main_detected else "✅ PASSED"
            consistency = "MATCH"
        else:
            status = "❌ MISMATCH"
            consistency = f"Main: {'YES' if main_detected else 'NO'}, Client: {'YES' if client_detected else 'NO'}"
            mismatches.append({
                'case': test_case,
                'main': main_detected,
                'client': client_detected
            })
        
        print(f"{i:2d}. {status} ({consistency}): {test_case}")
    
    print("\n" + "=" * 70)
    print("🎯 ANALYSIS RESULTS")
    print("=" * 70)
    
    if mismatches:
        print(f"🚨 FOUND {len(mismatches)} DETECTION MISMATCHES:")
        for mismatch in mismatches:
            print(f"   Case: {mismatch['case']}")
            print(f"   Main pipeline detects: {mismatch['main']}")
            print(f"   Client agent detects: {mismatch['client']}")
            print()
        
        print("💡 RECOMMENDATION: Unify detection functions to use same patterns")
    else:
        print("✅ All detection functions are consistent")
    
    # Test specific problematic patterns
    critical_patterns = [
        '"limit": 10',
        '"mcp_tool": "confluence_search"',
        '"arguments": {"query": "test"}'
    ]
    
    print("🔍 TESTING CRITICAL PATTERNS:")
    all_critical_caught = True
    
    for pattern in critical_patterns:
        main_caught = _contains_json_fragments_main(pattern)
        client_caught = _contains_raw_json_client(pattern)
        
        if main_caught and client_caught:
            print(f"   ✅ {pattern}")
        else:
            print(f"   ❌ {pattern} - Main: {main_caught}, Client: {client_caught}")
            all_critical_caught = False
    
    if all_critical_caught:
        print("✅ All critical JSON patterns are caught by both functions")
    else:
        print("🚨 Some critical patterns are not caught - system vulnerable")
    
    print("\n" + "=" * 70)
    print("🛡️  PROTECTION LAYER STATUS")
    print("=" * 70)
    
    if mismatches:
        print("❌ INCONSISTENT PROTECTION: Different functions may allow different patterns")
        print("🔧 ACTION NEEDED: Unify detection logic across all protection layers")
    else:
        print("✅ CONSISTENT PROTECTION: Both layers use equivalent detection")
        print("💡 If users still see JSON, the issue is in execution flow, not detection")

if __name__ == "__main__":
    test_comprehensive_json_detection()