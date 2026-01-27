import openai
from typing import Optional
from app.config import Config

class LLMClient:
    """LLM client factory"""
    
    _instance = None
    
    @classmethod
    def get_client(cls):
        """Get or create LLM client instance"""
        if cls._instance is None:
            cls._instance = cls._create_client()
        return cls._instance
    
    @staticmethod
    def _create_client():
        """Create LLM client based on provider"""
        if Config.PROVIDER == "azure":
            return openai.AzureOpenAI(
                api_key=Config.AZURE_API_KEY,
                api_version=Config.AZURE_API_VERSION,
                azure_endpoint=Config.AZURE_ENDPOINT
            )
        else:  # openai
            return openai.OpenAI(
                api_key=Config.OPENAI_API_KEY
            )
    
    @property
    def model(self):
        """Get model name"""
        if Config.PROVIDER == "azure":
            return Config.AZURE_DEPLOYMENT_NAME
        return Config.AZURE_DEPLOYMENT_MODEL