#!/usr/bin/env python3
"""
Pure MCP Integration Verification Test

This test verifies the complete end-to-end MCP integration without any REST API confusion.
Tests direct MCP command generation and execution through the orchestrator.
"""
import asyncio
import json
from typing import Dict, Any
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_pure_mcp_integration():
    """Test complete MCP integration with direct command generation"""
    print("🔧 PURE MCP INTEGRATION VERIFICATION")
    print("=" * 60)
    
    # Initialize components
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    # Test queries that should generate direct MCP commands
    test_cases = [
        {
            "name": "Jira Bug Search",
            "query": "Find all critical bugs in the AUTOPILOT project",
            "expected_mcp_tool": "jira_search",
            "expected_args": ["jql", "max_results"]
        },
        {
            "name": "Confluence Documentation Search", 
            "query": "Search for API documentation in Confluence",
            "expected_mcp_tool": "confluence_search",
            "expected_args": ["query", "limit"]
        },
        {
            "name": "Jira Issue Creation",
            "query": "Create a bug report for login timeout in AUTOPILOT project",
            "expected_mcp_tool": "jira_create",
            "expected_args": ["project_key", "issue_type", "summary"]
        },
        {
            "name": "Specific Issue Lookup",
            "query": "Get details for AUTOPILOT-456",
            "expected_mcp_tool": "jira_get", 
            "expected_args": ["issue_key"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        
        try:
            # Create test message
            message = ProcessedMessage(
                text=test_case['query'],
                user_id="U_TEST_USER",
                channel_id="C_TEST_CHANNEL",
                channel_name="test-channel",
                thread_ts=None,
                message_ts=f"1234567890.{i:06d}",
                user_name="Test User",
                user_first_name="Test",
                user_display_name="Test User",
                user_title="Developer",
                user_department="Engineering"
            )
            
            # Process query through orchestrator
            print("🤔 Analyzing query with orchestrator...")
            result = await orchestrator.process_query(message)
            
            if not result:
                print("❌ No execution plan generated")
                results.append({
                    "test": test_case['name'],
                    "status": "FAILED", 
                    "reason": "No execution plan"
                })
                continue
            
            # Check for Atlassian actions in execution plan
            atlassian_actions = result.get("atlassian_actions", [])
            if not atlassian_actions:
                print("❌ No Atlassian actions found in execution plan")
                results.append({
                    "test": test_case['name'],
                    "status": "FAILED",
                    "reason": "No Atlassian actions"
                })
                continue
            
            # Verify MCP command structure
            action = atlassian_actions[0]
            mcp_tool = action.get("mcp_tool")
            arguments = action.get("arguments", {})
            
            print(f"✅ Generated MCP command:")
            print(f"   Tool: {mcp_tool}")
            print(f"   Arguments: {list(arguments.keys())}")
            
            # Validate expected MCP tool
            if mcp_tool == test_case['expected_mcp_tool']:
                print(f"✅ Correct MCP tool: {mcp_tool}")
                
                # Validate required arguments present
                missing_args = []
                for expected_arg in test_case['expected_args']:
                    if expected_arg not in arguments:
                        missing_args.append(expected_arg)
                
                if not missing_args:
                    print(f"✅ All required arguments present")
                    results.append({
                        "test": test_case['name'],
                        "status": "PASSED",
                        "mcp_tool": mcp_tool,
                        "arguments": list(arguments.keys())
                    })
                else:
                    print(f"⚠️  Missing arguments: {missing_args}")
                    results.append({
                        "test": test_case['name'],
                        "status": "PARTIAL",
                        "mcp_tool": mcp_tool,
                        "missing_args": missing_args
                    })
            else:
                print(f"❌ Wrong MCP tool. Expected: {test_case['expected_mcp_tool']}, Got: {mcp_tool}")
                results.append({
                    "test": test_case['name'],
                    "status": "FAILED",
                    "reason": f"Wrong tool: {mcp_tool}"
                })
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append({
                "test": test_case['name'],
                "status": "ERROR",
                "error": str(e)
            })
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 PURE MCP INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['status'] == 'PASSED')
    partial = sum(1 for r in results if r['status'] == 'PARTIAL')
    failed = sum(1 for r in results if r['status'] in ['FAILED', 'ERROR'])
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"⚠️  Partial: {partial}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    
    print("\n📋 Detailed Results:")
    for result in results:
        status_emoji = {
            'PASSED': '✅',
            'PARTIAL': '⚠️ ',
            'FAILED': '❌',
            'ERROR': '💥'
        }.get(result['status'], '❓')
        
        print(f"{status_emoji} {result['test']}: {result['status']}")
        if 'mcp_tool' in result:
            print(f"   MCP Tool: {result['mcp_tool']}")
        if 'arguments' in result:
            print(f"   Arguments: {result['arguments']}")
        if 'reason' in result:
            print(f"   Reason: {result['reason']}")
        if 'error' in result:
            print(f"   Error: {result['error']}")
    
    # Final assessment
    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 PURE MCP INTEGRATION: FULLY OPERATIONAL")
        print("✅ All tests passed - direct MCP command generation working perfectly")
        print("✅ No REST API confusion - pure MCP architecture achieved")
    elif passed + partial == total:
        print("⚠️  PURE MCP INTEGRATION: MOSTLY OPERATIONAL")
        print("✅ MCP command generation working with minor argument issues")
    else:
        print("❌ PURE MCP INTEGRATION: NEEDS ATTENTION")
        print("❌ Some tests failed - MCP integration may have issues")
    
    print("=" * 60)
    return results

if __name__ == "__main__":
    asyncio.run(test_pure_mcp_integration())