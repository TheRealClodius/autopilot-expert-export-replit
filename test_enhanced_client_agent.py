#!/usr/bin/env python3
"""
Comprehensive test of the Enhanced Client Agent system.
Tests all features: contextual personality, role adaptations, source presentation.
"""

import asyncio
import logging
from typing import Dict, Any

# Import the Enhanced Client Agent
from agents.client_agent import ClientAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_client_agent():
    """Test the complete Enhanced Client Agent system."""
    
    print("🚀 Testing Enhanced Client Agent System")
    print("=" * 60)
    
    # Initialize the Enhanced Client Agent
    client_agent = ClientAgent()
    
    # Test Case 1: Technical User in DM with High Confidence
    print("\n📧 Test 1: Technical User DM (High Confidence)")
    print("-" * 40)
    
    orchestrator_output_tech = {
        "synthesized_response": "UiPath Autopilot uses a multi-agent architecture with specialized agents for different tasks. The system implements vector search with Pinecone for knowledge retrieval and uses Google Gemini for natural language processing.",
        "key_findings": [
            "Multi-agent architecture with specialized agents",
            "Vector search using Pinecone for knowledge base",
            "Google Gemini integration for NLP",
            "Real-time conversation processing"
        ],
        "source_links": [
            {"title": "Autopilot Architecture Guide", "url": "https://docs.uipath.com/autopilot-arch", "type": "documentation"},
            {"title": "PILOT-456: Vector Search Implementation", "url": "https://jira.uipath.com/PILOT-456", "type": "jira"},
            {"title": "Gemini Integration Best Practices", "url": "https://ai.google.dev/gemini-api", "type": "web"}
        ],
        "confidence_level": "high",
        "suggested_followups": [
            "How do I customize the agent behavior?",
            "What are the API rate limits?"
        ],
        "execution_summary": {
            "steps_completed": 4,
            "tools_used": ["vector_search", "atlassian_search"]
        }
    }
    
    message_context_tech = {
        "user": {
            "id": "U123TECH",
            "name": "Alex Thompson",
            "first_name": "Alex",
            "display_name": "Alex T",
            "title": "Senior Software Engineer",
            "department": "Engineering"
        },
        "context": {
            "channel_id": "D123TECH",
            "channel_name": "dm_alex",
            "is_dm": True,
            "thread_ts": None,
            "message_ts": "1625097600.123456"
        }
    }
    
    tech_response = await client_agent.generate_response(orchestrator_output_tech, message_context_tech)
    print(f"Response Text:\n{tech_response['text']}")
    print(f"Personality Context: {tech_response['personality_context']}")
    print(f"Suggestions: {tech_response['suggestions']}")
    
    # Test Case 2: Designer in Public Channel with Medium Confidence
    print("\n🎨 Test 2: Designer in Public Channel (Medium Confidence)")
    print("-" * 50)
    
    orchestrator_output_design = {
        "synthesized_response": "Design systems in Autopilot follow established UX patterns with component-based architecture. The interface adapts to user roles and provides contextual guidance.",
        "key_findings": [
            "Component-based design system architecture",
            "Role-based interface adaptations",
            "Contextual guidance and help systems",
            "Accessibility considerations built-in"
        ],
        "source_links": [
            {"title": "UiPath Design System Documentation", "url": "https://design.uipath.com/autopilot", "type": "documentation"},
            {"title": "Design Team Discussion: Autopilot UX", "url": "https://uipath.slack.com/archives/C123/p1625097600", "type": "slack"}
        ],
        "confidence_level": "medium",
        "suggested_followups": [
            "What are the design principles?",
            "How do we ensure accessibility?"
        ],
        "execution_summary": {
            "steps_completed": 3,
            "tools_used": ["vector_search"]
        }
    }
    
    message_context_design = {
        "user": {
            "id": "U456DESIGN",
            "name": "Sarah Chen",
            "first_name": "Sarah",
            "display_name": "Sarah C",
            "title": "Senior UX Designer",
            "department": "Design"
        },
        "context": {
            "channel_id": "C123DESIGN",
            "channel_name": "design-systems",
            "is_dm": False,
            "thread_ts": None,
            "message_ts": "1625097600.234567"
        }
    }
    
    design_response = await client_agent.generate_response(orchestrator_output_design, message_context_design)
    print(f"Response Text:\n{design_response['text']}")
    print(f"Personality Context: {design_response['personality_context']}")
    print(f"Suggestions: {design_response['suggestions']}")
    
    # Test Case 3: Manager with Low Confidence and Complex Sources
    print("\n👔 Test 3: Manager with Low Confidence (Complex Sources)")
    print("-" * 48)
    
    orchestrator_output_manager = {
        "synthesized_response": "Based on preliminary findings, Autopilot deployment might require additional infrastructure planning. The timeline could be affected by integration complexity.",
        "key_findings": [
            "Infrastructure requirements need assessment",
            "Integration complexity varies by use case",
            "Timeline depends on current system architecture",
            "Change management considerations"
        ],
        "source_links": [
            {"title": "Autopilot Deployment Guide", "url": "https://docs.uipath.com/deploy", "type": "confluence"},
            {"title": "INFRA-789: Deployment Planning", "url": "https://jira.uipath.com/INFRA-789", "type": "jira"},
            {"title": "Implementation Timeline Discussion", "url": "https://uipath.slack.com/archives/C456/p1625097600", "type": "slack"},
            {"title": "Enterprise Deployment Best Practices", "url": "https://enterprise-guide.example.com", "type": "web"}
        ],
        "confidence_level": "low",
        "suggested_followups": [
            "What's our current infrastructure status?",
            "Who should be involved in planning?"
        ],
        "execution_summary": {
            "steps_completed": 2,
            "tools_used": ["atlassian_search", "perplexity_search"]
        }
    }
    
    message_context_manager = {
        "user": {
            "id": "U789MANAGER",
            "name": "Michael Rodriguez",
            "first_name": "Michael",
            "display_name": "Michael R",
            "title": "Engineering Manager",
            "department": "Engineering"
        },
        "context": {
            "channel_id": "C789MGMT",
            "channel_name": "engineering-leads",
            "is_dm": False,
            "thread_ts": "1625097600.345678",
            "message_ts": "1625097600.456789"
        }
    }
    
    manager_response = await client_agent.generate_response(orchestrator_output_manager, message_context_manager)
    print(f"Response Text:\n{manager_response['text']}")
    print(f"Personality Context: {manager_response['personality_context']}")
    print(f"Suggestions: {manager_response['suggestions']}")
    
    print("\n✅ Enhanced Client Agent Test Complete!")
    print("=" * 60)
    
    # Test the source organization features specifically
    print("\n📚 Testing Source Organization Features")
    print("-" * 40)
    
    # Test elegant source presentation
    test_sources = [
        {"title": "API Documentation", "url": "https://docs.uipath.com/api", "type": "documentation"},
        {"title": "Getting Started Guide", "url": "https://docs.uipath.com/start", "type": "documentation"},
        {"title": "BUG-123: Authentication Issue", "url": "https://jira.uipath.com/BUG-123", "type": "jira"},
        {"title": "FEATURE-456: New Dashboard", "url": "https://jira.uipath.com/FEATURE-456", "type": "jira"},
        {"title": "Industry Best Practices", "url": "https://industry.example.com/practices", "type": "web"},
        {"title": "Team Discussion: Architecture", "url": "https://slack.com/archives/arch", "type": "slack"}
    ]
    
    context_analysis = {
        "communication_style": "professional_engaging",
        "confidence_tone": "confident",
        "personality_elements": {"technical_depth": True}
    }
    
    # Test source integration
    base_response = "Here's the information you requested about Autopilot implementation."
    integrated_response = client_agent._integrate_sources_elegantly(
        base_response, test_sources, context_analysis
    )
    
    print("Source Integration Test:")
    print(integrated_response)
    
    return {
        "tech_response": tech_response,
        "design_response": design_response, 
        "manager_response": manager_response,
        "source_integration": integrated_response
    }

if __name__ == "__main__":
    # Run the comprehensive test
    results = asyncio.run(test_enhanced_client_agent())
    print(f"\n🎯 Test completed successfully!")
    print(f"Generated {len(results)} different response types")