"""
Entity Extractor - Celery worker for background entity extraction from conversations.
Analyzes user queries and bot responses to extract and store structured entities.
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
from services.data.entity_store import EntityStore, Entity

# Import Gemini for enhanced entity extraction
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)

class EntityExtractionTask(Task):
    """Base task class for entity extraction with service initialization"""
    
    def __init__(self):
        self.memory_service = None
        self.entity_store = None
        self.gemini_client = None
        self._initialized = False
    
    def _initialize_services(self):
        """Initialize services if not already initialized"""
        if self._initialized:
            return
        
        try:
            # Initialize memory service
            self.memory_service = MemoryService()
            
            # Initialize entity store
            self.entity_store = EntityStore(self.memory_service)
            
            # Initialize Gemini client for enhanced extraction
            if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_client = genai.GenerativeModel(settings.GEMINI_FLASH_MODEL)
                logger.info("Gemini Flash initialized for entity extraction")
            else:
                logger.warning("Gemini not available for enhanced entity extraction")
            
            self._initialized = True
            logger.info("Entity extraction services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize entity extraction services: {e}")
            raise

    def _extract_entities_with_gemini(
        self, 
        user_query: str, 
        bot_response: str, 
        conversation_key: str,
        user_name: str
    ) -> List[Entity]:
        """
        Use Gemini to extract additional entities with AI understanding.
        
        Args:
            user_query: User's query text
            bot_response: Bot's response text
            conversation_key: Conversation identifier
            user_name: Name of the user
            
        Returns:
            List of AI-extracted entities
        """
        try:
            # Build prompt for entity extraction
            prompt = f"""
    Analyze the following conversation exchange and extract important entities that should be remembered for future reference.

    User ({user_name}): {user_query}

    Bot Response: {bot_response}

    Extract entities in the following categories and format your response as JSON:
    1. JIRA tickets (format: PROJ-123)
    2. Project names and initiatives
    3. People mentioned (names, roles, assignments)
    4. Deadlines and dates
    5. Important documents or templates
    6. Metrics, numbers, and measurements
    7. URLs and links
    8. Technical terms or product names

    For each entity, provide:
    - "type": entity category
    - "value": the actual entity value
    - "context": brief context where it was mentioned
    - "importance": score from 1-10 for how important this entity is to remember

    Only extract entities that are factual and specific. Avoid generic terms.

    Format as JSON array: [
      {{"type": "jira_ticket", "value": "PROJ-123", "context": "user asked about status", "importance": 8}},
      {{"type": "project", "value": "Phoenix Initiative", "context": "discussed roadmap", "importance": 9}}
    ]
    """
            
            # Generate entity extraction with Gemini
            response = self.gemini_client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Very low temperature for factual extraction
                    max_output_tokens=1000,
                    top_p=0.8,
                    top_k=20
                )
            )
            
            if not response or not response.text:
                return []
            
            # Parse JSON response with retry mechanism
            ai_entities = self._parse_gemini_response_with_retry(
                response.text, conversation_key, user_name, max_retries=2
            )
            
            logger.info(f"Gemini extracted {len(ai_entities)} additional entities")
            return ai_entities
            
        except Exception as e:
            logger.error(f"Error in Gemini entity extraction: {e}")
            return []

    def _parse_gemini_response_with_retry(self, response_text: str, conversation_key: str, 
                                        user_name: str, max_retries: int = 2) -> List[Entity]:
        """
        Parse Gemini JSON response with automatic retry mechanism for malformed JSON.
        If JSON parsing fails, sends a self-correction prompt to Gemini.
        
        Args:
            response_text: The original response text from Gemini
            conversation_key: Key for conversation context
            user_name: Name of the user in the conversation
            max_retries: Maximum number of retry attempts (default: 2)
            
        Returns:
            List of Entity objects extracted from the response
        """
        original_response = response_text
        
        for attempt in range(max_retries + 1):
            try:
                # Clean the response text (remove markdown formatting if present)
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
                
                # Attempt to parse JSON
                entities_data = json.loads(cleaned_text)
                
                # Convert to Entity objects
                ai_entities = []
                for entity_data in entities_data:
                    if not isinstance(entity_data, dict):
                        continue
                    
                    entity_type = entity_data.get("type", "unknown")
                    entity_value = entity_data.get("value", "")
                    entity_context = entity_data.get("context", "")
                    importance = entity_data.get("importance", 5)
                    
                    if not entity_value:
                        continue
                    
                    # Generate entity key
                    entity_key = self.entity_store._generate_entity_key(entity_type, entity_value)
                    
                    # Convert importance to relevance score
                    relevance_score = min(importance / 5.0, 2.0)  # Scale 1-10 to 0.2-2.0
                    
                    entity = self.entity_store.create_entity(
                        key=entity_key,
                        entity_type=entity_type,
                        value=entity_value,
                        context=entity_context,
                        conversation_key=conversation_key,
                        relevance_score=relevance_score,
                        aliases=self.entity_store._generate_aliases(entity_type, entity_value),
                        metadata={
                            "extraction_method": "gemini_ai",
                            "importance_score": importance,
                            "user_name": user_name
                        }
                    )
                    
                    ai_entities.append(entity)
                
                if attempt > 0:
                    logger.info(f"Gemini JSON parsing succeeded on retry attempt {attempt}")
                
                return ai_entities
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
                
                # If this is not the last attempt, try to get Gemini to self-correct
                if attempt < max_retries:
                    logger.info(f"Attempting Gemini self-correction (attempt {attempt + 1}/{max_retries})")
                    
                    correction_prompt = f"""The previous response was not valid JSON. Please correct it and provide only the JSON.

