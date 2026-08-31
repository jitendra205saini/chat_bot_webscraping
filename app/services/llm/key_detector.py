"""
Detects which LLM provider an API key belongs to.

Primary method: prefix matching. Every major provider's keys have a
distinct, documented shape, so this resolves almost every real key
instantly with zero network calls:

    Anthropic  sk-ant-...
    OpenAI     sk-... or sk-proj-...   (checked AFTER Anthropic, since
                                         Anthropic keys also start "sk-")
    Gemini     AIzaSy...
    Groq       gsk_...

If a key doesn't match any known shape, we return unknown rather than
guessing — silently trying a key against every provider in turn wastes
quota and looks like credential stuffing to their abuse systems. The
caller should return a clear "couldn't identify this key" error.

validate_key() is a separate, optional step: an actual authenticated
call to confirm a key that *looks* right also *works*. Used by
/detect-key when the caller wants real confirmation, not just a format
guess.
"""

import re
from dataclasses import dataclass
from typing import Optional

import httpx

# Order matters: Anthropic must be checked before the generic OpenAI
# pattern, since "sk-ant-..." would otherwise also match "starts with sk-".
_PATTERNS = [
    ("anthropic", re.compile(r"^sk-ant-")),
    ("openai", re.compile(r"^sk-(proj-)?[A-Za-z0-9_-]{20,}$")),
    ("gemini", re.compile(r"^AIzaSy[A-Za-z0-9_-]{20,}$")),
    ("groq", re.compile(r"^gsk_[A-Za-z0-9]{20,}$")),
]


@dataclass
class DetectionResult:
    provider: Optional[str]
    confidence: str  # "high" (prefix matched) | "none" (unrecognized)


def detect_provider(api_key: str) -> DetectionResult:
    api_key = api_key.strip()
    for provider, pattern in _PATTERNS:
        if pattern.match(api_key):
            return DetectionResult(provider=provider, confidence="high")
    return DetectionResult(provider=None, confidence="none")


async def validate_key(provider: str, api_key: str, timeout: float = 8.0) -> bool:
    """
    Makes one lightweight authenticated call to confirm the key actually
    works, not just that it's shaped correctly. Returns True/False —
    never raises, so a network hiccup here doesn't crash detection.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "anthropic":
                r = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )
            elif provider == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elif provider == "gemini":
                r = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                )
            elif provider == "groq":
                r = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            else:
                return False
        return r.status_code == 200
    except Exception:
        return False
