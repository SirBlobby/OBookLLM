"""
Anthropic Claude Provider.
Supports Claude 3 Opus, Sonnet, and Haiku models.
"""

import os
from typing import List, Dict, Any, Optional, AsyncGenerator

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from .base import BaseProvider, ProviderCapabilities


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""
    
    DEFAULT_CHAT_MODEL = "claude-sonnet-4-5-20250929"  # Latest per LangChain docs
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self._chat_model = self.DEFAULT_CHAT_MODEL
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_streaming=True,
            supports_embeddings=False,  # Anthropic doesn't provide embeddings
            supports_vision=True,
            supports_function_calling=True,
            max_context_length=200000,  # Claude supports 200K tokens
            available_chat_models=[
                # Claude 4.5 (Latest per LangChain docs)
                "claude-sonnet-4-5-20250929",
                "claude-haiku-4-5-20251001",
                # Claude 3.5
                "claude-3-5-sonnet-latest",
                "claude-3-5-haiku-latest",
                # Claude 3
                "claude-3-opus-latest",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            available_embedding_models=[]  # No embeddings
        )
    
    def get_chat_model(self, model_name: Optional[str] = None) -> BaseChatModel:
        """Get a LangChain ChatAnthropic instance."""
        return ChatAnthropic(
            model=model_name or self._chat_model,
            anthropic_api_key=self.api_key,
            temperature=0.7,
        )
    
    def get_embeddings(self, model_name: Optional[str] = None) -> Embeddings:
        """Anthropic doesn't provide embeddings. Raises NotImplementedError."""
        raise NotImplementedError(
            "Anthropic does not provide embedding models. "
            "Use a different provider (Ollama, OpenAI, or Gemini) for embeddings."
        )
    
    async def list_models(self) -> List[str]:
        """List available Claude models."""
        return self.capabilities.available_chat_models
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from Claude."""
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
        """Check Anthropic API status."""
        if not self.api_key:
            return {"status": "error", "message": "API key not configured", "code": "missing_api_key"}
            
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            # Anthropic doesn't have a cheap list_models API. 
            # We must make a minimal call, e.g. completion with max_tokens=1
            await client.messages.create(
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
                model=self._chat_model
            )
            return {"status": "ok", "message": "Anthropic is healthy"}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": "api_error"}

    def is_configured(self) -> bool:
        """Check if Anthropic API key is set."""
        return bool(self.api_key)
