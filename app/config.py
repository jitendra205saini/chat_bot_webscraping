import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    All environment-driven configuration lives here so the rest of the
    codebase never touches os.environ directly. Change values in .env,
    not in code.
    """

    # Tavily is the one cost we still absorb ourselves — search isn't an
    # "LLM operation", so it stays on our own key. Every LLM call (in both
    # /research and /chat) uses the caller's own api_key instead — no
    # provider key lives on the server anymore.
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    MAX_SOURCES: int = int(os.getenv("MAX_SOURCES", "5"))
    MAX_CONTENT_CHARS_PER_SOURCE: int = int(
        os.getenv("MAX_CONTENT_CHARS_PER_SOURCE", "2000")
    )
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
