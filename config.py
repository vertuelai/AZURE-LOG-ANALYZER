"""Configuration management for Azure Log Analytics Analyzer."""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret_from_keyvault(vault_url: str, secret_name: str):
    """Retrieve a secret from Azure Key Vault."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret = client.get_secret(secret_name)
        return secret.value
    except Exception as e:
        print(f"Warning: Could not retrieve secret '{secret_name}' from Key Vault: {e}")
        return None


class Config:
    """Application configuration."""
    
    # Azure Log Analytics
    WORKSPACE_ID = os.getenv("AZURE_LOG_ANALYTICS_WORKSPACE_ID")
    
    # Azure Authentication
    TENANT_ID = os.getenv("AZURE_TENANT_ID")
    CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    
    # Azure Key Vault Configuration
    KEY_VAULT_URL = os.getenv("AZURE_KEY_VAULT_URL")  # e.g., https://your-vault.vault.azure.net/
    
    # OpenAI Configuration (for natural language queries)
    # First try Key Vault, then fall back to environment variables
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    _openai_api_key = None
    _azure_openai_key = None
    
    @classmethod
    def _load_openai_keys(cls):
        """Load OpenAI keys from Key Vault or environment variables."""
        # Try Key Vault first if configured
        if cls.KEY_VAULT_URL:
            if cls._openai_api_key is None:
                cls._openai_api_key = _get_secret_from_keyvault(cls.KEY_VAULT_URL, "OPENAI-API-KEY")
            if cls._azure_openai_key is None:
                cls._azure_openai_key = _get_secret_from_keyvault(cls.KEY_VAULT_URL, "AZURE-OPENAI-KEY")
        
        # Fall back to environment variables if Key Vault didn't provide values
        if cls._openai_api_key is None:
            cls._openai_api_key = os.getenv("OPENAI_API_KEY")
        if cls._azure_openai_key is None:
            cls._azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
    
    @classmethod
    @property
    def OPENAI_API_KEY(cls):
        """Get OpenAI API key from Key Vault or environment variable."""
        cls._load_openai_keys()
        return cls._openai_api_key
    
    @classmethod
    @property
    def AZURE_OPENAI_KEY(cls):
        """Get Azure OpenAI key from Key Vault or environment variable."""
        cls._load_openai_keys()
        return cls._azure_openai_key
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.WORKSPACE_ID:
            raise ValueError("AZURE_LOG_ANALYTICS_WORKSPACE_ID is required")
        return True
    
    @classmethod
    def has_openai(cls):
        """Check if OpenAI is configured."""
        cls._load_openai_keys()
        return bool(cls._openai_api_key or (cls.AZURE_OPENAI_ENDPOINT and cls._azure_openai_key))
