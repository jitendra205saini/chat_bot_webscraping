"""
Anthropic's messages API only accepts alternating user/assistant turns —
system instructions go in a separate top-level `system` parameter, not
inside the messages list. Every other provider we support puts system
messages inline in the message array, so this extraction step is unique
to this adapter.
"""

from typing import List, Optional

from .base import ChatResult, Message, ProviderAdapter

DEFAULT_MODEL = "claude-sonnet-5"  # check docs.claude.com/en/docs/about-claude/models for the current list


class AnthropicAdapter(ProviderAdapter):
    async def chat(
        self, messages: List[Message], api_key: str, model: Optional[str] = None
    ) -> ChatResult:
        import anthropic

        system_parts = [m.content for m in messages if m.role == "system"]
        turns = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]

        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=1024,
            system="\n\n".join(system_parts) if system_parts else anthropic.NOT_GIVEN,
            messages=turns,
        )

        text = "".join(block.text for block in response.content if block.type == "text")
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return ChatResult(content=text, model_used=response.model, usage=usage)
