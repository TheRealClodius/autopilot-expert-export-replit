#!/usr/bin/env python3
"""
Test the client agent's ability to handle irrelevant search results gracefully
"""
import asyncio
import json
from models.schemas import ProcessedMessage
from agents.client_agent import ClientAgent

async def test_irrelevant_search_handling():
    """Test client agent with irrelevant search results like the production issue"""
    try:
        client_agent = ClientAgent()
        
        # Create the exact message that's failing in production
        test_message = ProcessedMessage(
            text="Oh ok, very sassy! I wanna know who designs the autopilot experience in the platform. Whom should I talk to?",
            user_id="U_TEST_USER",
            user_name="Andrei Clodius",
            channel_id="C_TEST_CHANNEL", 
            channel_name="autopilot-expert",
            message_ts="1735000000.000001",
            thread_ts=None,
            is_dm=True,
            thread_context=None
        )
        
        # Simulate gathered_info with irrelevant search results (furniture design)
        gathered_info = {
            "vector_results": [
                {
                    "content": "The Golden Age (1930s-1960s) The movement reached its peak during the mid-20th century. Iconic designers like Alvar Aalto from Finland, Arne Jacobsen from Denmark, and Bruno Mathsson from Sweden created pieces that would become design classics.",
                    "score": 0.333705693,
                    "metadata": {"source": "scandinavian_furniture_design", "document_type": "test_data"}
                },
                {
                    "content": "Aalto's work bridges the gap between architecture and furniture design. Arne Jacobsen (1902-1971) Danish architect Jacobsen created some of the most recognizable chairs in design history.",
                    "score": 0.33002162,
                    "metadata": {"source": "scandinavian_furniture_design", "document_type": "test_data"}
                }
            ],
            "graph_results": []
        }
        
        # Context from orchestrator
        context = {
            "query_type": "question",
            "topic": "autopilot", 
            "should_respond": True,
            "response_guidance": "Based on the search results, identify the person or team responsible for the autopilot experience design. Provide a direct answer and contact information if available. Maintain a friendly and helpful tone."
        }
        
        print("Testing Client Agent with Irrelevant Search Results")
        print("=" * 60)
        print(f"Query: {test_message.text}")
        print(f"Search Results: {len(gathered_info['vector_results'])} furniture design results")
        print("=" * 60)
        
        # Test client agent response generation
        response = await client_agent.generate_response(
            test_message,
            gathered_info,
            context
        )
        
        print("Client Agent Response:")
        if response:
            print(json.dumps(response, indent=2))
            
            # Check if response is helpful vs fallback
            response_text = response.get("text", "")
            if "having trouble understanding" in response_text.lower():
                print("\n❌ ISSUE: Still generating fallback response")
            elif "furniture" in response_text.lower() or "scandinavian" in response_text.lower():
                print("\n❌ ISSUE: Using irrelevant furniture data")
            elif "autopilot" in response_text.lower() or "design" in response_text.lower():
                print("\n✅ SUCCESS: Generated relevant Autopilot response despite irrelevant search")
            else:
                print("\n❓ UNKNOWN: Response generated but unclear if relevant")
        else:
            print("❌ CRITICAL: Client Agent returned None (triggers fallback)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_irrelevant_search_handling())