#!/usr/bin/env python3
"""
Individual Tool Testing with LangSmith Tracing

Tests each tool individually to verify MCP integration and LangSmith tracing works correctly.
"""

import asyncio
import time
import json
from typing import Dict, Any, List

# Import services and tools
from services.memory_service import MemoryService
from services.trace_manager import TraceManager
from tools.atlassian_tool import AtlassianTool
from tools.vector_search import VectorSearchTool
from tools.perplexity_search import PerplexitySearchTool
from tools.outlook_meeting import OutlookMeetingTool

class ToolTester:
    """Comprehensive tool testing with tracing integration"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.trace_manager = TraceManager()
        self.test_results = []
        
    async def run_all_tests(self):
        """Run all tool tests systematically"""
        print("🧪 INDIVIDUAL TOOL TESTING WITH LANGSMITH TRACING")
        print("=" * 60)
        
        # Start overall test session
        session_id = await self.trace_manager.start_conversation_session(
            user_id="test_system",
            message="Individual tool testing session",
            channel_id="test_tools",
            message_ts=str(time.time())
        )
        
        print(f"📊 Test Session Started: {session_id}")
        print(f"🔍 Trace Manager Enabled: {self.trace_manager.is_enabled()}")
        
        # Test each tool individually
        await self.test_atlassian_tool()
        await self.test_vector_search_tool()
        await self.test_perplexity_tool()
        await self.test_outlook_tool()
        
        # Complete test session
        await self.trace_manager.complete_conversation_session(
            final_response="All individual tool tests completed"
        )
        
        # Print summary
        self.print_test_summary()
        
    async def test_atlassian_tool(self):
        """Test Atlassian MCP tool with tracing"""
        print("\n" + "=" * 50)
        print("🔧 TESTING ATLASSIAN MCP TOOL")
        print("=" * 50)
        
        # Initialize with trace manager
        atlassian_tool = AtlassianTool(trace_manager=self.trace_manager)
        
        print(f"✅ Tool Initialized")
        print(f"   MCP Server URL: {atlassian_tool.mcp_server_url}")
        print(f"   Available: {atlassian_tool.available}")
        print(f"   Credentials Check: {atlassian_tool._check_credentials()}")
        print(f"   Trace Manager: {atlassian_tool.trace_manager is not None}")
        
        # Test 1: Health Check
        print(f"\n🔍 Test 1: MCP Server Health Check")
        try:
            health_ok = await atlassian_tool.check_server_health()
            print(f"   Result: {'✅ Healthy' if health_ok else '❌ Unhealthy'}")
            self.test_results.append(("Atlassian Health", health_ok))
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Atlassian Health", False))
        
        # Test 2: List Available Tools
        print(f"\n🔍 Test 2: List Available MCP Tools")
        try:
            tools = await atlassian_tool.list_tools()
            print(f"   Available Tools: {tools}")
            self.test_results.append(("Atlassian List Tools", len(tools) > 0))
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Atlassian List Tools", False))
        
        # Test 3: Confluence Search
        print(f"\n🔍 Test 3: Confluence Search with Tracing")
        start_time = time.time()
        try:
            result = await atlassian_tool.execute_mcp_tool(
                tool_name="confluence_search",
                arguments={
                    "query": "Autopilot for Everyone",
                    "limit": 3
                }
            )
            
            duration = time.time() - start_time
            print(f"   Duration: {duration:.2f}s")
            print(f"   Success: {result.get('success', False)}")
            
            if result.get('success'):
                data = result.get('result', {})
                if isinstance(data, dict) and 'result' in data:
                    pages = data['result']
                    print(f"   Found Pages: {len(pages)}")
                    for i, page in enumerate(pages[:2], 1):
                        title = page.get('title', 'Unknown')
                        space = page.get('space', {}).get('name', 'Unknown')
                        print(f"     {i}. {title} (Space: {space})")
                else:
                    print(f"   Data Type: {type(data)}")
                    print(f"   Data Preview: {str(data)[:100]}...")
                
                self.test_results.append(("Confluence Search", True))
            else:
                print(f"   Error: {result.get('error', 'Unknown')}")
                self.test_results.append(("Confluence Search", False))
                
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Confluence Search", False))
        
        # Test 4: Jira Search
        print(f"\n🔍 Test 4: Jira Search with Tracing")
        start_time = time.time()
        try:
            result = await atlassian_tool.execute_mcp_tool(
                tool_name="jira_search",
                arguments={
                    "jql": "project = DESIGN AND text ~ 'autopilot'",
                    "limit": 3
                }
            )
            
            duration = time.time() - start_time
            print(f"   Duration: {duration:.2f}s")
            print(f"   Success: {result.get('success', False)}")
            
            if result.get('success'):
                data = result.get('result', {})
                if isinstance(data, dict) and 'result' in data:
                    issues = data['result']
                    print(f"   Found Issues: {len(issues)}")
                    for i, issue in enumerate(issues[:2], 1):
                        key = issue.get('key', 'Unknown')
                        summary = issue.get('fields', {}).get('summary', 'Unknown')
                        print(f"     {i}. {key}: {summary[:50]}...")
                else:
                    print(f"   Data Type: {type(data)}")
                    print(f"   Data Preview: {str(data)[:100]}...")
                
                self.test_results.append(("Jira Search", True))
            else:
                print(f"   Error: {result.get('error', 'Unknown')}")
                self.test_results.append(("Jira Search", False))
                
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Jira Search", False))
    
    async def test_vector_search_tool(self):
        """Test Vector Search tool"""
        print("\n" + "=" * 50)
        print("🔍 TESTING VECTOR SEARCH TOOL")
        print("=" * 50)
        
        vector_tool = VectorSearchTool()
        
        print(f"✅ Tool Initialized")
        print(f"   Available: {hasattr(vector_tool, 'search')}")
        
        # Test vector search
        print(f"\n🔍 Test: Vector Search Query")
        start_time = time.time()
        try:
            result = await vector_tool.search(
                query="UiPath Autopilot features and capabilities",
                top_k=3
            )
            
            duration = time.time() - start_time
            print(f"   Duration: {duration:.2f}s")
            print(f"   Results Count: {len(result) if isinstance(result, list) else 0}")
            
            if isinstance(result, list) and len(result) > 0:
                for i, item in enumerate(result[:2], 1):
                    if isinstance(item, dict):
                        text = item.get('text', 'No text')[:50]
                        score = item.get('score', 0)
                        print(f"     {i}. Score: {score:.3f} - {text}...")
                
                self.test_results.append(("Vector Search", True))
            else:
                print(f"   No results or invalid format: {type(result)}")
                self.test_results.append(("Vector Search", False))
                
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Vector Search", False))
    
    async def test_perplexity_tool(self):
        """Test Perplexity search tool"""
        print("\n" + "=" * 50)
        print("🌐 TESTING PERPLEXITY SEARCH TOOL")
        print("=" * 50)
        
        perplexity_tool = PerplexitySearchTool()
        
        print(f"✅ Tool Initialized")
        print(f"   Available: {hasattr(perplexity_tool, 'search')}")
        
        # Test web search
        print(f"\n🔍 Test: Web Search Query")
        start_time = time.time()
        try:
            result = await perplexity_tool.search(
                query="UiPath company recent news and developments 2025"
            )
            
            duration = time.time() - start_time
            print(f"   Duration: {duration:.2f}s")
            print(f"   Success: {result.get('success', False) if isinstance(result, dict) else False}")
            
            if isinstance(result, dict) and result.get('success'):
                answer = result.get('answer', '')
                citations = result.get('citations', [])
                print(f"   Answer Length: {len(answer)} characters")
                print(f"   Citations: {len(citations)}")
                print(f"   Answer Preview: {answer[:100]}...")
                
                self.test_results.append(("Perplexity Search", True))
            else:
                print(f"   Error or no results: {result}")
                self.test_results.append(("Perplexity Search", False))
                
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Perplexity Search", False))
    
    async def test_outlook_tool(self):
        """Test Outlook meeting tool"""
        print("\n" + "=" * 50)
        print("📅 TESTING OUTLOOK MEETING TOOL")
        print("=" * 50)
        
        outlook_tool = OutlookMeetingTool()
        
        print(f"✅ Tool Initialized")
        print(f"   Available: {hasattr(outlook_tool, 'check_availability')}")
        print(f"   Credentials: {outlook_tool._check_credentials()}")
        
        # Test availability check (safe operation)
        print(f"\n🔍 Test: Check Meeting Availability")
        start_time = time.time()
        try:
            result = await outlook_tool.check_availability(
                start_time="2025-06-30T09:00:00",
                end_time="2025-06-30T10:00:00",
                attendees=["test@example.com"]
            )
            
            duration = time.time() - start_time
            print(f"   Duration: {duration:.2f}s")
            print(f"   Success: {result.get('success', False) if isinstance(result, dict) else False}")
            
            if isinstance(result, dict) and result.get('success'):
                print(f"   Availability data received")
                self.test_results.append(("Outlook Availability", True))
            else:
                print(f"   Error or credentials needed: {result}")
                self.test_results.append(("Outlook Availability", False))
                
        except Exception as e:
            print(f"   Error: {e}")
            self.test_results.append(("Outlook Availability", False))
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed in self.test_results if passed)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\nDetailed Results:")
        for test_name, passed in self.test_results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} - {test_name}")
        
        print(f"\n📊 LangSmith Tracing:")
        print(f"- Check your LangSmith dashboard for tool operation traces")
        print(f"- Expected traces for each successful tool execution")
        print(f"- MCP tool operations should show inputs, outputs, and timing")
        print(f"- All traces should be properly nested under test session")

async def main():
    """Run the comprehensive tool testing"""
    tester = ToolTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())