"""
OpenAI Provider.
Supports GPT-4o, GPT-4, GPT-3.5, and embedding models.
"""

import os
from typing import List, Dict, Any, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from .base import BaseProvider, ProviderCapabilities


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI models."""
    
    DEFAULT_CHAT_MODEL = "gpt-4.1-mini"  # Latest per LangChain docs
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL")
        )
        self._chat_model = self.DEFAULT_CHAT_MODEL
        self._embedding_model = self.DEFAULT_EMBEDDING_MODEL
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_streaming=True,
            supports_embeddings=True,
            supports_vision=True,
            supports_function_calling=True,
            max_context_length=128000,  # GPT-4 supports 128K tokens
            available_chat_models=[
                # GPT-5 (Latest)
                "gpt-5",
                "gpt-5-nano",
                # GPT-4.1 (Current)
                "gpt-4.1",
                "gpt-4.1-mini",
                # GPT-4o
                "gpt-4o",
                "gpt-4o-mini",
                # Older
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo",
                # Reasoning models
                "o1",
                "o1-mini",
            ],
            available_embedding_models=[
                "text-embedding-3-small",
                "text-embedding-3-large",
                "text-embedding-ada-002",
            ]
        )
    
    def get_chat_model(self, model_name: Optional[str] = None) -> BaseChatModel:
        """Get a LangChain ChatOpenAI instance."""
        kwargs = {
            "model": model_name or self._chat_model,
            "openai_api_key": self.api_key,
            "temperature": 0.7,
        }
        if self.base_url:
            kwargs["openai_api_base"] = self.base_url
        return ChatOpenAI(**kwargs)
    
    def get_embeddings(self, model_name: Optional[str] = None) -> Embeddings:
        """Get a LangChain OpenAIEmbeddings instance."""
        kwargs = {
            "model": model_name or self._embedding_model,
            "openai_api_key": self.api_key,
        }
        if self.base_url:
            kwargs["openai_api_base"] = self.base_url
        return OpenAIEmbeddings(**kwargs)
    
    async def list_models(self) -> List[str]:
        """List available OpenAI models."""
        # OpenAI has a models list API, but for simplicity return known models
        return self.capabilities.available_chat_models
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from OpenAI."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        # Convert dict messages to LangChain format
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
        
        model = self.get_chat_model(model_name)
        
        async for chunk in model.astream(lc_messages):
            if chunk.content:
                yield chunk.content
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API status."""
        if not self.api_key:
            return {"status": "error", "message": "API key not configured", "code": "missing_api_key"}
            
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            # Listing models is a good way to check auth without spending tokens
            await client.models.list()
            return {"status": "ok", "message": "OpenAI is healthy"}
        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg:
                return {"status": "error", "message": "Insufficient quota. Please check your billing.", "code": "insufficient_quota"}
            return {"status": "error", "message": error_msg, "code": "api_error"}

    def is_configured(self) -> bool:
        """Check if OpenAI API key is set."""
        return bool(self.api_key)
