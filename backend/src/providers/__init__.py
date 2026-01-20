"""
AI Provider Controllers for OBookLLM.
Supports multiple AI providers: Ollama (local), OpenAI, Google Gemini, Anthropic Claude.
"""

from .base import BaseProvider, ProviderCapabilities
from .registry import ProviderRegistry, get_provider

__all__ = [
    "BaseProvider",
    "ProviderCapabilities", 
    "ProviderRegistry",
    "get_provider"
]