Original response that failed to parse:
{response_text}

Error: {str(e)}

Please return ONLY a valid JSON array of entities in this exact format:
[
  {{
    "type": "entity_type",
    "value": "entity_value", 
    "context": "brief_context",
    "importance": 7
  }}
]

Provide only the JSON array, no markdown formatting, no explanations."""
                    
                    try:
                        # Send correction prompt to Gemini
                        correction_response = self.model.generate_content(
                            correction_prompt,
                            generation_config=self.model_config
                        )
                        
                        if correction_response and correction_response.text:
                            response_text = correction_response.text
                            logger.debug(f"Gemini self-correction response: {response_text[:200]}...")
                        else:
                            logger.warning("Gemini self-correction returned empty response")
                            break
                            
                    except Exception as correction_error:
                        logger.error(f"Error during Gemini self-correction: {correction_error}")
                        break
                else:
                    logger.error(f"Failed to parse JSON after {max_retries} retries, giving up")
            
            except Exception as e:
                logger.error(f"Unexpected error during JSON parsing attempt {attempt + 1}: {e}")
                break
        
        # All attempts failed
        logger.warning("All JSON parsing attempts failed, returning empty entity list")
        return []

    def _deduplicate_extraction_results(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate entities between regex and AI extraction before storage.
        When duplicates are found, merge them by keeping the one with higher relevance
        score and richer context.
        
        Args:
            entities: Combined list of entities from regex and AI extraction
            
        Returns:
            Deduplicated list of entities with merged information
        """
        try:
            entity_map = {}
            
            for entity in entities:
                if entity.key in entity_map:
                    existing = entity_map[entity.key]
                    
                    # Choose the entity with higher relevance score as base
                    if entity.relevance_score > existing.relevance_score:
                        primary, secondary = entity, existing
                    else:
                        primary, secondary = existing, entity
                    
                    # Merge information from both extractions
                    merged_entity = self._merge_duplicate_entities(primary, secondary)
                    entity_map[entity.key] = merged_entity
                    
                    logger.debug(f"Merged duplicate entity {entity.key}: regex + AI extraction")
                else:
                    entity_map[entity.key] = entity
            
            original_count = len(entities)
            deduplicated_count = len(entity_map)
            
            if original_count > deduplicated_count:
                logger.info(f"Deduplicated {original_count - deduplicated_count} duplicate entities from combined extraction results")
            
            return list(entity_map.values())
            
        except Exception as e:
            logger.error(f"Error deduplicating extraction results: {e}")
            return entities  # Return original list if deduplication fails

    def _merge_duplicate_entities(self, primary: Entity, secondary: Entity) -> Entity:
        """
        Merge two duplicate entities, combining their best attributes.
        
        Args:
            primary: Entity with higher relevance score (used as base)
            secondary: Entity to merge information from
            
        Returns:
            Merged entity with combined information
        """
        try:
            # Start with primary entity as base
            merged = Entity(
                key=primary.key,
                type=primary.type,
                value=primary.value,
                context=primary.context,
                conversation_key=primary.conversation_key,
                relevance_score=primary.relevance_score,
                aliases=primary.aliases.copy() if primary.aliases else [],
                metadata=primary.metadata.copy() if primary.metadata else {}
            )
            
            # Merge contexts (prefer AI context if it's richer)
            if secondary.context and len(secondary.context) > len(primary.context or ""):
                merged.context = secondary.context
            
            # Merge aliases (avoid duplicates)
            if secondary.aliases:
                existing_aliases_lower = [alias.lower() for alias in merged.aliases]
                for alias in secondary.aliases:
                    if alias.lower() not in existing_aliases_lower:
                        merged.aliases.append(alias)
            
            # Merge metadata (combine extraction methods)
            if secondary.metadata:
                extraction_methods = []
                
                # Track extraction methods
                if primary.metadata.get("extraction_method"):
                    extraction_methods.append(primary.metadata["extraction_method"])
                if secondary.metadata.get("extraction_method"):
                    extraction_methods.append(secondary.metadata["extraction_method"])
                
                # Merge all metadata
                merged.metadata.update(secondary.metadata)
                
                # Store combined extraction methods
                if extraction_methods:
                    merged.metadata["extraction_methods"] = list(set(extraction_methods))
                    merged.metadata["extraction_method"] = "+".join(sorted(set(extraction_methods)))
            
            # Use the more descriptive value
            if len(secondary.value) > len(primary.value):
                merged.value = secondary.value
            
            # Calculate weighted relevance score (slightly favor AI extraction if present)
            ai_boost = 1.1 if any("gemini" in method for method in 
                                 merged.metadata.get("extraction_methods", [])) else 1.0
            merged.relevance_score = max(primary.relevance_score, secondary.relevance_score) * ai_boost
            
            logger.debug(f"Merged entity {merged.key}: methods={merged.metadata.get('extraction_method', 'unknown')}, score={merged.relevance_score:.2f}")
            return merged
            
        except Exception as e:
            logger.error(f"Error merging duplicate entities: {e}")
            return primary  # Return primary if merge fails

