"""
Gemini differs from the other two providers in two ways: it calls the
assistant role "model" instead of "assistant", and system instructions
go in a separate `systemInstruction` field, similar to Anthropic. We
call the REST API directly with httpx rather than adding Google's SDK
as a dependency — one plain POST is all this needs.

Gemini's model lineup moves fast — three generations shipped in the
first half of 2026 alone, and Google has since deprecated the old
"-latest" alias pattern entirely (it now 404s). Pin an explicit,
currently-stable model instead and check ai.google.dev/gemini-api/docs/models
if this ever starts erroring.
"""

from typing import List, Optional

import httpx

from .base import ChatResult, Message, ProviderAdapter

DEFAULT_MODEL = "gemini-2.5-flash"  # see ai.google.dev/gemini-api/docs/models for the current list
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiAdapter(ProviderAdapter):
    async def chat(
        self, messages: List[Message], api_key: str, model: Optional[str] = None
    ) -> ChatResult:
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
            if m.role in ("user", "assistant")
        ]

        payload = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        model_name = model or DEFAULT_MODEL
        url = f"{GEMINI_BASE}/models/{model_name}:generateContent?key={api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidate = data["candidates"][0]
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])

        usage_meta = data.get("usageMetadata", {})
        usage = {
            "input_tokens": usage_meta.get("promptTokenCount", 0),
            "output_tokens": usage_meta.get("candidatesTokenCount", 0),
        }
        return ChatResult(content=text, model_used=model_name, usage=usage)
