"""
Scraping layer.

Tavily often returns enough page text on its own (via raw_content), so this
module is only used as a *fallback* — when a result comes back with little
or no content, we fetch the page ourselves and extract the visible text.

Two safety rules baked in, matching what the platform doc calls out:
  1. Respect robots.txt — skip pages that don't allow scraping.
  2. Never let a bad site take the whole request down — every failure
     here returns "" instead of raising, so the pipeline just skips
     that one source.
"""

import asyncio
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.config import settings

USER_AGENT = "Mozilla/5.0 (compatible; ResearchAgentBot/1.0)"
HEADERS = {"User-Agent": USER_AGENT}
UNWANTED_TAGS = ["script", "style", "nav", "footer", "header", "form", "aside", "noscript"]


def _check_robots(url: str) -> bool:
    """Best-effort robots.txt check. Defaults to allow if it can't be read."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


async def scrape_url(url: str) -> str:
    """Fetches a page and returns its cleaned visible text, or "" on any failure."""
    allowed = await asyncio.to_thread(_check_robots, url)
    if not allowed:
        return ""

    try:
        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            headers=HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(UNWANTED_TAGS):
        tag.decompose()

    return soup.get_text(separator=" ", strip=True)
