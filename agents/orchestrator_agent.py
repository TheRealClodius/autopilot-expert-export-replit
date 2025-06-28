"""
Orchestrator Agent - Main coordination agent that analyzes queries and creates execution plans.
Uses Gemini 2.5 Pro for query analysis and tool orchestration.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.gemini_client import GeminiClient
from tools.vector_search import VectorSearchTool
from agents.client_agent import ClientAgent
from agents.observer_agent import ObserverAgent
from services.memory_service import MemoryService
from models.schemas import ProcessedMessage

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Main orchestrating agent that analyzes queries and coordinates tool usage.
    Creates multi-step execution plans and manages the overall response flow.
    """
    
    def __init__(self, memory_service: MemoryService):
        self.gemini_client = GeminiClient()
        self.vector_tool = VectorSearchTool()
        self.client_agent = ClientAgent()
        self.observer_agent = ObserverAgent()
        self.memory_service = memory_service
        
    async def process_query(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        Process incoming query and generate response through multi-agent coordination.
        
        Args:
            message: Processed message from Slack Gateway
            
        Returns:
            Response data for sending back to Slack
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Orchestrator processing query: {message.text[:100]}...")
            
            # Store raw message in short-term memory (10 message sliding window)
            # Use consistent thread identifier: for new mentions use message_ts, for thread replies use thread_ts
            thread_identifier = message.thread_ts or message.message_ts
            conversation_key = f"conv:{message.channel_id}:{thread_identifier}"
            await self.memory_service.store_raw_message(
                conversation_key,
                message.dict(),
                max_messages=10
            )
            
            # Also store current conversation context for compatibility
            await self.memory_service.store_conversation_context(
                conversation_key, 
                message.dict(), 
                ttl=86400  # 24 hours
            )
            
            plan_start = time.time()
            # Analyze query and create execution plan
            execution_plan = await self._analyze_query_and_plan(message)
            logger.info(f"Query analysis took {time.time() - plan_start:.2f}s")
            
            if not execution_plan:
                # Let the orchestrator plan freely without constraints
                logger.warning("Query analysis returned None, letting orchestrator handle freely")
                # Don't force a minimal plan - let the system handle it naturally
                execution_plan = {
                    "analysis": f"Free-form analysis of query: '{message.text}'",
                    "tools_needed": ["vector_search"],  # Let it use available tools
                    "vector_queries": [message.text],  # Use the original query
                    "context": {
                        "intent": "open_query",
                        "response_approach": "Use full AI capabilities and available knowledge"
                    }
                }
            
            exec_start = time.time()
            # Execute the plan
            gathered_information = await self._execute_plan(execution_plan, message)
            logger.info(f"Plan execution took {time.time() - exec_start:.2f}s")
            
            response_start = time.time()
            # Build comprehensive state stack for Client Agent
            state_stack = await self._build_state_stack(message, gathered_information, execution_plan)
            
            # Generate final response through Client Agent with complete state
            response = await self.client_agent.generate_response(state_stack)
            logger.info(f"Response generation took {time.time() - response_start:.2f}s")
            
            if response:
                # Handle both string and dict responses from Client Agent
                if isinstance(response, dict):
                    response_text = response.get("text", "")
                    suggestions = response.get("suggestions", [])
                else:
                    response_text = response
                    suggestions = []
                
                # Trigger Observer Agent for learning (fire and forget - don't wait)
                import asyncio
                asyncio.create_task(self._trigger_observation(message, response_text, gathered_information))
                
                total_time = time.time() - start_time
                logger.info(f"Total processing time: {total_time:.2f}s")
                
                # Determine thread_ts for response
                # If user mentioned bot in channel (not in existing thread), start new thread
                # If user replied in existing thread, continue same thread
                response_thread_ts = message.thread_ts or message.message_ts
                
                result = {
                    "channel_id": message.channel_id,
                    "thread_ts": response_thread_ts,
                    "text": response_text,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add suggestions if they exist
                if suggestions:
                    result["suggestions"] = suggestions
                    logger.info(f"Including {len(suggestions)} suggestions in response")
                
                return result
            
            logger.warning("No response generated")
            return None
            
        except Exception as e:
            logger.error(f"Error in orchestrator processing: {e}")
            return None
    
    async def _analyze_query_and_plan(self, message: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        Analyze the query using Gemini and create an execution plan.
        
        Args:
            message: Processed message to analyze
            
        Returns:
            Execution plan dictionary
        """
        try:
            # Get recent messages for better context (10 message sliding window)
            conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
            recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=10)
            
            # Also get legacy conversation history for compatibility
            conversation_history = await self.memory_service.get_conversation_context(conversation_key)
            
            # Prepare context for analysis with short-term memory
            context = {
                "query": message.text,
                "user": message.user_name,
                "channel": message.channel_name,
                "is_dm": message.is_dm,
                "thread_context": message.thread_context,
                "recent_messages": recent_messages,  # Last 10 raw messages
                "conversation_history": conversation_history
            }
            
            # Load prompt from centralized prompt loader
            from utils.prompt_loader import get_orchestrator_prompt
            system_prompt = get_orchestrator_prompt()
            
            user_prompt = f"""
Context: {json.dumps(context, indent=2)}

Create an execution plan to answer this query effectively.

Current Query: "{message.text}"
"""
            
            response = await self.gemini_client.generate_structured_response(
                system_prompt,
                user_prompt,
                response_format="json",
                model=self.gemini_client.pro_model  # Orchestrator uses Pro model for complex planning
            )
            
            if response:
                try:
                    plan = json.loads(response)
                    logger.info(f"Generated execution plan: {plan.get('analysis', 'No analysis')}")
                    return plan
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse execution plan JSON: {e}")
                    logger.error(f"Raw Gemini response: {response[:500]}...")
                    return None
            else:
                logger.error("Gemini API returned empty/None response")
                return None
            
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return None
    

    
    async def _execute_plan(self, plan: Dict[str, Any], message: ProcessedMessage) -> Dict[str, Any]:
        """
        Execute the generated plan by calling appropriate tools.
        
        Args:
            plan: Execution plan from query analysis
            message: Original processed message
            
        Returns:
            Dictionary containing gathered information from vector search
        """
        gathered_info = {"vector_results": []}
        
        try:
            tools_needed = plan.get("tools_needed", [])
            
            # Execute vector search if needed
            if "vector_search" in tools_needed:
                vector_queries = plan.get("vector_queries", [])
                if vector_queries:
                    logger.info(f"Executing {len(vector_queries)} vector searches")
                    for query in vector_queries:
                        results = await self.vector_tool.search(
                            query=query,
                            top_k=5,
                            filters={}
                        )
                        if results:
                            gathered_info["vector_results"].extend(results)
            
            logger.info(f"Gathered {len(gathered_info['vector_results'])} vector results")
            return gathered_info
            
        except Exception as e:
            logger.error(f"Error executing plan: {e}")
            return gathered_info
    
    async def _build_state_stack(self, message: ProcessedMessage, gathered_information: Dict[str, Any], execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive state stack for Client Agent containing all context needed.
        
        Args:
            message: Original processed message
            gathered_information: Results from vector search and other tools
            execution_plan: Orchestrator's execution plan with insights
            
        Returns:
            Complete state stack for client agent
        """
        try:
            # Get conversation history
            thread_identifier = message.thread_ts or message.message_ts
            conversation_key = f"conv:{message.channel_id}:{thread_identifier}"
            recent_messages = await self.memory_service.get_recent_messages(conversation_key, limit=10)
            
            # Get conversation context for potential long-term summary
            conversation_context = await self.memory_service.get_conversation_context(conversation_key)
            
            # Organize recent messages into user queries and agent responses
            user_queries = []
            agent_responses = []
            
            for msg in recent_messages:
                if msg.get("user_name") != "bot" and msg.get("user_name") != "autopilot":
                    user_queries.append({
                        "text": msg.get("text", ""),
                        "user": msg.get("user_name", "Unknown"),
                        "timestamp": msg.get("message_ts", "")
                    })
                else:
                    agent_responses.append({
                        "text": msg.get("text", ""),
                        "timestamp": msg.get("message_ts", "")
                    })
            
            # Build complete state stack
            state_stack = {
                "query": message.text,  # Client agent expects "query" key with text directly
                "current_query": {
                    "text": message.text,
                    "user": message.user_name,
                    "channel": message.channel_name,
                    "is_dm": message.is_dm,
                    "is_mention": message.is_mention,
                    "thread_ts": message.thread_ts,
                    "message_ts": message.message_ts
                },
                "recent_history": {
                    "user_queries": user_queries[-5:],  # Last 5 user queries
                    "agent_responses": agent_responses[-5:],  # Last 5 agent responses
                    "raw_messages": recent_messages  # All 10 raw messages for full context
                },
                "long_conversation_summary": {
                    "has_long_history": len(recent_messages) >= 10,
                    "conversation_context": conversation_context,
                    "summary": "This is a continuing conversation..." if len(recent_messages) >= 10 else None
                },
                "orchestrator_results": {
                    "vector_search_results": gathered_information.get("vector_results", []),
                    "execution_plan": execution_plan,
                    "orchestrator_insights": execution_plan.get("analysis", ""),
                    "response_approach": execution_plan.get("context", {}).get("response_approach", ""),
                    "tools_used": execution_plan.get("tools_needed", [])
                },
                "metadata": {
                    "conversation_key": conversation_key,
                    "thread_identifier": thread_identifier,
                    "response_thread_ts": message.thread_ts or message.message_ts
                }
            }
            
            logger.info(f"Built state stack with {len(user_queries)} user queries, {len(agent_responses)} agent responses, {len(gathered_information.get('vector_results', []))} vector results")
            return state_stack
            
        except Exception as e:
            logger.error(f"Error building state stack: {e}")
            # Return minimal state stack on error
            return {
                "query": message.text,  # Client agent expects "query" key
                "current_query": {
                    "text": message.text,
                    "user": message.user_name,
                    "channel": message.channel_name
                },
                "recent_history": {"user_queries": [], "agent_responses": [], "raw_messages": []},
                "long_conversation_summary": {"has_long_history": False, "summary": None},
                "orchestrator_results": {
                    "vector_search_results": gathered_information.get("vector_results", []),
                    "execution_plan": execution_plan,
                    "orchestrator_insights": execution_plan.get("analysis", "")
                },
                "metadata": {"response_thread_ts": message.thread_ts or message.message_ts}
            }

    async def _trigger_observation(self, message: ProcessedMessage, response: str, gathered_info: Dict[str, Any]):
        """
        Trigger Observer Agent to learn from the conversation (async).
        
        Args:
            message: Original message
            response: Generated response
            gathered_info: Information used to generate response
        """
        try:
            # Don't wait for observation to complete
            observation_data = {
                "message": message.dict(),
                "response": response,
                "gathered_info": gathered_info,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store for Observer Agent to process later
            await self.memory_service.store_temp_data(
                f"observation:{message.message_ts}",
                observation_data,
                ttl=3600  # 1 hour
            )
            
            # Trigger Observer Agent (fire and forget)
            await self.observer_agent.observe_conversation(observation_data)
            
        except Exception as e:
            logger.error(f"Error triggering observation: {e}")
    

