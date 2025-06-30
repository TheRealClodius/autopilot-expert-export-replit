"""
Pydantic schemas for data validation and API contracts.
Defines data models for Slack events, processed messages, and system responses.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

class SlackEvent(BaseModel):
    """Schema for incoming Slack event data"""
    token: Optional[str] = None
    team_id: Optional[str] = None
    api_app_id: Optional[str] = None
    event: Dict[str, Any]
    type: str
    event_id: Optional[str] = None
    event_time: Optional[int] = None
    
    class Config:
        extra = "allow"

class SlackChallenge(BaseModel):
    """Schema for Slack URL verification challenge"""
    token: str
    challenge: str
    type: str

class ProcessedMessage(BaseModel):
    """Schema for processed Slack messages"""
    text: str
    user_id: str
    user_name: str
    user_email: Optional[str] = ""
    user_display_name: Optional[str] = ""
    user_first_name: Optional[str] = ""
    user_title: Optional[str] = ""
    user_department: Optional[str] = ""
    channel_id: str
    channel_name: str
    is_dm: bool = False
    is_mention: bool = False
    thread_ts: Optional[str] = None
    message_ts: str
    
    class Config:
        extra = "allow"

class VectorSearchRequest(BaseModel):
    """Schema for vector search requests"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True

class VectorSearchResult(BaseModel):
    """Schema for vector search results"""
    id: str
    score: float = Field(..., ge=0.0, le=1.0)
    content: str
    metadata: Dict[str, Any] = {}
    source: Optional[str] = None
    timestamp: Optional[str] = None

class GraphQueryRequest(BaseModel):
    """Schema for graph query requests"""
    query: str = Field(..., min_length=1, max_length=500)
    query_type: Optional[str] = None

class GraphNode(BaseModel):
    """Schema for graph nodes"""
    id: str
    type: str
    properties: Dict[str, Any] = {}
    created: Optional[str] = None

class GraphRelationship(BaseModel):
    """Schema for graph relationships"""
    source: str
    target: str
    relationship_type: str
    properties: Dict[str, Any] = {}
    created: Optional[str] = None

class ExecutionPlan(BaseModel):
    """Schema for orchestrator execution plans"""
    analysis: str
    tools_needed: List[str] = []
    vector_queries: List[str] = []
    graph_queries: List[str] = []
    context: Dict[str, Any] = {}
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

class AgentResponse(BaseModel):
    """Schema for agent responses"""
    channel_id: str
    thread_ts: Optional[str] = None
    text: str
    timestamp: str
    agent_type: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ConversationContext(BaseModel):
    """Schema for conversation context storage"""
    conversation_id: str
    messages: List[ProcessedMessage] = []
    context_summary: Optional[str] = None
    participants: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class IngestionMetadata(BaseModel):
    """Schema for data ingestion metadata"""
    timestamp: str
    ingestion_type: str = Field(..., pattern="^(daily|manual|incremental)$")
    channels_processed: int = Field(..., ge=0)
    total_messages_processed: int = Field(..., ge=0)
    total_messages_embedded: int = Field(..., ge=0)
    errors: List[str] = []
    time_range: Dict[str, str]
    processing_time_seconds: Optional[float] = None

class KnowledgeQueueItem(BaseModel):
    """Schema for knowledge update queue items"""
    id: Optional[str] = None
    type: str = Field(..., pattern="^(knowledge_gap|entity_research|manual_task)$")
    description: Optional[str] = None
    entity: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    timestamp: str
    status: str = Field(default="pending", pattern="^(pending|processing|completed|failed)$")
    metadata: Dict[str, Any] = {}

class ObservationData(BaseModel):
    """Schema for Observer Agent observation data"""
    message: Dict[str, Any]
    response: str
    gathered_info: Dict[str, Any]
    timestamp: str
    insights: Optional[Dict[str, Any]] = None
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)

