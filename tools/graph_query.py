"""
Graph Query Tool - Manages relationships and dependencies using NetworkX.
Handles project relationships, ownership, and dependency queries.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Set
import networkx as nx
from datetime import datetime

from services.memory_service import MemoryService

logger = logging.getLogger(__name__)

class GraphQueryTool:
    """
    Tool for querying and managing relationships in a knowledge graph.
    Uses NetworkX for graph operations and Redis for persistence.
    """
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.graph = nx.MultiDiGraph()  # Directed multigraph for complex relationships
        self._graph_key = "knowledge_graph"
        
    async def initialize_graph(self):
        """Initialize graph from persistent storage"""
        try:
            graph_data = await self.memory_service.get_graph_data(self._graph_key)
            if graph_data:
                self.graph = nx.node_link_graph(graph_data, multigraph=True, directed=True)
                logger.info(f"Loaded graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
            else:
                logger.info("Initialized empty knowledge graph")
        except Exception as e:
            logger.error(f"Error initializing graph: {e}")
            self.graph = nx.MultiDiGraph()
    
    async def query(self, query: str) -> List[Dict[str, Any]]:
        """
        Query the knowledge graph based on natural language input.
        
        Args:
            query: Natural language query about relationships
            
        Returns:
            List of query results
        """
        try:
            logger.info(f"Executing graph query: {query[:100]}...")
            
            query_lower = query.lower()
            results = []
            
            # Ensure graph is initialized
            if self.graph.number_of_nodes() == 0:
                await self.initialize_graph()
            
            # Parse query intent and execute appropriate graph operations
            if "owner" in query_lower or "owns" in query_lower:
                results = await self._query_ownership(query)
            elif "depend" in query_lower or "relationship" in query_lower:
                results = await self._query_dependencies(query)
            elif "connect" in query_lower or "related" in query_lower:
                results = await self._query_connections(query)
            elif "project" in query_lower:
                results = await self._query_projects(query)
            else:
                # General search across all relationships
                results = await self._general_query(query)
            
            logger.info(f"Graph query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error executing graph query: {e}")
            return []
    
    async def add_relationship(
        self, 
        source: str, 
        target: str, 
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a new relationship to the knowledge graph.
        
        Args:
            source: Source node identifier
            target: Target node identifier
            relationship_type: Type of relationship
            properties: Additional properties for the relationship
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure graph is initialized
            if self.graph.number_of_nodes() == 0:
                await self.initialize_graph()
            
            # Add nodes if they don't exist
            if not self.graph.has_node(source):
                self.graph.add_node(source, type="entity", created=datetime.now().isoformat())
            
            if not self.graph.has_node(target):
                self.graph.add_node(target, type="entity", created=datetime.now().isoformat())
            
            # Add edge with properties
            edge_properties = properties or {}
            edge_properties.update({
                "relationship_type": relationship_type,
                "created": datetime.now().isoformat()
            })
            
            self.graph.add_edge(source, target, **edge_properties)
            
            # Persist graph
            await self._persist_graph()
            
            logger.info(f"Added relationship: {source} -> {relationship_type} -> {target}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            return False
    
    async def _query_ownership(self, query: str) -> List[Dict[str, Any]]:
        """Query ownership relationships"""
        try:
            results = []
            
            # Find ownership edges
            for source, target, data in self.graph.edges(data=True):
                rel_type = data.get("relationship_type", "").lower()
                if "own" in rel_type or "owner" in rel_type or "responsible" in rel_type:
                    results.append({
                        "type": "ownership",
                        "owner": source,
                        "owned": target,
                        "relationship": data.get("relationship_type"),
                        "created": data.get("created", ""),
                        "properties": {k: v for k, v in data.items() if k not in ["relationship_type", "created"]}
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying ownership: {e}")
            return []
    
    async def _query_dependencies(self, query: str) -> List[Dict[str, Any]]:
        """Query dependency relationships"""
        try:
            results = []
            
            # Find dependency edges
            for source, target, data in self.graph.edges(data=True):
                rel_type = data.get("relationship_type", "").lower()
                if "depend" in rel_type or "require" in rel_type or "use" in rel_type:
                    results.append({
                        "type": "dependency",
                        "dependent": source,
                        "dependency": target,
                        "relationship": data.get("relationship_type"),
                        "created": data.get("created", ""),
                        "properties": {k: v for k, v in data.items() if k not in ["relationship_type", "created"]}
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying dependencies: {e}")
            return []
    
    async def _query_connections(self, query: str) -> List[Dict[str, Any]]:
        """Query general connections between entities"""
        try:
            results = []
            
            # Extract potential entity names from query
            query_words = query.lower().split()
            entities = [word.title() for word in query_words if len(word) > 2]
            
            # Find connections between entities mentioned in query
            for entity in entities:
                if self.graph.has_node(entity):
                    # Get neighbors
                    predecessors = list(self.graph.predecessors(entity))
                    successors = list(self.graph.successors(entity))
                    
                    for pred in predecessors:
                        edge_data = self.graph[pred][entity]
                        for key, data in edge_data.items():
                            results.append({
                                "type": "connection",
                                "source": pred,
                                "target": entity,
                                "relationship": data.get("relationship_type", "connected"),
                                "direction": "incoming",
                                "properties": data
                            })
                    
                    for succ in successors:
                        edge_data = self.graph[entity][succ]
                        for key, data in edge_data.items():
                            results.append({
                                "type": "connection",
                                "source": entity,
                                "target": succ,
                                "relationship": data.get("relationship_type", "connected"),
                                "direction": "outgoing",
                                "properties": data
                            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying connections: {e}")
            return []
    
    async def _query_projects(self, query: str) -> List[Dict[str, Any]]:
        """Query project-specific information"""
        try:
            results = []
            
            # Find project nodes and their relationships
            for node, data in self.graph.nodes(data=True):
                node_type = data.get("type", "").lower()
                if "project" in node_type or "autopilot" in node.lower():
                    project_info = {
                        "type": "project",
                        "name": node,
                        "properties": data,
                        "relationships": []
                    }
                    
                    # Get all relationships for this project
                    for source, target, edge_data in self.graph.edges(node, data=True):
                        project_info["relationships"].append({
                            "target": target,
                            "relationship": edge_data.get("relationship_type", "related"),
                            "properties": edge_data
                        })
                    
                    # Get incoming relationships
                    for source, target, edge_data in self.graph.in_edges(node, data=True):
                        project_info["relationships"].append({
                            "source": source,
                            "relationship": edge_data.get("relationship_type", "related"),
                            "direction": "incoming",
                            "properties": edge_data
                        })
                    
                    results.append(project_info)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying projects: {e}")
            return []
    
    async def _general_query(self, query: str) -> List[Dict[str, Any]]:
        """General query across all graph data"""
        try:
            results = []
            
            # Simple text matching against node names and edge properties
            query_terms = set(query.lower().split())
            
            # Search nodes
            for node, data in self.graph.nodes(data=True):
                node_terms = set(node.lower().split())
                if query_terms.intersection(node_terms):
                    results.append({
                        "type": "node",
                        "name": node,
                        "properties": data,
                        "match_type": "name"
                    })
            
            # Search edge properties
            for source, target, data in self.graph.edges(data=True):
                edge_text = " ".join([
                    str(v) for v in data.values() 
                    if isinstance(v, str)
                ]).lower()
                
                if any(term in edge_text for term in query_terms):
                    results.append({
                        "type": "relationship",
                        "source": source,
                        "target": target,
                        "properties": data,
                        "match_type": "properties"
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in general query: {e}")
            return []
    
    async def _persist_graph(self):
        """Persist graph to Redis"""
        try:
            graph_data = nx.node_link_data(self.graph)
            await self.memory_service.store_graph_data(self._graph_key, graph_data)
            logger.debug("Graph persisted to Redis")
        except Exception as e:
            logger.error(f"Error persisting graph: {e}")
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        try:
            if self.graph.number_of_nodes() == 0:
                await self.initialize_graph()
            
            # Basic statistics
            stats = {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
                "density": nx.density(self.graph),
                "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
            }
            
            # Node type distribution
            node_types = {}
            for node, data in self.graph.nodes(data=True):
                node_type = data.get("type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            stats["node_types"] = node_types
            
            # Relationship type distribution
            relationship_types = {}
            for source, target, data in self.graph.edges(data=True):
                rel_type = data.get("relationship_type", "unknown")
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            
            stats["relationship_types"] = relationship_types
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {}
