"""
Entity Store Service - Manages structured memory with entity extraction.
Stores and retrieves specific facts, entities, and relationships from conversations.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from copy import deepcopy

from config import settings
from services.memory_service import MemoryService

logger = logging.getLogger(__name__)

@dataclass
class EntityContext:
    """Represents a single context where an entity was mentioned"""
    context: str  # The text context where entity appeared
    mentioned_at: str  # ISO timestamp when mentioned
    relevance_score: float  # Relevance score for this specific mention
    message_id: Optional[str] = None  # Optional message identifier

@dataclass
class Entity:
    """Represents an extracted entity with metadata and history"""
    key: str  # Unique identifier (e.g., "JIRA-123", "Project-Phoenix")
    type: str  # Entity type (jira_ticket, project, deadline, person, etc.)
    value: str  # Primary value/description
    conversation_key: str  # Source conversation
    relevance_score: float = 1.0  # Aggregated relevance/importance score
    aliases: List[str] = field(default_factory=list)  # Alternative names/references
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional structured data
    contexts: List[EntityContext] = field(default_factory=list)  # All contexts where mentioned
    first_mentioned_at: Optional[str] = None  # First time this entity appeared
    last_mentioned_at: Optional[str] = None  # Most recent mention
    mention_count: int = 0  # Total number of times mentioned
    
    # Legacy fields for backward compatibility
    context: Optional[str] = None  # Deprecated - use contexts instead
    mentioned_at: Optional[str] = None  # Deprecated - use first_mentioned_at/last_mentioned_at
    
    def __post_init__(self):
        # Handle legacy single context format
        if self.context and not self.contexts:
            legacy_context = EntityContext(
                context=self.context,
                mentioned_at=self.mentioned_at or datetime.now().isoformat(),
                relevance_score=self.relevance_score
            )
            self.contexts = [legacy_context]
            self.first_mentioned_at = legacy_context.mentioned_at
            self.last_mentioned_at = legacy_context.mentioned_at
            self.mention_count = 1
        
        # Ensure timestamps are set
        if self.contexts and not self.first_mentioned_at:
            sorted_contexts = sorted(self.contexts, key=lambda c: c.mentioned_at)
            self.first_mentioned_at = sorted_contexts[0].mentioned_at
            self.last_mentioned_at = sorted_contexts[-1].mentioned_at
            self.mention_count = len(self.contexts)
    
    def add_context(self, context: EntityContext) -> None:
        """Add a new context mention to this entity"""
        self.contexts.append(context)
        self.mention_count = len(self.contexts)
        
        # Update timestamps
        if not self.first_mentioned_at or context.mentioned_at < self.first_mentioned_at:
            self.first_mentioned_at = context.mentioned_at
        if not self.last_mentioned_at or context.mentioned_at > self.last_mentioned_at:
            self.last_mentioned_at = context.mentioned_at
        
        # Update relevance score (weighted average with recency bias)
        if self.contexts:
            # Give more weight to recent mentions
            total_weight = 0
            weighted_score = 0
            for i, ctx in enumerate(self.contexts):
                # More recent contexts get higher weight
                weight = 1.0 + (i * 0.1)  # 1.0, 1.1, 1.2, etc.
                weighted_score += ctx.relevance_score * weight
                total_weight += weight
            self.relevance_score = weighted_score / total_weight
    
    def get_recent_contexts(self, limit: int = 3) -> List[EntityContext]:
        """Get the most recent contexts where this entity was mentioned"""
        return sorted(self.contexts, key=lambda c: c.mentioned_at, reverse=True)[:limit]
    
    def get_context_summary(self) -> str:
        """Get a summary of all contexts where this entity was mentioned"""
        if not self.contexts:
            return self.context or ""
        
        if len(self.contexts) == 1:
            return self.contexts[0].context
        
        # Create summary of multiple contexts
        recent_contexts = self.get_recent_contexts(3)
        summary_parts = []
        for ctx in recent_contexts:
            # Truncate long contexts
            truncated = ctx.context[:100] + "..." if len(ctx.context) > 100 else ctx.context
            summary_parts.append(truncated)
        
        return f"Mentioned {self.mention_count} times. Recent: " + " | ".join(summary_parts)

class EntityStore:
    """
    Service for managing structured entity storage and retrieval.
    Uses Redis hashes for efficient entity management and lookup.
    """
    
    def __init__(self, memory_service: MemoryService = None):
        self.memory_service = memory_service or MemoryService()
        self.entity_patterns = self._load_entity_patterns()
        
    def _load_entity_patterns(self) -> Dict[str, List[Dict[str, str]]]:
        """Load entity extraction patterns for different entity types"""
        return {
            "jira_ticket": [
                {"pattern": r"\b([A-Z]+-\d+)\b", "description": "JIRA ticket format"},
                {"pattern": r"\bticket\s+([A-Z]+-\d+)\b", "description": "JIRA ticket with prefix"},
                {"pattern": r"\bissue\s+([A-Z]+-\d+)\b", "description": "JIRA issue with prefix"}
            ],
            "project": [
                {"pattern": r"\bProject[\s-]([A-Za-z0-9\s-]+?)(?:\s|$|[,.!?])", "description": "Project name"},
                {"pattern": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s+[Pp]roject\b", "description": "Named project"},
                {"pattern": r"\b([A-Z][A-Z0-9_-]+)\s+(?:initiative|program)\b", "description": "Initiative/program"}
            ],
            "deadline": [
                {"pattern": r"\bdue\s+(?:on\s+)?(\d{4}-\d{2}-\d{2})\b", "description": "Due date"},
                {"pattern": r"\bdeadline[\s:]+(\d{4}-\d{2}-\d{2})\b", "description": "Deadline date"},
                {"pattern": r"\b(Q[1-4]\s+\d{4})\b", "description": "Quarterly deadline"},
                {"pattern": r"\b((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\w+\s+\d{1,2}(?:st|nd|rd|th)?)\b", "description": "Natural date"}
            ],
            "person": [
                {"pattern": r"@([a-zA-Z][a-zA-Z0-9._-]*)", "description": "Slack mention"},
                {"pattern": r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", "description": "Full name"},
                {"pattern": r"\b(?:assigned\s+to|owner|lead|manager)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\b", "description": "Role assignment"}
            ],
            "document": [
                {"pattern": r"\b([A-Z][a-zA-Z0-9\s]+)(?:\s+Template|\s+Document|\s+Report)\b", "description": "Document title"},
                {"pattern": r"\bdocument[\s:]+([A-Za-z0-9\s-]+)", "description": "Referenced document"}
            ],
            "metric": [
                {"pattern": r"\b(\d+(?:\.\d+)?%)\s+(?:uptime|performance|completion|success)", "description": "Percentage metric"},
                {"pattern": r"\b(\d+(?:\.\d+)?)\s*(?:ms|seconds?|minutes?)\s+(?:response|time|latency)", "description": "Time metric"},
                {"pattern": r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:budget|cost|revenue)", "description": "Money metric"}
            ],
            "url": [
                {"pattern": r"(https?://[^\s<>\"]+)", "description": "Web URL"},
                {"pattern": r"\b([a-zA-Z0-9.-]+\.atlassian\.net/[^\s<>\"]*)", "description": "Atlassian URL"}
            ]
        }
    
    async def extract_entities_from_text(
        self, 
        text: str, 
        conversation_key: str,
        context: str = ""
    ) -> List[Entity]:
        """
        Extract entities from text using pattern matching and context analysis.
        
        Args:
            text: Text to analyze
            conversation_key: Source conversation identifier
            context: Additional context about the text
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        try:
            for entity_type, patterns in self.entity_patterns.items():
                for pattern_info in patterns:
                    pattern = pattern_info["pattern"]
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        # Extract the entity value
                        entity_value = match.group(1) if match.groups() else match.group(0)
                        entity_value = entity_value.strip()
                        
                        if not entity_value or len(entity_value) < 2:
                            continue
                        
                        # Create entity key
                        entity_key = self._generate_entity_key(entity_type, entity_value)
                        
                        # Calculate relevance score based on context
                        relevance_score = self._calculate_relevance(entity_value, text, context)
                        
                        # Extract surrounding context
                        start_idx = max(0, match.start() - 50)
                        end_idx = min(len(text), match.end() + 50)
                        surrounding_context = text[start_idx:end_idx].strip()
                        
                        # Create entity
                        entity = self.create_entity(
                            key=entity_key,
                            entity_type=entity_type,
                            value=entity_value,
                            context=surrounding_context,
                            conversation_key=conversation_key,
                            relevance_score=relevance_score,
                            aliases=self._generate_aliases(entity_type, entity_value),
                            metadata={
                                "pattern_used": pattern_info["description"],
                                "match_position": match.span(),
                                "full_text_length": len(text)
                            }
                        )
                        
                        entities.append(entity)
            
            # Deduplicate entities
            entities = self._deduplicate_entities(entities)
            
            logger.info(f"Extracted {len(entities)} entities from text: {[e.key for e in entities]}")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def _generate_entity_key(self, entity_type: str, entity_value: str) -> str:
        """Generate a unique key for an entity"""
        # Normalize the value
        normalized_value = re.sub(r'[^\w\s-]', '', entity_value).strip()
        normalized_value = re.sub(r'\s+', '_', normalized_value)
        
        return f"{entity_type}:{normalized_value}".lower()
    
    def _calculate_relevance(self, entity_value: str, full_text: str, context: str) -> float:
        """Calculate relevance score for an entity based on context"""
        base_score = 1.0
        
        # Boost score for entities mentioned multiple times
        mentions = len(re.findall(re.escape(entity_value), full_text, re.IGNORECASE))
        if mentions > 1:
            base_score *= (1 + (mentions - 1) * 0.2)
        
        # Boost score for important context keywords
        important_keywords = [
            "important", "critical", "urgent", "deadline", "priority",
            "assigned", "responsible", "owner", "lead", "manager",
            "status", "update", "progress", "blocked", "issue"
        ]
        
        context_text = (full_text + " " + context).lower()
        for keyword in important_keywords:
            if keyword in context_text:
                base_score *= 1.1
        
        return min(base_score, 2.0)  # Cap at 2.0
    
    def _generate_aliases(self, entity_type: str, entity_value: str) -> List[str]:
        """Generate alternative names/references for an entity"""
        aliases = []
        
        if entity_type == "jira_ticket":
            # Add variations like "ticket JIRA-123", "issue JIRA-123"
            aliases.extend([
                f"ticket {entity_value}",
                f"issue {entity_value}",
                f"#{entity_value}"
            ])
        elif entity_type == "project":
            # Add abbreviations and variations
            words = entity_value.split()
            if len(words) > 1:
                # Create acronym
                acronym = ''.join(word[0].upper() for word in words)
                aliases.append(acronym)
                # Add first word only
                aliases.append(words[0])
        elif entity_type == "person":
            # Add first name only and variations
            names = entity_value.split()
            if len(names) > 1:
                aliases.append(names[0])  # First name
                aliases.append(names[-1])  # Last name
        
        return aliases
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities, keeping the highest relevance score"""
        entity_map = {}
        
        for entity in entities:
            if entity.key in entity_map:
                # Keep the entity with higher relevance score
                if entity.relevance_score > entity_map[entity.key].relevance_score:
                    entity_map[entity.key] = entity
            else:
                entity_map[entity.key] = entity
        
        return list(entity_map.values())
    
    def create_entity(
        self,
        key: str,
        entity_type: str,
        value: str,
        context: str,
        conversation_key: str,
        relevance_score: float = 1.0,
        aliases: List[str] = None,
        metadata: Dict[str, Any] = None,
        message_id: str = None
    ) -> Entity:
        """
        Create a new entity with proper context structure.
        
        Args:
            key: Unique identifier for the entity
            entity_type: Type of entity (jira_ticket, project, etc.)
            value: Primary value/description
            context: Text context where entity was mentioned
            conversation_key: Source conversation identifier
            relevance_score: Relevance score for this mention
            aliases: Alternative names/references
            metadata: Additional structured data
            message_id: Optional message identifier
            
        Returns:
            New Entity instance with proper context structure
        """
        entity_context = EntityContext(
            context=context,
            mentioned_at=datetime.now().isoformat(),
            relevance_score=relevance_score,
            message_id=message_id
        )
        
        return Entity(
            key=key,
            type=entity_type,
            value=value,
            conversation_key=conversation_key,
            relevance_score=relevance_score,
            aliases=aliases or [],
            metadata=metadata or {},
            contexts=[entity_context],
            first_mentioned_at=entity_context.mentioned_at,
            last_mentioned_at=entity_context.mentioned_at,
            mention_count=1
        )
    
    async def _get_existing_entity(self, entity_store_key: str, entity_key: str) -> Optional[Entity]:
        """Retrieve an existing entity from storage"""
        try:
            if self.memory_service.redis_available and self.memory_service.redis_client:
                hget_result = self.memory_service.redis_client.hget(entity_store_key, entity_key)
                if hasattr(hget_result, '__await__'):
                    entity_json = await hget_result
                else:
                    entity_json = hget_result
            else:
                # Use in-memory fallback
                cache_item = self.memory_service._memory_cache.get(entity_store_key)
                if cache_item and (not cache_item['expiry'] or datetime.now() < cache_item['expiry']):
                    entity_json = cache_item['data'].get(entity_key)
                else:
                    entity_json = None
            
            if entity_json:
                entity_dict = json.loads(entity_json)
                return Entity(**entity_dict)
            return None
            
        except Exception as e:
            logger.warning(f"Error retrieving existing entity {entity_key}: {e}")
            return None
    
    def _merge_entities(self, existing: Entity, new: Entity) -> Entity:
        """
        Merge a new entity with an existing one, combining contexts and updating metadata.
        
        Args:
            existing: The entity already stored
            new: The new entity to merge
            
        Returns:
            Merged entity with combined information
        """
        # Create a copy of the existing entity to modify
        merged = deepcopy(existing)
        
        # Create new context from the new entity
        if new.contexts:
            # Use the first context from new entity (should only be one for new extractions)
            new_context = new.contexts[0]
        else:
            # Handle legacy format
            new_context = EntityContext(
                context=new.context or new.value,
                mentioned_at=new.mentioned_at or datetime.now().isoformat(),
                relevance_score=new.relevance_score
            )
        
        # Add the new context to the merged entity
        merged.add_context(new_context)
        
        # Merge aliases (avoid duplicates)
        if new.aliases:
            existing_aliases_lower = [alias.lower() for alias in merged.aliases]
            for alias in new.aliases:
                if alias.lower() not in existing_aliases_lower:
                    merged.aliases.append(alias)
        
        # Merge metadata (new values override old ones)
        if new.metadata:
            merged.metadata.update(new.metadata)
        
        # Update primary value if new one is more descriptive
        if len(new.value) > len(merged.value):
            merged.value = new.value
        
        logger.debug(f"Merged entity {merged.key}: {len(merged.contexts)} contexts, score {merged.relevance_score:.2f}")
        return merged
    
    async def store_entities(
        self, 
        entities: List[Entity],
        conversation_key: str,
        merge_duplicates: bool = True
    ) -> bool:
        """
        Store entities in Redis hash structure with intelligent merging.
        
        Args:
            entities: List of entities to store
            conversation_key: Source conversation identifier
            merge_duplicates: Whether to merge with existing entities (default: True)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entity_store_key = f"{conversation_key}:entity_store"
            
            stored_count = 0
            merged_count = 0
            
            for entity in entities:
                final_entity = entity
                
                if merge_duplicates:
                    # Check if entity already exists
                    existing_entity = await self._get_existing_entity(entity_store_key, entity.key)
                    if existing_entity:
                        # Merge the new entity with existing one
                        final_entity = self._merge_entities(existing_entity, entity)
                        merged_count += 1
                        logger.debug(f"Merged entity {entity.key}: {existing_entity.mention_count} -> {final_entity.mention_count} mentions")
                
                # Convert entity to JSON
                entity_data = json.dumps(asdict(final_entity), default=str)
                
                # Store in Redis hash
                if self.memory_service.redis_available and self.memory_service.redis_client:
                    hset_result = self.memory_service.redis_client.hset(
                        entity_store_key, 
                        final_entity.key, 
                        entity_data
                    )
                    # Set TTL on the hash
                    expire_result = self.memory_service.redis_client.expire(entity_store_key, 86400 * 7)  # 7 days
                    
                    # Await the results if they are coroutines
                    if hasattr(hset_result, '__await__'):
                        await hset_result
                    if hasattr(expire_result, '__await__'):
                        await expire_result
                else:
                    # Use in-memory fallback
                    if entity_store_key not in self.memory_service._memory_cache:
                        self.memory_service._memory_cache[entity_store_key] = {
                            'data': {},
                            'expiry': datetime.now() + timedelta(days=7)
                        }
                    
                    self.memory_service._memory_cache[entity_store_key]['data'][final_entity.key] = entity_data
                
                stored_count += 1
            
            logger.info(f"Stored {stored_count} entities for conversation: {conversation_key} ({merged_count} merged with existing)")
            return True
            
        except Exception as e:
            logger.error(f"Error storing entities: {e}")
            return False
    
    async def search_entities(
        self, 
        query_keywords: List[str],
        conversation_key: str,
        entity_types: List[str] = None,
        limit: int = 10
    ) -> List[Entity]:
        """
        Search for entities matching query keywords.
        
        Args:
            query_keywords: List of keywords to search for
            conversation_key: Source conversation identifier
            entity_types: Filter by entity types (optional)
            limit: Maximum number of entities to return
            
        Returns:
            List of matching entities, sorted by relevance
        """
        try:
            entity_store_key = f"{conversation_key}:entity_store"
            matching_entities = []
            
            # Get all entities from store
            if self.memory_service.redis_available and self.memory_service.redis_client:
                hgetall_result = self.memory_service.redis_client.hgetall(entity_store_key)
                if hasattr(hgetall_result, '__await__'):
                    entity_data = await hgetall_result
                else:
                    entity_data = hgetall_result
            else:
                # Use in-memory fallback
                cache_item = self.memory_service._memory_cache.get(entity_store_key)
                if cache_item and (not cache_item['expiry'] or datetime.now() < cache_item['expiry']):
                    entity_data = cache_item['data']
                else:
                    entity_data = {}
            
            # Search through entities
            if entity_data:
                for entity_key, entity_json in entity_data.items():
                    try:
                        entity_dict = json.loads(entity_json)
                        entity = Entity(**entity_dict)
                        
                        # Filter by entity type if specified
                        if entity_types and entity.type not in entity_types:
                            continue
                        
                        # Check if any keyword matches
                        match_score = self._calculate_match_score(entity, query_keywords)
                        if match_score > 0:
                            # Boost by original relevance score
                            entity.relevance_score = match_score * entity.relevance_score
                            matching_entities.append(entity)
                    
                    except Exception as e:
                        logger.warning(f"Error parsing entity {entity_key}: {e}")
                        continue
            
            # Sort by relevance score and limit results
            matching_entities.sort(key=lambda e: e.relevance_score, reverse=True)
            result = matching_entities[:limit]
            
            logger.info(f"Found {len(result)} matching entities for keywords: {query_keywords}")
            return result
            
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    def _calculate_match_score(self, entity: Entity, query_keywords: List[str]) -> float:
        """Calculate how well an entity matches the query keywords"""
        match_score = 0.0
        
        # Normalize keywords for comparison
        query_keywords_lower = [kw.lower() for kw in query_keywords]
        
        # Check direct matches in entity value
        entity_value_lower = entity.value.lower()
        for keyword in query_keywords_lower:
            if keyword in entity_value_lower:
                match_score += 2.0  # High score for direct match
        
        # Check matches in aliases
        for alias in entity.aliases:
            alias_lower = alias.lower()
            for keyword in query_keywords_lower:
                if keyword in alias_lower:
                    match_score += 1.5  # Medium score for alias match
        
        # Check matches in context
        context_lower = entity.context.lower()
        for keyword in query_keywords_lower:
            if keyword in context_lower:
                match_score += 0.5  # Lower score for context match
        
        return match_score
    
    async def get_entity_by_key(
        self, 
        entity_key: str,
        conversation_key: str
    ) -> Optional[Entity]:
        """
        Retrieve a specific entity by its key.
        
        Args:
            entity_key: Unique entity identifier
            conversation_key: Source conversation identifier
            
        Returns:
            Entity if found, None otherwise
        """
        try:
            entity_store_key = f"{conversation_key}:entity_store"
            
            if self.memory_service.redis_available and self.memory_service.redis_client:
                hget_result = self.memory_service.redis_client.hget(entity_store_key, entity_key)
                if hasattr(hget_result, '__await__'):
                    entity_json = await hget_result
                else:
                    entity_json = hget_result
            else:
                # Use in-memory fallback
                cache_item = self.memory_service._memory_cache.get(entity_store_key)
                if cache_item and (not cache_item['expiry'] or datetime.now() < cache_item['expiry']):
                    entity_json = cache_item['data'].get(entity_key)
                else:
                    entity_json = None
            
            if entity_json:
                entity_dict = json.loads(entity_json)
                return Entity(**entity_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving entity {entity_key}: {e}")
            return None
    
    async def get_conversation_entity_summary(self, conversation_key: str) -> Dict[str, Any]:
        """
        Get a summary of all entities stored for a conversation.
        
        Args:
            conversation_key: Source conversation identifier
            
        Returns:
            Dictionary with entity statistics and summaries
        """
        try:
            entity_store_key = f"{conversation_key}:entity_store"
            
            # Get all entities
            if self.memory_service.redis_available and self.memory_service.redis_client:
                entity_data = await self.memory_service.redis_client.hgetall(entity_store_key)
            else:
                cache_item = self.memory_service._memory_cache.get(entity_store_key)
                if cache_item and (not cache_item['expiry'] or datetime.now() < cache_item['expiry']):
                    entity_data = cache_item['data']
                else:
                    entity_data = {}
            
            # Analyze entities
            entity_counts = {}
            recent_entities = []
            high_relevance_entities = []
            
            for entity_key, entity_json in entity_data.items():
                try:
                    entity_dict = json.loads(entity_json)
                    entity = Entity(**entity_dict)
                    
                    # Count by type
                    entity_counts[entity.type] = entity_counts.get(entity.type, 0) + 1
                    
                    # Track recent entities (last 24 hours)
                    mentioned_time = datetime.fromisoformat(entity.mentioned_at.replace('Z', '+00:00'))
                    if datetime.now() - mentioned_time.replace(tzinfo=None) < timedelta(hours=24):
                        recent_entities.append(entity)
                    
                    # Track high relevance entities
                    if entity.relevance_score >= 1.5:
                        high_relevance_entities.append(entity)
                
                except Exception as e:
                    logger.warning(f"Error analyzing entity {entity_key}: {e}")
                    continue
            
            return {
                "total_entities": len(entity_data),
                "entity_types": entity_counts,
                "recent_entities_24h": len(recent_entities),
                "high_relevance_entities": len(high_relevance_entities),
                "most_recent_entities": [
                    {"key": e.key, "type": e.type, "value": e.value, "mentioned_at": e.mentioned_at}
                    for e in sorted(recent_entities, key=lambda x: x.mentioned_at, reverse=True)[:5]
                ],
                "highest_relevance_entities": [
                    {"key": e.key, "type": e.type, "value": e.value, "relevance_score": e.relevance_score}
                    for e in sorted(high_relevance_entities, key=lambda x: x.relevance_score, reverse=True)[:5]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating entity summary: {e}")
            return {"total_entities": 0, "entity_types": {}, "error": str(e)}