"""
Simple test to verify client agent link formatting
"""

import asyncio
from agents.client_agent import ClientAgent

async def test_client_links():
    """Test if client agent correctly formats Slack links"""
    
    print("🔗 TESTING CLIENT AGENT LINK FORMATTING")
    print("=" * 50)
    
    client_agent = ClientAgent()
    
    # Test mock state stack with Atlassian results
    mock_state_stack = {
        "current_query": "Who is currently assigned to the most Jira tickets?",
        "conversation_history": {"recent_exchanges": []},
        "orchestrator_analysis": {
            "intent": "Find user with most Jira assignments",
            "atlassian_results": [
                {
                    "action_type": "search_jira_issues", 
                    "success": True,
                    "result": {
                        "jira_search_results": {
                            "query": "assignee = 'Andrei Clodius'",
                            "total_found": 3,
                            "issues": [
                                {
                                    "key": "DESIGN-10321",
                                    "summary": "Messages component issue",
                                    "status": "In Design",
                                    "url": "https://uipath.atlassian.net/browse/DESIGN-10321"
                                },
                                {
                                    "key": "DESIGN-10572", 
                                    "summary": "Baseline component Messages",
                                    "status": "Closed",
                                    "url": "https://uipath.atlassian.net/browse/DESIGN-10572"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    }
    
    print("Input state stack contains Atlassian results with URLs:")
    for result in mock_state_stack["orchestrator_analysis"]["atlassian_results"]:
        if result["success"] and "result" in result:
            issues = result["result"]["jira_search_results"]["issues"]
            for issue in issues:
                print(f"  {issue['key']}: {issue['url']}")
    
    print("\nGenerating client response...")
    response = await client_agent.generate_response(mock_state_stack)
    
    if response:
        response_text = response.get("text", "")
        print(f"\nClient Agent Response ({len(response_text)} chars):")
        print("-" * 40)
        print(response_text)
        print("-" * 40)
        
        # Check for various link patterns
        print("\nLink Analysis:")
        
        # Check for raw URLs
        if "https://uipath.atlassian.net/browse/" in response_text:
            print("✅ Raw URLs found in response")
        else:
            print("❌ No raw URLs in response")
            
        # Check for Slack link format
        slack_links = response_text.count("<https://")
        if slack_links > 0:
            print(f"✅ Found {slack_links} Slack-formatted links")
        else:
            print("❌ No Slack-formatted links found")
            
        # Check for pipe format
        pipe_links = response_text.count("|")
        if pipe_links > 0:
            print(f"✅ Found {pipe_links} pipe separators")
        else:
            print("❌ No pipe separators found")
        
        # Show exact link examples
        import re
        slack_link_pattern = r'<(https://[^|>]+)\|([^>]+)>'
        matches = re.findall(slack_link_pattern, response_text)
        if matches:
            print("\nExact Slack links found:")
            for url, text in matches:
                print(f"  URL: {url}")
                print(f"  Text: {text}")
        else:
            print("\nNo Slack link pattern matches found")
            
    else:
        print("❌ Client agent returned None")

if __name__ == "__main__":
    asyncio.run(test_client_links())