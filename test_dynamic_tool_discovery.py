#!/usr/bin/env python3
"""
Test dynamic tool discovery system
"""
import asyncio
from tools.atlassian_tool import AtlassianTool
from agents.orchestrator_agent import OrchestratorAgent
from services.memory_service import MemoryService

async def test_discovery():
    """Test the dynamic tool discovery"""
    
    print("🔧 Testing Dynamic Tool Discovery...")
    
    # Test 1: Direct AtlassianTool discovery
    print("\n1. Direct AtlassianTool discovery:")
    atlassian_tool = AtlassianTool()
    tools = await atlassian_tool.discover_available_tools()
    
    print(f"Discovered {len(tools)} tools")
    for tool in tools:
        name = tool.get('name', 'unknown')
        desc = tool.get('description', 'No description')[:50] + '...'
        print(f"  - {name}: {desc}")
    
    print(f"\nAtlassian tools list: {atlassian_tool.available_tools}")
    
    # Test 2: Orchestrator discovery
    print("\n2. Orchestrator discovery:")
    memory_service = MemoryService()
    orchestrator = OrchestratorAgent(memory_service)
    
    orchestrator_tools = await orchestrator.discover_and_update_tools()
    print(f"Orchestrator discovered {len(orchestrator_tools)} total tools")
    print(f"Orchestrator Atlassian tools: {orchestrator.atlassian_tool.available_tools}")
    
    # Test 3: Dynamic prompt generation
    print("\n3. Dynamic prompt generation:")
    if hasattr(orchestrator, '_generate_dynamic_system_prompt'):
        prompt = await orchestrator._generate_dynamic_system_prompt()
        print("Generated dynamic system prompt:")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    else:
        print("Dynamic prompt generation method not found")
    
    return tools

if __name__ == "__main__":
    asyncio.run(test_discovery())