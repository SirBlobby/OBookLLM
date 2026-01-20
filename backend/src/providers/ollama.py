"""
Ollama Provider - Local LLM support.
Connects to a local or remote Ollama instance.
"""

import os
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from .base import BaseProvider, ProviderCapabilities


class OllamaProvider(BaseProvider):
    """Provider for Ollama (local LLMs)."""
    
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_CHAT_MODEL = "llama3"
    DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
    
    def __init__(self, base_url: Optional[str] = None):
        super().__init__(base_url=base_url or os.getenv("OLLAMA_HOST", self.DEFAULT_HOST))
        self._chat_model = self.DEFAULT_CHAT_MODEL
        self._embedding_model = self.DEFAULT_EMBEDDING_MODEL
        self._capabilities = None
    
    @property
    def name(self) -> str:
        return "ollama"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        if self._capabilities is None:
            self._capabilities = ProviderCapabilities(
                supports_chat=True,
                supports_streaming=True,
                supports_embeddings=True,
                supports_vision=True,  # Some Ollama models support vision
                supports_function_calling=False,
                max_context_length=8192,
            )
        return self._capabilities
    
    def get_chat_model(self, model_name: Optional[str] = None) -> BaseChatModel:
        """Get a LangChain ChatOllama instance."""
        return ChatOllama(
            model=model_name or self._chat_model,
            base_url=self.base_url,
            temperature=0.7,
        )
    
    def get_embeddings(self, model_name: Optional[str] = None) -> Embeddings:
        """Get a LangChain OllamaEmbeddings instance."""
        return OllamaEmbeddings(
            model=model_name or self._embedding_model,
            base_url=self.base_url,
        )
    
    async def list_models(self) -> List[str]:
        """List available models from Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            print(f"Error listing Ollama models: {e}")
        return []
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from Ollama."""
        import json
        
        model = model_name or self._chat_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama servier is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    return {"status": "ok", "message": "Ollama is reachable"}
                else:
                    return {"status": "error", "message": f"Ollama returned {response.status_code}", "code": "http_error"}
        except Exception as e:
            return {"status": "error", "message": f"Could not connect to Ollama: {e}", "code": "connection_error"}

    def is_configured(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
