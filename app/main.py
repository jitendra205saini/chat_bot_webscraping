"""
Entry point for the combined AI Agent API.

Two capabilities, one shared core:
    POST /research   -> web search + scrape + grounded answer
    POST /chat        -> multi-turn conversation
Both take the CALLER'S OWN LLM api_key and route through the same
key-detector + adapter-registry pipeline, so we never pay for LLM
inference — only the Tavily search calls in /research use our own
server-side key.

    POST /detect-key            -> identify a key's provider without chatting
    GET  /prompts/suggestions   -> curated example prompts for a blank chat box

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    ChatRequest,
    ChatResponse,
    DetectKeyRequest,
    DetectKeyResponse,
    ResearchRequest,
    ResearchResponse,
    SourceResult,
    SuggestionsResponse,
)
from app.services import scraper_service, search_service
from app.services.llm import key_detector, prompt_library
from app.services.llm.adapters.base import Message
from app.services.llm.adapters.registry import get_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-agent-api")

DEFAULT_RESEARCH_SYSTEM_PROMPT = (
    "You are a research assistant. Answer the user's question using ONLY the "
    "source passages provided below — do not use outside knowledge. Cite "
    "sources inline like [1], [2] matching the source numbers. If the "
    "passages don't fully answer the question, say what's missing instead "
    "of guessing."
)

app = FastAPI(title="AI Agent API", version="2.0.0")

# Wide open by default so any frontend can call it during development.
# Lock this down to your actual domain(s) before going to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _detect_or_400(api_key: str) -> str:
    """Shared helper: detect a provider from a key, or raise a clear 400."""
    result = key_detector.detect_provider(api_key)
    if result.provider is None:
        raise HTTPException(
            status_code=400,
            detail="Couldn't identify this API key's provider. Supported: Claude (sk-ant-...), "
            "OpenAI (sk-...), Gemini (AIzaSy...), Groq (gsk_...).",
        )
    return result.provider


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/detect-key", response_model=DetectKeyResponse)
async def detect_key(request: DetectKeyRequest):
    result = key_detector.detect_provider(request.api_key)

    valid = None
    if request.verify and result.provider:
        valid = await key_detector.validate_key(result.provider, request.api_key)

    return DetectKeyResponse(provider=result.provider, confidence=result.confidence, valid=valid)


@app.get("/prompts/suggestions", response_model=SuggestionsResponse)
async def suggestions(category: str | None = Query(default=None)):
    return SuggestionsResponse(suggestions=prompt_library.get_suggestions(category))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    provider = _detect_or_400(request.api_key)
    adapter = get_adapter(provider)
    messages = [Message(role=m.role, content=m.content) for m in request.messages]

    try:
        result = await adapter.chat(messages, request.api_key, request.model)
    except Exception as e:
        logger.exception("Chat call failed")
        raise HTTPException(status_code=502, detail=f"{provider} request failed: {e}")

    return ChatResponse(
        provider_detected=provider,
        model_used=result.model_used,
        response=result.content,
        usage=result.usage,
    )


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    provider = _detect_or_400(request.api_key)
    adapter = get_adapter(provider)
    num_sources = request.num_sources or settings.MAX_SOURCES

    # 1. Search (our own Tavily key — this is the one cost we still absorb)
    try:
        raw_results = await search_service.search_web(request.query, num_sources)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=502, detail=f"Search provider error: {e}")

    if not raw_results:
        raise HTTPException(status_code=404, detail="No sources found for this query.")

    # 2. Fill in content, scraping only where the search API left a gap
    enriched_sources = []
    for result in raw_results:
        content = result.get("raw_content") or result.get("content") or ""
        if len(content) < 200:
            scraped = await scraper_service.scrape_url(result["url"])
            if scraped:
                content = scraped
        if not content:
            continue
        enriched_sources.append(
            {
                "title": result.get("title", result["url"]),
                "url": result["url"],
                "content": content[: settings.MAX_CONTENT_CHARS_PER_SOURCE],
            }
        )

    if not enriched_sources:
        raise HTTPException(
            status_code=404, detail="Found sources but couldn't extract usable content from any of them."
        )

    # 3. Ask the caller's own LLM to answer using only what was found
    system_instructions = request.system_prompt or DEFAULT_RESEARCH_SYSTEM_PROMPT
    context = "\n\n".join(
        f"[{i}] {s['title']} ({s['url']})\n{s['content']}" for i, s in enumerate(enriched_sources, start=1)
    )
    messages = [
        Message(role="system", content=system_instructions),
        Message(role="user", content=f"SOURCES:\n{context}\n\nQUESTION: {request.query}"),
    ]

    try:
        result = await adapter.chat(messages, request.api_key, request.model)
    except Exception as e:
        logger.exception("LLM generation failed")
        raise HTTPException(status_code=502, detail=f"{provider} request failed: {e}")

    # 4. Return answer + the sources it's grounded in
    return ResearchResponse(
        query=request.query,
        answer=result.content,
        sources=[
            SourceResult(title=s["title"], url=s["url"], snippet=s["content"][:300])
            for s in enriched_sources
        ],
        provider_detected=provider,
        model_used=result.model_used,
    )
