"""
Conversation Summarizer - Celery worker for abstractive conversation summarization.
Creates dense, narrative summaries of conversation history using LLM intelligence.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from celery import Task
from celery_app import celery_app
from config import settings
from services.core.memory_service import MemoryService

# Import Gemini for summarization
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)

class ConversationSummarizerTask(Task):
    """Base task class for conversation summarization with service initialization"""
    
    def __init__(self):
        self.memory_service = None
        self.gemini_client = None
        self._initialized = False
    
    def _initialize_services(self):
        """Initialize services if not already initialized"""
        if self._initialized:
            return
        
        try:
            # Initialize memory service
            self.memory_service = MemoryService()
            
            # Initialize Gemini client
            if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_client = genai.GenerativeModel(settings.GEMINI_FLASH_MODEL)
                logger.info("Gemini Flash initialized for conversation summarization")
            else:
                logger.warning("Gemini not available for conversation summarization")
            
            self._initialized = True
            logger.info("Conversation summarizer services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversation summarizer services: {e}")
            raise

@celery_app.task(base=ConversationSummarizerTask, bind=True)
def summarize_conversation_chunk(self, conversation_key: str, messages_to_summarize: List[Dict[str, Any]], 
                               existing_summary: str = "") -> Dict[str, Any]:
    """
    Celery task to create abstractive summary of conversation messages.
    
    Args:
        conversation_key: Unique conversation identifier
        messages_to_summarize: List of message dictionaries to summarize
        existing_summary: Previous summary to build upon
        
    Returns:
        Dictionary with new summary and metadata
    """
    
    # Initialize services if needed
    self._initialize_services()
    
    if not self.gemini_client:
        logger.error("Gemini client not available for summarization")
        return {
            "success": False,
            "error": "Gemini client not available",
            "fallback_summary": _create_fallback_summary(messages_to_summarize, existing_summary)
        }
    
    try:
        # Create summarization prompt
        prompt = _build_summarization_prompt(messages_to_summarize, existing_summary)
        
        # Generate summary using Gemini Flash
        response = self.gemini_client.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,  # Lower temperature for more focused summarization
                max_output_tokens=800,  # Limit summary length
                top_p=0.9,
                top_k=40
            )
        )
        
        if response and response.text:
            new_summary = response.text.strip()
            
            # Log success
            logger.info(f"Generated abstractive summary for {conversation_key}: {len(new_summary)} chars")
            
            # Queue update task with the new summary
            update_result = update_conversation_summary.delay(
                conversation_key=conversation_key.split(":")[0],  # Remove potential suffix
                summary_key=f"{conversation_key.split(':')[0]}:long_term_summary",
                new_summary=new_summary,
                message_count=len(messages_to_summarize)
            )
            
            return {
                "success": True,
                "summary": new_summary,
                "messages_processed": len(messages_to_summarize),
                "summary_length": len(new_summary),
                "timestamp": datetime.now().isoformat(),
                "method": "gemini_flash_abstractive",
                "update_task_id": update_result.id
            }
        else:
            logger.warning("Empty response from Gemini for conversation summarization")
            return {
                "success": False,
                "error": "Empty response from Gemini",
                "fallback_summary": _create_fallback_summary(messages_to_summarize, existing_summary)
            }
            
    except Exception as e:
        logger.error(f"Failed to generate abstractive summary: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback_summary": _create_fallback_summary(messages_to_summarize, existing_summary)
        }

def _build_summarization_prompt(messages_to_summarize: List[Dict[str, Any]], 
                               existing_summary: str) -> str:
    """
    Build the summarization prompt for Gemini Flash.
    
    Args:
        messages_to_summarize: Messages to be summarized
        existing_summary: Previous summary to extend
        
    Returns:
        Formatted prompt string
    """
    
    # Format messages for the prompt
    messages_text = ""
    for msg in messages_to_summarize:
        user_name = msg.get("user_name", "Unknown")
        text = msg.get("text", "")
        timestamp = msg.get("stored_at", "")
        
        # Determine speaker
        is_bot = user_name.lower() in ["bot", "autopilot", "assistant"]
        speaker = "Assistant" if is_bot else "User"
        
        messages_text += f"{speaker}: {text}\n"
    
    # Build comprehensive prompt
    prompt = f"""You are a conversation summarizer creating dense, narrative summaries of Slack conversations.