class SystemHealth(BaseModel):
    """Schema for system health status"""
    redis: str = Field(..., pattern="^(healthy|unhealthy|unknown)$")
    celery: str = Field(..., pattern="^(healthy|unhealthy|unknown)$")
    agents: str = Field(..., pattern="^(healthy|unhealthy|unknown)$")
    pinecone: Optional[str] = Field(None, pattern="^(healthy|unhealthy|unknown)$")
    gemini: Optional[str] = Field(None, pattern="^(healthy|unhealthy|unknown)$")
    last_check: str
    uptime_seconds: Optional[float] = None

class MemoryStats(BaseModel):
    """Schema for memory usage statistics"""
    used_memory: int = Field(..., ge=0)
    used_memory_human: str
    used_memory_peak: int = Field(..., ge=0)
    used_memory_peak_human: str
    total_system_memory: Optional[int] = Field(None, ge=0)
    total_system_memory_human: Optional[str] = None

class PineconeStats(BaseModel):
    """Schema for Pinecone index statistics"""
    total_vectors: int = Field(..., ge=0)
    dimension: int = Field(..., ge=0)
    index_fullness: float = Field(..., ge=0.0, le=1.0)
    namespaces: Dict[str, Any] = {}

class SlackMessage(BaseModel):
    """Schema for structured Slack messages"""
    id: str
    text: str
    timestamp: str
    ts: str
    user_id: Optional[str] = None
    user_name: str = "Unknown"
    user_email: Optional[str] = None
    channel_id: str
    channel_name: str = "Unknown"
    channel_purpose: Optional[str] = None
    thread_ts: Optional[str] = None
    is_thread_reply: bool = False
    reply_count: int = Field(default=0, ge=0)
    reactions: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []
    attachments: List[Dict[str, Any]] = []

class ProcessedMessageBatch(BaseModel):
    """Schema for batch of processed messages"""
    messages: List[SlackMessage]
    total_count: int = Field(..., ge=0)
    processed_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    processing_time_seconds: Optional[float] = None
    
    @validator('processed_count', 'failed_count')
    def validate_counts(cls, v, values):
        if 'total_count' in values and v > values['total_count']:
            raise ValueError('Count cannot exceed total_count')
        return v

class EmbeddingBatch(BaseModel):
    """Schema for embedding batch operations"""
    embeddings_generated: int = Field(..., ge=0)
    vectors_stored: int = Field(..., ge=0)
    failed_embeddings: int = Field(..., ge=0)
    processing_time_seconds: Optional[float] = None
    batch_id: Optional[str] = None

class GraphStatistics(BaseModel):
    """Schema for knowledge graph statistics"""
    nodes: int = Field(..., ge=0)
    edges: int = Field(..., ge=0)
    density: float = Field(..., ge=0.0, le=1.0)
    is_connected: bool
    node_types: Dict[str, int] = {}
    relationship_types: Dict[str, int] = {}

class APIError(BaseModel):
    """Schema for API error responses"""
    error: str
    message: str
    timestamp: str
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class TaskResult(BaseModel):
    """Schema for Celery task results"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str
    processing_time_seconds: Optional[float] = None

class UserProfile(BaseModel):
    """Schema for Slack user profiles"""
    id: str
    name: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    is_bot: bool = False
    is_admin: bool = False
    timezone: Optional[str] = None

class ChannelInfo(BaseModel):
    """Schema for Slack channel information"""
    id: str
    name: str
    purpose: Optional[str] = None
    topic: Optional[str] = None
    is_private: bool = False
    member_count: Optional[int] = None
    created: Optional[str] = None
    creator: Optional[str] = None

class ThreadContext(BaseModel):
    """Schema for thread context"""
    thread_ts: str
    parent_message: Optional[SlackMessage] = None
    reply_count: int = Field(default=0, ge=0)
    recent_messages: List[SlackMessage] = []
    participants: List[str] = []

class SearchFilters(BaseModel):
    """Schema for search filters"""
    channel_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None
    has_files: Optional[bool] = None
    has_reactions: Optional[bool] = None
    is_thread: Optional[bool] = None
    message_types: Optional[List[str]] = None

class ResponseMetadata(BaseModel):
    """Schema for response metadata"""
    processing_time_ms: float = Field(..., ge=0)
    tokens_used: Optional[int] = Field(None, ge=0)
    model_used: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    sources_used: List[str] = []
    cache_hit: bool = False
