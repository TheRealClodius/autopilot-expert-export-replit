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
    
    # SAFETY: Disable Slack responses during development/testing
    DISABLE_SLACK_RESPONSES: bool = True  # Set to False only for production use
    
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
    
    # Microsoft Graph/Outlook Configuration
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_TENANT_ID: str = os.getenv("MICROSOFT_TENANT_ID", "")
    MICROSOFT_SCOPE: str = os.getenv("MICROSOFT_SCOPE", "https://graph.microsoft.com/.default")
    
    # Atlassian Configuration
    ATLASSIAN_JIRA_URL: str = os.getenv("ATLASSIAN_JIRA_URL", "")
    ATLASSIAN_JIRA_USERNAME: str = os.getenv("ATLASSIAN_JIRA_USERNAME", "")
    ATLASSIAN_JIRA_TOKEN: str = os.getenv("ATLASSIAN_JIRA_TOKEN", "")
    ATLASSIAN_CONFLUENCE_URL: str = os.getenv("ATLASSIAN_CONFLUENCE_URL", "")
    ATLASSIAN_CONFLUENCE_USERNAME: str = os.getenv("ATLASSIAN_CONFLUENCE_USERNAME", "")
    ATLASSIAN_CONFLUENCE_TOKEN: str = os.getenv("ATLASSIAN_CONFLUENCE_TOKEN", "")
    ATLASSIAN_MCP_URL: str = os.getenv("ATLASSIAN_MCP_URL", "https://mcp.atlassian.com/v1/sse")
    
    # MCP Server Configuration (deployment-aware)
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
    
    # Redis Configuration (DISABLED for deployment - using memory-only fallbacks)
    REDIS_URL: str = ""  # Intentionally empty to force memory cache
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery Configuration (DISABLED for deployment - using memory transport)
    CELERY_BROKER_URL: str = ""  # Intentionally empty to force memory transport
    CELERY_RESULT_BACKEND: str = ""  # Intentionally empty to force memory backend
    
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
    
    # MCP Server Configuration
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", 
        "https://remote-mcp-server-andreiclodius.replit.app" if os.getenv("REPLIT_DEPLOYMENT") 
        else "http://localhost:8001")
    
    @property
    def DEPLOYMENT_AWARE_MCP_URL(self) -> str:
        """Get deployment-aware MCP server URL"""
        # Always use the configured MCP_SERVER_URL for remote server connection
        # This supports separate project deployment architecture
        return self.MCP_SERVER_URL
    
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
