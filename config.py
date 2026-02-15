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
    
    # Azure OpenAI Configuration (for natural language queries)
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.WORKSPACE_ID:
            raise ValueError("AZURE_LOG_ANALYTICS_WORKSPACE_ID is required")
        return True
    
    @classmethod
    def has_openai(cls):
        """Check if Azure OpenAI is configured."""
        return bool(cls.AZURE_OPENAI_ENDPOINT and cls.AZURE_OPENAI_KEY)
