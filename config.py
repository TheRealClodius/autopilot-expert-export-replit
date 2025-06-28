"""
Configuration settings for the multi-agent system.
Manages environment variables and system configuration.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Slack Configuration
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_BOT_USER_ID: str = os.getenv("SLACK_BOT_USER_ID", "")
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
    
    # Channels to monitor for ingestion (comma-separated)
    SLACK_CHANNELS_TO_MONITOR: str = os.getenv("SLACK_CHANNELS_TO_MONITOR", "")
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "uipath-slack-chatter")
    
    # Perplexity Configuration
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    
    # Redis Configuration (optional - fallback to in-memory cache if not available)
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Celery Configuration (disabled for Cloud Run deployment)
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "")
    
    # System Configuration
    MAX_CHUNK_SIZE: int = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "384"))
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
    
    # Memory Configuration
    SHORT_TERM_MEMORY_TTL: int = int(os.getenv("SHORT_TERM_MEMORY_TTL", "3600"))  # 1 hour
    CONVERSATION_MEMORY_TTL: int = int(os.getenv("CONVERSATION_MEMORY_TTL", "86400"))  # 24 hours
    
    # Agent Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # LangSmith Configuration
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "autopilot-expert-multi-agent")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    
    def get_monitored_channels(self) -> List[str]:
        """Get list of channels to monitor for data ingestion"""
        if not self.SLACK_CHANNELS_TO_MONITOR:
            return []
        return [ch.strip() for ch in self.SLACK_CHANNELS_TO_MONITOR.split(",")]
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()

# Validate required configuration
def validate_config():
    """Validate that all required configuration is present"""
    # Core required variables for basic operation
    required_vars = [
        "SLACK_BOT_TOKEN",
        "GEMINI_API_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Validate configuration on import
validate_config()
