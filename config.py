"""Configuration management for Azure Log Analytics Analyzer."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Azure Log Analytics
    WORKSPACE_ID = os.getenv("AZURE_LOG_ANALYTICS_WORKSPACE_ID")
    
    # Azure Authentication
    TENANT_ID = os.getenv("AZURE_TENANT_ID")
    CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    
    # OpenAI Configuration (for natural language queries)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.WORKSPACE_ID:
            raise ValueError("AZURE_LOG_ANALYTICS_WORKSPACE_ID is required")
        return True
    
    @classmethod
    def has_openai(cls):
        """Check if OpenAI is configured."""
        return bool(cls.OPENAI_API_KEY or (cls.AZURE_OPENAI_ENDPOINT and cls.AZURE_OPENAI_KEY))