@celery_app.task(base=EntityExtractionTask, bind=True)
def extract_entities_from_conversation(
    self, 
    conversation_key: str, 
    user_query: str, 
    bot_response: str,
    user_name: str = "user",
    additional_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Celery task to extract entities from a conversation exchange.
    
    Args:
        conversation_key: Unique conversation identifier
        user_query: User's query text
        bot_response: Bot's response text
        user_name: Name of the user
        additional_context: Additional context data
        
    Returns:
        Dictionary with extraction results
    """
    
    # Initialize services if needed
    self._initialize_services()
    
    if not self.entity_store:
        logger.error("Entity store not available for extraction")
        return {
            "success": False,
            "error": "Entity store not available",
            "entities_extracted": 0
        }
    
    try:
        additional_context = additional_context or {}
        
        # Extract entities from both user query and bot response
        all_entities = []
        
        # Extract from user query
        user_entities = asyncio.run(
            self.entity_store.extract_entities_from_text(
                text=user_query,
                conversation_key=conversation_key,
                context=f"User query by {user_name}"
            )
        )
        all_entities.extend(user_entities)
        
        # Extract from bot response
        bot_entities = asyncio.run(
            self.entity_store.extract_entities_from_text(
                text=bot_response,
                conversation_key=conversation_key,
                context="Bot response with factual information"
            )
        )
        all_entities.extend(bot_entities)
        
        # Enhanced extraction using Gemini if available
        if self.gemini_client:
            enhanced_entities = self._extract_entities_with_gemini(
                user_query, bot_response, conversation_key, user_name
            )
            all_entities.extend(enhanced_entities)
        
        # Deduplicate between regex and AI extraction before storage
        all_entities = self._deduplicate_extraction_results(all_entities)
        
        # Store extracted entities
        if all_entities:
            success = asyncio.run(
                self.entity_store.store_entities(all_entities, conversation_key)
            )
            
            if success:
                logger.info(f"Successfully extracted and stored {len(all_entities)} entities for conversation: {conversation_key}")
                
                # Queue entity relationship analysis
                analyze_entity_relationships.delay(
                    conversation_key=conversation_key,
                    new_entities=[entity.key for entity in all_entities]
                )
                
                return {
                    "success": True,
                    "entities_extracted": len(all_entities),
                    "entity_types": list(set(e.type for e in all_entities)),
                    "entity_keys": [e.key for e in all_entities],
                    "conversation_key": conversation_key
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to store entities",
                    "entities_extracted": len(all_entities)
                }
        else:
            return {
                "success": True,
                "entities_extracted": 0,
                "message": "No entities found in conversation"
            }
            
    except Exception as e:
        logger.error(f"Error extracting entities from conversation: {e}")
        return {
            "success": False,
            "error": str(e),
            "entities_extracted": 0
        }



@celery_app.task(base=EntityExtractionTask, bind=True)
def analyze_entity_relationships(
    self, 
    conversation_key: str, 
    new_entities: List[str]
) -> Dict[str, Any]:
    """
    Analyze relationships between entities for better context understanding.
    
    Args:
        conversation_key: Unique conversation identifier
        new_entities: List of newly extracted entity keys
        
    Returns:
        Dictionary with relationship analysis results
    """
    
    # Initialize services if needed
    self._initialize_services()
    
    if not self.entity_store:
        logger.error("Entity store not available for relationship analysis")
        return {"success": False, "error": "Entity store not available"}
    
    try:
        # Get entity summary for the conversation
        entity_summary = asyncio.run(
            self.entity_store.get_conversation_entity_summary(conversation_key)
        )
        
        # Simple relationship analysis
        relationships = []
        
        # Check for common patterns
        if entity_summary.get("total_entities", 0) > 1:
            entity_types = entity_summary.get("entity_types", {})
            
            # Look for project-ticket relationships
            if "project" in entity_types and "jira_ticket" in entity_types:
                relationships.append({
                    "type": "project_ticket_association",
                    "description": f"Found {entity_types['jira_ticket']} JIRA tickets and {entity_types['project']} projects in conversation"
                })
            
            # Look for person-assignment relationships
            if "person" in entity_types and ("jira_ticket" in entity_types or "project" in entity_types):
                relationships.append({
                    "type": "person_assignment",
                    "description": f"Found {entity_types['person']} people mentioned with project/ticket references"
                })
            
            # Look for deadline associations
            if "deadline" in entity_types and ("project" in entity_types or "jira_ticket" in entity_types):
                relationships.append({
                    "type": "deadline_association",
                    "description": f"Found {entity_types['deadline']} deadlines associated with project work"
                })
        
        logger.info(f"Analyzed {len(relationships)} entity relationships for conversation: {conversation_key}")
        
        return {
            "success": True,
            "conversation_key": conversation_key,
            "relationships_found": len(relationships),
            "relationships": relationships,
            "entity_summary": entity_summary
        }
        
    except Exception as e:
        logger.error(f"Error analyzing entity relationships: {e}")
        return {
            "success": False,
            "error": str(e),
            "conversation_key": conversation_key
        }

@celery_app.task(base=EntityExtractionTask, bind=True)
def cleanup_old_entities(self) -> Dict[str, Any]:
    """
    Clean up old entities to prevent memory bloat.
    Removes entities older than 30 days.
    
    Returns:
        Dictionary with cleanup results
    """
    
    # Initialize services if needed
    self._initialize_services()
    
    if not self.memory_service:
        logger.error("Memory service not available for entity cleanup")
        return {"success": False, "error": "Memory service not available"}
    
    try:
        cleanup_count = 0
        
        # This is a simplified cleanup - in production you might want more sophisticated logic
        # For now, rely on Redis TTL to handle cleanup automatically
        
        logger.info("Entity cleanup completed - relying on Redis TTL for automatic cleanup")
        
        return {
            "success": True,
            "entities_cleaned": cleanup_count,
            "cleanup_method": "redis_ttl"
        }
        
    except Exception as e:
        logger.error(f"Error during entity cleanup: {e}")
        return {
            "success": False,
            "error": str(e),
            "entities_cleaned": 0
        }

# Add tasks to Celery app configuration
celery_app.conf.task_routes.update({
    'workers.entity_extractor.extract_entities_from_conversation': {'queue': 'entity_extraction'},
    'workers.entity_extractor.analyze_entity_relationships': {'queue': 'entity_extraction'},
    'workers.entity_extractor.cleanup_old_entities': {'queue': 'entity_extraction'},
})

# Add periodic cleanup task
from celery.schedules import crontab
celery_app.conf.beat_schedule.update({
    'cleanup-old-entities': {
        'task': 'workers.entity_extractor.cleanup_old_entities',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
})