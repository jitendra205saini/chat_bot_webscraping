"""
Every provider adapter implements the same interface:

    chat(messages, api_key, model) -> ChatResult

regardless of how different the underlying provider's actual API looks.
This is the whole point of the adapter pattern: /chat and /research never
touch a provider's SDK or REST format directly — they only ever talk to
this interface, so adding a fifth provider later means writing one new
adapter file, not touching main.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatResult:
    content: str
    model_used: str
    usage: dict = field(default_factory=dict)


class ProviderAdapter(ABC):
    @abstractmethod
    async def chat(
        self, messages: List[Message], api_key: str, model: Optional[str] = None
    ) -> ChatResult:
        ...
