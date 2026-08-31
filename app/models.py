from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# --- /research -------------------------------------------------------

class ResearchRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    query: str = Field(..., min_length=1, description="Topic or question to research")
    api_key: str = Field(..., min_length=1, description="Your own LLM provider API key (Claude, OpenAI, Gemini, or Groq)")
    num_sources: Optional[int] = Field(
        default=None, ge=1, le=10, description="How many sources to pull in (default: server setting)"
    )
    model: Optional[str] = Field(
        default=None, description="Specific model to use. Omit to use the provider's default."
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Override the grounding instruction given to the model. Omit to use the default "
        "'answer only from these sources' instruction.",
    )


class SourceResult(BaseModel):
    title: str
    url: str
    snippet: str


class ResearchResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    query: str
    answer: str
    sources: List[SourceResult]
    provider_detected: str
    model_used: str


# --- /chat -------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    messages: List[ChatMessage] = Field(..., min_length=1, description="Full conversation so far, oldest first")
    api_key: str = Field(..., min_length=1, description="Your own LLM provider API key")
    model: Optional[str] = Field(default=None, description="Specific model to use. Omit to use the provider's default.")


class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    provider_detected: str
    model_used: str
    response: str
    usage: dict


# --- /detect-key ---------------------------------------------------------

class DetectKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    verify: bool = Field(default=False, description="If true, makes one real call to confirm the key works, not just its shape")


class DetectKeyResponse(BaseModel):
    provider: Optional[str]
    confidence: str  # "high" | "none"
    valid: Optional[bool] = None  # only set when verify=true was requested


# --- /prompts/suggestions --------------------------------------------------

class PromptSuggestion(BaseModel):
    id: str
    category: str
    text: str


class SuggestionsResponse(BaseModel):
    suggestions: List[PromptSuggestion]
