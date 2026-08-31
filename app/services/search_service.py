"""
Search layer.

Responsible for one thing: given a topic/question, find the best matching
pages on the open web. We use Tavily because it's built for AI agents —
unlike raw Google/Bing APIs, it already returns clean, relevance-ranked
results (and optionally pre-extracted page text), so we don't have to
build our own ranking logic.
"""

from typing import Dict, List

import httpx

from app.config import settings

TAVILY_URL = "https://api.tavily.com/search"


async def search_web(query: str, max_results: int) -> List[Dict]:
    """
    Returns a list of result dicts, each shaped like:
        {
            "title": str,
            "url": str,
            "content": str,        # short relevance snippet
            "raw_content": str|None,  # fuller page text, if Tavily has it
            "score": float,
        }
    Raises RuntimeError if the API key is missing, or httpx.HTTPStatusError
    if Tavily itself returns an error.
    """
    if not settings.TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Add it to your .env file (see .env.example)."
        )

    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",  # better ranking, slightly slower
        "include_raw_content": True,  # ask Tavily for full text when it has it
    }

    async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(TAVILY_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    return data.get("results", [])
