#!/usr/bin/env python3
"""
Test MCP Results Display

Test the complete flow: MCP tool execution → results processing → client agent display
"""

import asyncio
import json
from tools.atlassian_tool import AtlassianTool
from agents.client_agent import ClientAgent

async def test_mcp_results_display():
    """Test MCP tool execution and results display"""
    
    print("🔍 TESTING MCP RESULTS DISPLAY")
    print("=" * 50)
    
    # Test MCP tool execution
    print("Step 1: Testing MCP tool execution")
    print("-" * 30)
    
    atlassian_tool = AtlassianTool()
    
    # Test confluence search (should return real UiPath data)
    mcp_action = {
        "mcp_tool": "confluence_search",
        "arguments": {
            "query": "Autopilot for Everyone",
            "limit": 3
        }
    }
    
    print(f"Executing MCP action: {mcp_action}")
    
    try:
        # Execute the MCP tool with proper parameters
        result = await atlassian_tool.execute_mcp_tool(
            tool_name=mcp_action["mcp_tool"],
            arguments=mcp_action["arguments"]
        )
        
        if result:
            print("✅ MCP tool execution successful")
            print(f"Result keys: {list(result.keys())}")
            print(f"Success: {result.get('success', False)}")
            
            # Show the structure of the result
            result_data = result.get("result", {})
            print(f"Result data type: {type(result_data)}")
            
            if isinstance(result_data, dict):
                print(f"Result data keys: {list(result_data.keys())}")
                actual_results = result_data.get("result", [])
                print(f"Actual results type: {type(actual_results)}")
                print(f"Number of pages found: {len(actual_results) if isinstance(actual_results, list) else 'Not a list'}")
                
                if isinstance(actual_results, list) and len(actual_results) > 0:
                    first_page = actual_results[0]
                    print(f"First page: {first_page.get('title', 'No title')}")
                    print(f"First page URL: {first_page.get('url', 'No URL')}")
            
        else:
            print("❌ MCP tool execution failed - no result")
            return
            
    except Exception as e:
        print(f"❌ MCP tool execution error: {e}")
        return
    
    print("\nStep 2: Testing client agent result formatting")
    print("-" * 30)
    
    # Create a mock state stack with the MCP results in the format orchestrator stores them
    # Orchestrator stores: {"success": True, "result": pages_array, "tool": mcp_tool}
    mock_atlassian_result = {
        "action_type": "confluence_search",  # For backward compatibility 
        "mcp_tool": "confluence_search",     # Modern MCP format
        "success": result.get("success", False),
        "result": result.get("result", [])   # This should be the pages array
    }
    
    mock_state_stack = {
        "query": "What are the Autopilot for Everyone features?",
        "user": {"name": "TestUser", "first_name": "Test"},
        "context": {"channel": "general", "is_dm": False},
        "conversation_history": {"recent_exchanges": []},
        "orchestrator_analysis": {
            "intent": "User wants information about Autopilot for Everyone",
            "tools_used": ["atlassian_search"],
            "atlassian_results": [mock_atlassian_result]  # Use properly formatted result
        }
    }
    
    print("Creating client agent and formatting context...")
    client_agent = ClientAgent()
    
    # Test the state stack formatting
    formatted_context = client_agent._format_state_stack_context(mock_state_stack)
    
    print(f"✅ Context formatted successfully")
    print(f"Context length: {len(formatted_context)} characters")
    
    # Check if Atlassian results appear in the context
    if "Atlassian Actions:" in formatted_context:
        print("✅ Atlassian results section found in context")
        
        # Extract the Atlassian section
        lines = formatted_context.split('\n')
        in_atlassian_section = False
        atlassian_lines = []
        
        for line in lines:
            if "Atlassian Actions:" in line:
                in_atlassian_section = True
                atlassian_lines.append(line)
            elif in_atlassian_section and line.strip():
                if line.startswith("  ") or line.startswith("     "):
                    atlassian_lines.append(line)
                else:
                    break
        
        if atlassian_lines:
            print("✅ Atlassian results details found:")
            for line in atlassian_lines[:10]:  # Show first 10 lines
                print(f"   {line}")
                
            # Check for clickable links
            has_clickable_links = any('<' in line and '|' in line and '>' in line for line in atlassian_lines)
            if has_clickable_links:
                print("✅ Clickable links found in results")
            else:
                print("❌ NO clickable links found in results")
        else:
            print("❌ No Atlassian result details found")
    else:
        print("❌ NO Atlassian results section found in context")
        print("First 500 characters of context:")
        print(formatted_context[:500])
    
    print("\nStep 3: Testing complete client agent response generation")
    print("-" * 30)
    
    try:
        # Generate a full response using the client agent
        response = await client_agent.generate_response(mock_state_stack)
        
        if response:
            print("✅ Client agent response generated")
            response_text = response.get("text", "") if isinstance(response, dict) else str(response)
            print(f"Response length: {len(response_text)} characters")
            
            # Check if the response mentions Confluence pages
            confluence_mentions = [
                "Confluence", "page", "documentation", "Autopilot for Everyone"
            ]
            
            found_mentions = [mention for mention in confluence_mentions if mention.lower() in response_text.lower()]
            if found_mentions:
                print(f"✅ Response mentions relevant content: {found_mentions}")
            else:
                print("❌ Response doesn't mention expected Confluence content")
            
            # Check for clickable links in the final response
            has_links = '<' in response_text and '|' in response_text and '>' in response_text
            if has_links:
                print("✅ Final response contains clickable links")
            else:
                print("❌ Final response missing clickable links")
            
            print("\nFirst 300 characters of response:")
            print(response_text[:300])
            
        else:
            print("❌ Client agent failed to generate response")
            
    except Exception as e:
        print(f"❌ Client agent error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 MCP RESULTS DISPLAY TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_mcp_results_display())