Your task is to create an abstractive summary that captures the key points, decisions, and context from the conversation.

EXISTING SUMMARY:
{existing_summary if existing_summary else "No previous summary - this is the start of the conversation."}

NEW MESSAGES TO INTEGRATE:
{messages_text}

SUMMARIZATION GUIDELINES:
1. Create a flowing narrative summary, not bullet points
2. Focus on key topics discussed, decisions made, and important context
3. Preserve specific details like project names, people mentioned, and technical terms
4. If extending an existing summary, seamlessly integrate new information
5. Keep the summary dense but readable - aim for 2-4 sentences per major topic
6. Maintain chronological flow when possible
7. Include user context and bot responses that add value

EXAMPLE GOOD SUMMARY:
"The conversation began with the user asking about UiPath Autopilot integration timeline. The assistant provided details about the current development status and mentioned that the Q2 release is on track. The user then inquired about specific API endpoints, and the assistant explained the REST API structure and authentication requirements. Later, the user reported a bug in the dashboard and the assistant helped troubleshoot the issue, ultimately creating a Jira ticket for tracking."

Generate a comprehensive summary that integrates the new messages with the existing summary:"""

    return prompt

def _create_fallback_summary(messages_to_summarize: List[Dict[str, Any]], 
                           existing_summary: str) -> str:
    """
    Create a fallback summary when Gemini is unavailable.
    
    Args:
        messages_to_summarize: Messages to summarize
        existing_summary: Previous summary
        
    Returns:
        Simple concatenated summary
    """
    
    # Extract key information
    user_messages = []
    bot_messages = []
    
    for msg in messages_to_summarize:
        user_name = msg.get("user_name", "Unknown")
        text = msg.get("text", "")
        
        if not text:
            continue
            
        is_bot = user_name.lower() in ["bot", "autopilot", "assistant"]
        
        if is_bot:
            bot_messages.append(text[:100] + "..." if len(text) > 100 else text)
        else:
            user_messages.append(text[:100] + "..." if len(text) > 100 else text)
    
    # Create simple summary
    fallback_parts = []
    
    if existing_summary:
        fallback_parts.append(existing_summary)
    
    if user_messages:
        fallback_parts.append(f"User discussed: {'; '.join(user_messages[-2:])}")
    
    if bot_messages:
        fallback_parts.append(f"Assistant responded with: {'; '.join(bot_messages[-2:])}")
    
    return " | ".join(fallback_parts)

@celery_app.task(base=ConversationSummarizerTask, bind=True)
def update_conversation_summary(self, conversation_key: str, summary_key: str, 
                              new_summary: str, message_count: int) -> Dict[str, Any]:
    """
    Celery task to update the conversation summary in Redis/memory.
    
    Args:
        conversation_key: Unique conversation identifier
        summary_key: Redis key for the summary
        new_summary: New abstractive summary
        message_count: Number of messages in the summary
        
    Returns:
        Dictionary with update results
    """
    
    # Initialize services if needed
    self._initialize_services()
    
    if not self.memory_service:
        logger.error("Memory service not available for summary update")
        return {"success": False, "error": "Memory service not available"}
    
    try:
        # Prepare summary data
        summary_data = {
            "summary": new_summary,
            "message_count": message_count,
            "last_updated": datetime.now().isoformat(),
            "method": "abstractive_summarization"
        }
        
        # Store in memory service (async operation needs to be handled)
        # Use asyncio.run to handle the async memory service call
        success = asyncio.run(
            self.memory_service.store_conversation_context(
                summary_key,
                summary_data,
                ttl=86400 * 7  # 7 days TTL
            )
        )
        
        if success:
            logger.info(f"Updated conversation summary for {conversation_key}: {len(new_summary)} chars")
            return {
                "success": True,
                "summary_length": len(new_summary),
                "message_count": message_count,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"Failed to store conversation summary for {conversation_key}")
            return {"success": False, "error": "Failed to store summary"}
            
    except Exception as e:
        logger.error(f"Failed to update conversation summary: {e}")
        return {"success": False, "error": str(e)}

# Add task to Celery app configuration
celery_app.conf.task_routes.update({
    'workers.conversation_summarizer.summarize_conversation_chunk': {'queue': 'summarization'},
    'workers.conversation_summarizer.update_conversation_summary': {'queue': 'summarization'},
})