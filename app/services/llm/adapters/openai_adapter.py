"""
OpenAI's chat completions format matches our normalized Message shape
almost exactly — system/user/assistant all go straight into one
messages array, no extraction needed. This is the simplest adapter.
"""

from typing import List, Optional

from .base import ChatResult, Message, ProviderAdapter

DEFAULT_MODEL = "gpt-5.6"  # OpenAI ships new model versions often — check platform.openai.com/docs/models


class OpenAIAdapter(ProviderAdapter):
    async def chat(
        self, messages: List[Message], api_key: str, model: Optional[str] = None
    ) -> ChatResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
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
