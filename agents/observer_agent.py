"""
Observer Agent - Learns from conversations to improve system knowledge.
Analyzes interactions and updates the knowledge graph with new relationships.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.gemini_client import GeminiClient
from tools.graph_query import GraphQueryTool
from services.memory_service import MemoryService

logger = logging.getLogger(__name__)

class ObserverAgent:
    """
    Observer agent that learns from conversations to improve system knowledge.
    Analyzes conversation patterns and updates the knowledge graph.
    """
    
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.graph_tool = GraphQueryTool()
        self.memory_service = MemoryService()
        
    async def observe_conversation(self, observation_data: Dict[str, Any]):
        """
        Observe and learn from a conversation.
        
        Args:
            observation_data: Dictionary containing conversation data
        """
        try:
            logger.info("Observer Agent analyzing conversation...")
            
            # Extract conversation insights
            insights = await self._analyze_conversation_patterns(observation_data)
            
            if insights:
                # Update knowledge graph with new relationships
                await self._update_knowledge_graph(insights)
                
                # Queue knowledge updates if needed
                await self._queue_knowledge_updates(insights)
                
                logger.info("Observer Agent completed conversation analysis")
            else:
                logger.info("No actionable insights found in conversation")
                
        except Exception as e:
            logger.error(f"Error in Observer Agent: {e}")
    
    async def _analyze_conversation_patterns(self, observation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze conversation patterns to extract insights.
        
        Args:
            observation_data: Conversation data to analyze
            
        Returns:
            Dictionary containing extracted insights
        """
        try:
            message = observation_data.get("message", {})
            response = observation_data.get("response", "")
            gathered_info = observation_data.get("gathered_info", {})
            
            system_prompt = """You are an Observer Agent that learns from conversations to improve an AI knowledge system.

Analyze the conversation and identify:
1. New relationships between people, projects, or concepts
2. Updated information that should be added to the knowledge base
3. Gaps in knowledge that were revealed
4. Common question patterns that could improve search

Focus on extracting structured insights that can be used to:
- Update the knowledge graph with new relationships
- Add new information to the knowledge queue
- Improve future query understanding

Return your analysis as JSON with these fields:
- new_relationships: List of relationships to add to graph
- knowledge_gaps: List of information gaps identified
- entities_mentioned: List of people/projects/concepts mentioned
- query_patterns: Common patterns in the user's question
- confidence_score: How confident you are in these insights (0-1)
"""
            
            user_prompt = f"""
Conversation to analyze:

User Query: {message.get('text', '')}
User: {message.get('user_name', 'Unknown')}
Channel: {message.get('channel_name', 'Unknown')}

AI Response: {response}

Information Used:
Vector Results: {len(gathered_info.get('vector_results', []))} results found
Graph Results: {len(gathered_info.get('graph_results', []))} relationships found

Sample Vector Content: {str(gathered_info.get('vector_results', [])[:2])}
Sample Graph Content: {str(gathered_info.get('graph_results', [])[:2])}

Analyze this conversation and extract actionable insights.
"""
            
            analysis = await self.gemini_client.generate_structured_response(
                system_prompt,
                user_prompt,
                response_format="json"
            )
            
            if analysis:
                try:
                    insights = json.loads(analysis)
                    logger.info(f"Extracted insights with confidence: {insights.get('confidence_score', 0)}")
                    return insights
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse insights JSON: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing conversation patterns: {e}")
            return None
    
    async def _update_knowledge_graph(self, insights: Dict[str, Any]):
        """
        Update the knowledge graph with new relationships.
        
        Args:
            insights: Extracted insights from conversation analysis
        """
        try:
            new_relationships = insights.get("new_relationships", [])
            
            if not new_relationships:
                return
            
            logger.info(f"Updating knowledge graph with {len(new_relationships)} new relationships")
            
            # Process each relationship
            for relationship in new_relationships:
                try:
                    # Extract relationship components
                    source = relationship.get("source")
                    target = relationship.get("target")
                    relationship_type = relationship.get("type")
                    properties = relationship.get("properties", {})
                    
                    if source and target and relationship_type:
                        # Add relationship to graph
                        await self.graph_tool.add_relationship(
                            source=source,
                            target=target,
                            relationship_type=relationship_type,
                            properties=properties
                        )
                        
                        logger.info(f"Added relationship: {source} -> {relationship_type} -> {target}")
                    
                except Exception as e:
                    logger.error(f"Error adding relationship to graph: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error updating knowledge graph: {e}")
    
    async def _queue_knowledge_updates(self, insights: Dict[str, Any]):
        """
        Queue knowledge updates for the Knowledge Update Worker.
        
        Args:
            insights: Extracted insights from conversation analysis
        """
        try:
            knowledge_gaps = insights.get("knowledge_gaps", [])
            entities_mentioned = insights.get("entities_mentioned", [])
            
            if not knowledge_gaps and not entities_mentioned:
                return
            
            # Create knowledge update tasks
            update_tasks = []
            
            # Add tasks for knowledge gaps
            for gap in knowledge_gaps:
                update_tasks.append({
                    "type": "knowledge_gap",
                    "description": gap,
                    "priority": "medium",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Add tasks for new entities that need more information
            for entity in entities_mentioned:
                update_tasks.append({
                    "type": "entity_research",
                    "entity": entity,
                    "priority": "low",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Store update tasks in knowledge queue
            if update_tasks:
                queue_key = f"knowledge_queue:{datetime.now().strftime('%Y%m%d')}"
                
                for task in update_tasks:
                    await self.memory_service.add_to_queue(queue_key, task)
                
                logger.info(f"Queued {len(update_tasks)} knowledge update tasks")
                
        except Exception as e:
            logger.error(f"Error queuing knowledge updates: {e}")
    
    async def analyze_conversation_trends(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze conversation trends over a time window.
        
        Args:
            time_window_hours: Hours to look back for trend analysis
            
        Returns:
            Dictionary containing trend analysis
        """
        try:
            logger.info(f"Analyzing conversation trends for last {time_window_hours} hours")
            
            # Get recent observations from memory
            cutoff_time = datetime.now().timestamp() - (time_window_hours * 3600)
            
            # This would typically query stored observations
            # For now, return placeholder structure
            trends = {
                "total_conversations": 0,
                "most_common_topics": [],
                "frequent_users": [],
                "knowledge_gaps_identified": [],
                "new_relationships_added": 0,
                "confidence_scores": []
            }
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing conversation trends: {e}")
            return {}
