"""
Abstract base class for AI providers.
Defines the interface that all providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Generator, Optional, AsyncGenerator
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


@dataclass
class ProviderCapabilities:
    """Describes what a provider can do."""
    supports_chat: bool = True
    supports_streaming: bool = True
    supports_embeddings: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False
    max_context_length: int = 4096
    available_chat_models: List[str] = field(default_factory=list)
    available_embedding_models: List[str] = field(default_factory=list)


class BaseProvider(ABC):
    """
    Abstract base class for AI providers.
    Each provider (Ollama, OpenAI, Gemini, Claude) must implement this interface.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self._chat_model: Optional[str] = None
        self._embedding_model: Optional[str] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        pass
    
    @abstractmethod
    def get_chat_model(self, model_name: Optional[str] = None) -> BaseChatModel:
        """
        Get a LangChain chat model instance.
        
        Args:
            model_name: Specific model to use, or None for default.
            
        Returns:
            A LangChain BaseChatModel instance.
        """
        pass
    
    @abstractmethod
    def get_embeddings(self, model_name: Optional[str] = None) -> Embeddings:
        """
        Get a LangChain embeddings instance.
        
        Args:
            model_name: Specific model to use, or None for default.
            
        Returns:
            A LangChain Embeddings instance.
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models from the provider."""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model_name: Specific model to use.
            **kwargs: Additional parameters.
            
        Yields:
            Text chunks as they are generated.
        """
        pass
    
    async def embed_text(self, text: str, model_name: Optional[str] = None) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text to embed.
            model_name: Specific model to use.
            
        Returns:
            List of floats representing the embedding vector.
        """
        embeddings = self.get_embeddings(model_name)
        return await embeddings.aembed_query(text)
    
    async def embed_documents(self, texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed.
            model_name: Specific model to use.
            
        Returns:
            List of embedding vectors.
        """
        embeddings = self.get_embeddings(model_name)
        return await embeddings.aembed_documents(texts)
    
    def set_chat_model(self, model_name: str):
        """Set the default chat model."""
        self._chat_model = model_name
    
    def set_embedding_model(self, model_name: str):
        """Set the default embedding model."""
        self._embedding_model = model_name
    
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        return True  # Override in subclasses that require API keys
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the provider is healthy and working.
        Returns a dict with 'status' ("ok" or "error"), 'message', and 'code'.
        """
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(configured={self.is_configured()})>"
