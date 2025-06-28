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
from tools.graph_query import GraphQueryTool
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
        self.graph_tool = GraphQueryTool()
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
            conversation_key = f"conv:{message.channel_id}:{message.thread_ts or message.message_ts}"
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
                return await self._generate_fallback_response(message)
            
            exec_start = time.time()
            # Execute the plan
            gathered_information = await self._execute_plan(execution_plan, message)
            logger.info(f"Plan execution took {time.time() - exec_start:.2f}s")
            
            response_start = time.time()
            # Generate final response through Client Agent
            response = await self.client_agent.generate_response(
                message, 
                gathered_information, 
                execution_plan.get("context", {})
            )
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
                
                result = {
                    "channel_id": message.channel_id,
                    "thread_ts": message.thread_ts,
                    "text": response_text,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add suggestions if they exist
                if suggestions:
                    result["suggestions"] = suggestions
                    logger.info(f"Including {len(suggestions)} suggestions in response")
                
                return result
            
            return await self._generate_fallback_response(message)
            
        except Exception as e:
            logger.error(f"Error in orchestrator processing: {e}")
            return await self._generate_error_response(message, str(e))
    
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
                    return None
            
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
            Dictionary containing gathered information from all tools
        """
        gathered_info = {"vector_results": [], "graph_results": []}
        
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
            
            # Execute graph queries if needed
            if "graph_query" in tools_needed:
                graph_queries = plan.get("graph_queries", [])
                if graph_queries:
                    logger.info(f"Executing {len(graph_queries)} graph queries")
                    for query in graph_queries:
                        results = await self.graph_tool.query(query)
                        if results:
                            gathered_info["graph_results"].extend(results)
            
            # Skip additional searches for faster response time
            # TODO: Re-enable when vector search is properly configured
            logger.info("Skipping additional searches for performance")
            
            logger.info(f"Gathered {len(gathered_info['vector_results'])} vector results and {len(gathered_info['graph_results'])} graph results")
            return gathered_info
            
        except Exception as e:
            logger.error(f"Error executing plan: {e}")
            return gathered_info
    
    async def _generate_additional_searches(self, current_info: Dict[str, Any], original_query: str) -> List[str]:
        """
        Generate additional search queries based on current findings.
        
        Args:
            current_info: Information gathered so far
            original_query: The original user query
            
        Returns:
            List of additional search queries
        """
        try:
            # Extract key entities and concepts from current results
            entities = set()
            
            # Extract from vector results
            for result in current_info.get("vector_results", []):
                content = result.get("content", "")
                # Simple entity extraction (could be enhanced with NER)
                words = content.split()
                for word in words:
                    if word.isupper() and len(word) > 2:  # Likely acronyms/project names
                        entities.add(word)
            
            # Extract from graph results  
            for result in current_info.get("graph_results", []):
                if "name" in result:
                    entities.add(result["name"])
                if "owner" in result:
                    entities.add(result["owner"])
            
            # Generate additional queries
            additional_queries = []
            for entity in list(entities)[:3]:  # Limit to top 3 entities
                additional_queries.extend([
                    f"Latest updates on {entity}",
                    f"{entity} dependencies and relationships",
                    f"Who owns {entity} project"
                ])
            
            return additional_queries[:5]  # Limit total additional queries
            
        except Exception as e:
            logger.error(f"Error generating additional searches: {e}")
            return []
    
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
    
    async def _generate_fallback_response(self, message: ProcessedMessage) -> Dict[str, Any]:
        """Generate fallback response when planning fails"""
        fallback_text = f"I'm having trouble understanding your question about '{message.text[:50]}...'. Could you please rephrase or provide more specific details?"
        
        return {
            "channel_id": message.channel_id,
            "thread_ts": message.thread_ts,
            "text": fallback_text,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_error_response(self, message: ProcessedMessage, error: str) -> Dict[str, Any]:
        """Generate error response"""
        error_text = "I'm experiencing technical difficulties right now. Please try again in a few moments."
        
        return {
            "channel_id": message.channel_id,
            "thread_ts": message.thread_ts,
            "text": error_text,
            "timestamp": datetime.now().isoformat()
        }
