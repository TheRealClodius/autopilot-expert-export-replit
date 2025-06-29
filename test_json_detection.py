#!/usr/bin/env python3
"""
Test JSON Fragment Detection

Test if the current _contains_json_fragments function catches all the problematic patterns.
"""

def _contains_json_fragments(text: str) -> bool:
    """Helper function to detect JSON fragments in response text"""
    json_patterns = ['"limit"', '": 10', '": {', '"}', '"arguments"', '"mcp_tool"']
    return any(pattern in text for pattern in json_patterns) or text.strip().startswith(('{', '[', '"'))

def test_json_detection():
    """Test various JSON fragment patterns"""
    
    print("🔍 TESTING JSON FRAGMENT DETECTION")
    print("=" * 50)
    
    # Test cases based on user reports
    test_cases = [
        '"limit": 10',  # Exact user report
        'limit": 10',   # Without opening quote
        '"limit": 10,', # With comma
        '"limit":10',   # No spaces
        'The limit is 10', # False positive test
        '"mcp_tool": "confluence_search"',
        '"arguments": {"query": "test"}',
        '{"limit": 10}',  # Full JSON object
        'Here are the results: "limit": 10', # Mixed content
        'I found 10 results with limit set to 10', # False positive
        'Based on the search with "limit": 10 parameter', # Embedded
        'Something "limit": 10 something else', # Middle of text
    ]
    
    print("Testing current detection function:")
    for i, test_case in enumerate(test_cases, 1):
        detected = _contains_json_fragments(test_case)
        status = "✅ DETECTED" if detected else "❌ MISSED"
        print(f"{i:2d}. {status}: {test_case}")
    
    print("\n" + "=" * 50)
    print("🎯 ANALYSIS")
    
    # Check specific patterns
    problematic_cases = [
        '"limit": 10',
        '"mcp_tool": "confluence_search"',
        '"arguments": {"query": "test"}'
    ]
    
    all_detected = True
    for case in problematic_cases:
        if not _contains_json_fragments(case):
            print(f"❌ CRITICAL: Failed to detect: {case}")
            all_detected = False
    
    if all_detected:
        print("✅ All critical JSON patterns are detected")
        print("💡 If users still see JSON, the issue is elsewhere")
    else:
        print("🚨 DETECTION GAPS FOUND - Need to improve pattern matching")
    
    print("=" * 50)

if __name__ == "__main__":
    test_json_detection()