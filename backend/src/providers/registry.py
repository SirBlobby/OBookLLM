"""
Provider Registry - Factory for getting the right provider.
Manages provider instances and configuration.
"""

import os
from typing import Dict, Optional, Type
from .base import BaseProvider
from .ollama import OllamaProvider
from .gemini import GeminiProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider


class ProviderRegistry:
    """
    Registry for AI providers.
    Manages provider instances and handles selection of chat and embedding providers.
    """
    
    # Map of provider names to classes
    PROVIDERS: Dict[str, Type[BaseProvider]] = {
        "ollama": OllamaProvider,
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
    }
    
    def __init__(self):
        self._instances: Dict[str, BaseProvider] = {}
        self._chat_provider_name: str = "ollama"  # Default
        self._chat_model: Optional[str] = None
        self._embedding_provider_name: str = "ollama"  # Default
        self._embedding_model: Optional[str] = None
    
    def get_provider(self, name: str) -> BaseProvider:
        """
        Get a provider instance by name.
        Creates the instance if it doesn't exist.
        """
        if name not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {name}. Available: {list(self.PROVIDERS.keys())}")
        
        if name not in self._instances:
            self._instances[name] = self.PROVIDERS[name]()
        
        return self._instances[name]
    
    def set_chat_provider(self, provider_name: str, model_name: Optional[str] = None):
        """Set the active chat provider and optionally the model."""
        if provider_name not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")
        self._chat_provider_name = provider_name
        self._chat_model = model_name
        
        # Also update the provider's default model if specified
        if model_name:
            provider = self.get_provider(provider_name)
            provider.set_chat_model(model_name)
    
    def set_embedding_provider(self, provider_name: str, model_name: Optional[str] = None):
        """Set the active embedding provider and optionally the model."""
        if provider_name not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        # Check if the provider supports embeddings
        provider = self.get_provider(provider_name)
        if not provider.capabilities.supports_embeddings:
            raise ValueError(f"Provider {provider_name} does not support embeddings")
        
        self._embedding_provider_name = provider_name
        self._embedding_model = model_name
        
        if model_name:
            provider.set_embedding_model(model_name)
    
    def get_chat_provider(self) -> BaseProvider:
        """Get the currently active chat provider."""
        return self.get_provider(self._chat_provider_name)
    
    def get_embedding_provider(self) -> BaseProvider:
        """Get the currently active embedding provider."""
        return self.get_provider(self._embedding_provider_name)
    
    def get_chat_model_name(self) -> Optional[str]:
        """Get the current chat model name."""
        return self._chat_model
    
    def get_embedding_model_name(self) -> Optional[str]:
        """Get the current embedding model name."""
        return self._embedding_model
    
    def list_providers(self) -> Dict[str, dict]:
        """List all available providers with their status."""
        result = {}
        for name, cls in self.PROVIDERS.items():
            provider = self.get_provider(name)
            result[name] = {
                "name": name,
                "configured": provider.is_configured(),
                "capabilities": {
                    "chat": provider.capabilities.supports_chat,
                    "streaming": provider.capabilities.supports_streaming,
                    "embeddings": provider.capabilities.supports_embeddings,
                    "vision": provider.capabilities.supports_vision,
                    "function_calling": provider.capabilities.supports_function_calling,
                },
                "available_chat_models": provider.capabilities.available_chat_models,
                "available_embedding_models": provider.capabilities.available_embedding_models,
            }
        return result
    
    def configure_from_settings(self, settings: dict):
        """
        Configure providers from settings dict.
        
        Expected format:
        {
            "chat_provider": "ollama",
            "chat_model": "llama3",
            "embedding_provider": "ollama",
            "embedding_model": "nomic-embed-text",
            "api_keys": {
                "openai": "sk-...",
                "anthropic": "sk-ant-...",
                "gemini": "AI..."
            }
        }
        """
        # Set API keys first
        api_keys = settings.get("api_keys", {})
        for provider_name, api_key in api_keys.items():
            if provider_name in self._instances:
                self._instances[provider_name].api_key = api_key
            elif provider_name in self.PROVIDERS:
                # Pre-create with API key
                self._instances[provider_name] = self.PROVIDERS[provider_name](api_key=api_key)
        
        # Set chat provider
        chat_provider = settings.get("chat_provider", "ollama")
        chat_model = settings.get("chat_model")
        self.set_chat_provider(chat_provider, chat_model)
        
        # Set embedding provider
        embedding_provider = settings.get("embedding_provider", "ollama")
        embedding_model = settings.get("embedding_model")
        try:
            self.set_embedding_provider(embedding_provider, embedding_model)
        except ValueError:
            # Fallback to Ollama if provider doesn't support embeddings
            self.set_embedding_provider("ollama", embedding_model)


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def get_provider(name: str) -> BaseProvider:
    """Convenience function to get a provider by name."""
    return get_registry().get_provider(name)
