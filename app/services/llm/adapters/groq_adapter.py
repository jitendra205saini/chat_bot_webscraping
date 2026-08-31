"""
Groq's API is OpenAI-compatible, so this adapter reuses the OpenAI SDK
pointed at Groq's base URL instead of adding a separate client library.
"""

from typing import List, Optional

from .base import ChatResult, Message, ProviderAdapter

DEFAULT_MODEL = "openai/gpt-oss-120b"  # Groq's free-tier lineup changes often — check console.groq.com/docs/models
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqAdapter(ProviderAdapter):
    async def chat(
        self, messages: List[Message], api_key: str, model: Optional[str] = None
    ) -> ChatResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        response = await client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            max_tokens=1024,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )

        choice = response.choices[0].message
        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        return ChatResult(content=choice.content or "", model_used=response.model, usage=usage)
