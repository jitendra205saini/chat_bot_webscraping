"""
The single lookup table from provider name to adapter. main.py never
imports an individual adapter directly — it always goes through here.
Adding a fifth provider means: write the adapter file, add one line
below, done.
"""

from typing import Dict

from .base import ProviderAdapter
from .anthropic_adapter import AnthropicAdapter
from .openai_adapter import OpenAIAdapter
from .gemini_adapter import GeminiAdapter
from .groq_adapter import GroqAdapter

_REGISTRY: Dict[str, ProviderAdapter] = {
    "anthropic": AnthropicAdapter(),
    "openai": OpenAIAdapter(),
    "gemini": GeminiAdapter(),
    "groq": GroqAdapter(),
}


def get_adapter(provider: str) -> ProviderAdapter:
    if provider not in _REGISTRY:
        raise ValueError(
            f"No adapter for provider '{provider}'. Supported: {', '.join(_REGISTRY)}"
        )
    return _REGISTRY[provider]
