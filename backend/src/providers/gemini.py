"""
Google Gemini Provider.
Uses the google-genai SDK (newer SDK with proper async support).
"""

import os
from typing import List, Dict, Any, Optional, AsyncGenerator

from google import genai
from google.genai import types
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from .base import BaseProvider, ProviderCapabilities


class GeminiEmbeddings(Embeddings):
    """Embeddings wrapper using google-genai SDK."""
    
    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
        )
        return [e.values for e in response.embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return response.embeddings[0].values


class GeminiProvider(BaseProvider):
    """Provider for Google Gemini models using google-genai SDK."""
    
    DEFAULT_CHAT_MODEL = "gemini-1.5-flash"
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        self._chat_model = self.DEFAULT_CHAT_MODEL
        self._embedding_model = self.DEFAULT_EMBEDDING_MODEL
        self._client: Optional[genai.Client] = None
    
    def _get_client(self) -> genai.Client:
        """Get or create the Google GenAI client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client
    
    def _refresh_client(self):
        """Force refresh of the client (when API key changes)."""
        self._client = genai.Client(api_key=self.api_key)
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_streaming=True,
            supports_embeddings=True,
            supports_vision=True,
            supports_function_calling=True,
            max_context_length=1048576,  # 1M tokens
            available_chat_models=[
                "gemini-2.5-pro",
                "gemini-3-flash-preview",
                "gemini-3-pro-preview"
            ],
            available_embedding_models=[
                "gemini-embedding-001",
            ]
        )
    
    def get_chat_model(self, model_name: Optional[str] = None) -> BaseChatModel:
        """Get a LangChain ChatGoogleGenerativeAI instance."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name or self._chat_model,
                google_api_key=self.api_key,
                temperature=0.7,
                convert_system_message_to_human=True
            )
        except ImportError:
            raise ImportError("langchain-google-genai is required for get_chat_model")
    
    def get_embeddings(self, model_name: Optional[str] = None) -> Embeddings:
        """Get embeddings using google-genai SDK."""
        return GeminiEmbeddings(
            api_key=self.api_key,
            model=model_name or self._embedding_model
        )
    
    async def list_models(self) -> List[str]:
        """List available Gemini models."""
        return self.capabilities.available_chat_models
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from Gemini using google-genai SDK."""
        model = model_name or self._chat_model
        self._refresh_client()
        client = self._get_client()
        
        # Build contents list and extract system instruction
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)]
                ))
            elif role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)]
                ))
        
        # Build config
        config = types.GenerateContentConfig(
            temperature=0.7,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        
        # Use async streaming
        try:
            async for chunk in await client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            error_msg = str(e)
            print(f"Gemini async streaming error: {error_msg}")
            
            # Fallback to sync streaming
            try:
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                ):
                    if chunk.text:
                        yield chunk.text
            except Exception as e2:
                raise Exception(f"Gemini error: {e2}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Gemini API status."""
        if not self.api_key:
            return {"status": "error", "message": "API key not configured", "code": "missing_api_key"}
            
        try:
            client = self._get_client()
            # Simple metadata query to list models
            # We use an async iterator if available or sync fallback
            # but list() on the pager shouldn't cost money
            list(client.models.list(config={"page_size": 1}))
            return {"status": "ok", "message": "Gemini is healthy"}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": "api_error"}

    def is_configured(self) -> bool:
        """Check if Gemini API key is set."""
        return bool(self.api_key)
