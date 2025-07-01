#!/usr/bin/env python3
"""
Debug script to test orchestrator output and client agent processing
"""

import asyncio
import logging
import json
from models.schemas import ProcessedMessage
from agents.orchestrator_agent import OrchestratorAgent
from agents.client_agent import ClientAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_orchestrator_output():
    """Test orchestrator output generation"""
    try:
        # Create test message
        test_message = ProcessedMessage(
            text="@Autopilot test message with bot mention",
            user_id="U123TEST",
            user_name="TestUser",
            user_email="test@example.com",
            user_display_name="Test User",
            user_first_name="Test",
            user_title="Engineer",
            user_department="Engineering",
            channel_id="C123TEST",
            channel_name="test-channel",
            is_dm=False,
            is_mention=True,
            thread_ts=None,
            message_ts="1672531200.123456"
        )
        
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        
        # Test orchestrator processing
        logger.info("Testing orchestrator processing...")
        result = await orchestrator.analyze_and_respond(test_message)
        
        if result:
            logger.info(f"Orchestrator result keys: {list(result.keys())}")
            logger.info(f"Text length: {len(result.get('text', ''))}")
            logger.info(f"Text preview: {result.get('text', '')[:200]}...")
            
            # Check if we have the new clean output format
            if hasattr(orchestrator, '_get_clean_output_from_result'):
                clean_output = orchestrator._get_clean_output_from_result(result)
                logger.info(f"Clean output keys: {list(clean_output.keys()) if clean_output else 'None'}")
                if clean_output:
                    logger.info(f"Synthesized response: {clean_output.get('synthesized_response', '')[:200]}...")
            
        else:
            logger.error("Orchestrator returned None")
            
    except Exception as e:
        logger.error(f"Error testing orchestrator: {e}")

async def test_client_agent_direct():
    """Test client agent with sample data"""
    try:
        # Create sample orchestrator output
        sample_output = {
            "synthesized_response": "Hello! I'm your Autopilot assistant. I help with project information and automation tasks.",
            "key_findings": ["Bot is operational", "Ready to assist"],
            "source_links": [],
            "confidence_level": "high",
            "suggested_followups": ["Ask about my capabilities", "Try a specific question"],
            "execution_summary": {"steps_completed": 1, "total_steps": 1}
        }
        
        # Create sample message context
        message_context = {
            "user": {
                "first_name": "Test",
                "title": "Engineer",
                "department": "Engineering"
            },
            "context": {
                "is_dm": False,
                "channel_name": "test-channel",
                "thread_ts": None
            },
            "query": "test message"
        }
        
        # Initialize client agent
        client_agent = ClientAgent()
        
        # Test client agent processing
        logger.info("Testing client agent processing...")
        result = await client_agent.generate_response(sample_output, message_context)
        
        if result:
            logger.info(f"Client agent result keys: {list(result.keys())}")
            logger.info(f"Enhanced text: {result.get('text', '')[:200]}...")
        else:
            logger.error("Client agent returned None")
            
    except Exception as e:
        logger.error(f"Error testing client agent: {e}")

async def main():
    """Run all tests"""
    logger.info("=== Testing Orchestrator Output ===")
    await test_orchestrator_output()
    
    logger.info("\n=== Testing Client Agent Directly ===")
    await test_client_agent_direct()

if __name__ == "__main__":
    asyncio.run(main())