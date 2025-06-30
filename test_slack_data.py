"""
Test data generator for Slack conversation ingestion testing.
Creates sample Slack messages to test the vector embedding and storage pipeline.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from services.data_processor import DataProcessor

# Sample Slack conversation data for UiPath Autopilot project
SAMPLE_CONVERSATIONS = [
    {
        "channel": "C087QKECFKQ",
        "channel_name": "autopilot-development",
        "messages": [
            {
                "ts": "1703875200.123456",
                "user": "U123USER1",
                "user_name": "Sarah Chen",
                "text": "Hey team, I'm working on the UiPath Autopilot integration with our Slack bot. We need to ensure the vector search is working properly for project documentation retrieval.",
                "thread_ts": None,
                "reply_count": 3
            },
            {
                "ts": "1703875260.234567", 
                "user": "U123USER2",
                "user_name": "Mike Johnson",
                "text": "Great! I've been testing the Pinecone integration. The embedding model is working well with the Google Gemini text-embedding-004. We're getting 768-dimensional vectors.",
                "thread_ts": "1703875200.123456",
                "reply_count": 0
            },
            {
                "ts": "1703875320.345678",
                "user": "U123USER3", 
                "user_name": "Alex Rodriguez",
                "text": "The agent architecture looks solid. We have the Orchestrator using Gemini 2.5 Pro for planning, and the Client Agent using Gemini Flash for response generation. The multi-agent coordination is working smoothly.",
                "thread_ts": "1703875200.123456",
                "reply_count": 0
            },
            {
                "ts": "1703875380.456789",
                "user": "U123USER1",
                "user_name": "Sarah Chen", 
                "text": "Perfect! Let's also make sure the background processing is working. The Celery workers should be handling knowledge updates and entity extraction automatically.",
                "thread_ts": "1703875200.123456",
                "reply_count": 0
            },
            {
                "ts": "1703875440.567890",
                "user": "U123USER4",
                "user_name": "Emma Wilson",
                "text": "I've been working on the progress tracking system. Users now see real-time updates in Slack when the agent is processing their requests. The progress events show 'Analyzing your request...', 'Searching knowledge base...', etc.",
                "thread_ts": None,
                "reply_count": 2
            },
            {
                "ts": "1703875500.678901",
                "user": "U123USER2",
                "user_name": "Mike Johnson",
                "text": "That's awesome Emma! The user experience improvements are really noticeable. The debounced updates prevent message spam while maintaining the real-time feel.",
                "thread_ts": "1703875440.567890",
                "reply_count": 0
            },
            {
                "ts": "1703875560.789012",
                "user": "U123USER5",
                "user_name": "David Kim",
                "text": "I'm focusing on the memory management system. We have hybrid memory with rolling long-term summaries and token-managed live history. The system can maintain conversation context indefinitely now.",
                "thread_ts": None,
                "reply_count": 1
            },
            {
                "ts": "1703875620.890123",
                "user": "U123USER3",
                "user_name": "Alex Rodriguez",
                "text": "The token management is really precise now. We replaced character approximation with tiktoken for exact token counting. Getting 17.1% better efficiency!",
                "thread_ts": "1703875560.789012", 
                "reply_count": 0
            },
            {
                "ts": "1703875680.901234",
                "user": "U123USER6",
                "user_name": "Lisa Park",
                "text": "The entity extraction system is working great. We're using both regex patterns and AI extraction to identify JIRA tickets, project names, deadlines, and people. The deduplication is intelligent too.",
                "thread_ts": None,
                "reply_count": 0
            },
            {
                "ts": "1703875740.012345",
                "user": "U123USER1",
                "user_name": "Sarah Chen",
                "text": "Excellent work everyone! The Autopilot system is really coming together. Our multi-agent architecture with specialized roles (Orchestrator, Client, Observer, Atlassian Guru) is proving very effective.",
                "thread_ts": None,
                "reply_count": 0
            }
        ]
    }
]

def create_processed_messages(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert sample conversations to processed message format for embedding."""
    processed_messages = []
    
    for conversation in conversations:
        channel_id = conversation["channel"]
        channel_name = conversation["channel_name"]
        
        for message in conversation["messages"]:
            # Create processed message in the format expected by the embedding service
            processed_msg = {
                "message_id": f"{channel_id}_{message['ts']}",
                "channel_id": channel_id,
                "channel_name": channel_name,
                "user_id": message["user"],
                "user_name": message["user_name"],
                "timestamp": datetime.fromtimestamp(float(message["ts"])).isoformat(),
                "text": message["text"],
                "thread_ts": message.get("thread_ts"),
                "reply_count": message.get("reply_count", 0),
                "is_thread_reply": message.get("thread_ts") is not None,
                "processed_at": datetime.now().isoformat(),
                "content_type": "slack_message",
                "metadata": {
                    "source": "test_data",
                    "project": "uipath_autopilot",
                    "topics": ["automation", "ai", "slack_integration", "vector_search", "multi_agent"]
                }
            }
            processed_messages.append(processed_msg)
    
    return processed_messages

async def test_embedding_pipeline():
    """Test the complete embedding pipeline with sample data."""
    print("🚀 Starting embedding pipeline test...")
    
    # Initialize services
    embedding_service = EmbeddingService()
    
    # Create processed messages
    processed_messages = create_processed_messages(SAMPLE_CONVERSATIONS)
    print(f"📝 Created {len(processed_messages)} processed messages")
    
    # Test embedding and storage
    try:
        stored_count = await embedding_service.embed_and_store_messages(processed_messages)
        print(f"✅ Successfully embedded and stored {stored_count} messages")
        
        # Get index stats
        stats = await embedding_service.get_index_stats()
        print(f"📊 Index now contains {stats.get('total_vector_count', 0)} vectors")
        
        return {
            "status": "success",
            "messages_processed": len(processed_messages),
            "messages_stored": stored_count,
            "index_stats": stats
        }
        
    except Exception as e:
        print(f"❌ Error in embedding pipeline: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "messages_processed": len(processed_messages)
        }

if __name__ == "__main__":
    result = asyncio.run(test_embedding_pipeline())
    print(f"\n📋 Final Result: {json.dumps(result, indent=2)}")