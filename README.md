# AI Agent API

Ek combined API — do capabilities, ek hi shared engine:

- **`/research`** — web search + scrape + grounded answer (sources ke saath)
- **`/chat`** — multi-turn conversation, kisi bhi supported LLM provider ke saath

**Sabse important baat:** iska koi bhi LLM call hamari taraf se pay nahi hota. Har
request ke saath caller apni khud ki API key bhejta hai (Claude, OpenAI, Gemini, ya
Groq) — hum sirf usse detect karke sahi provider ko route kar dete hain. Sirf ek
cost hum khud bear karte hain: Tavily (web search), kyunki wo LLM operation nahi hai.

## Architecture

```
Client → api_key + prompt/messages
              │
              ▼
     Key detector (prefix match, e.g. sk-ant- = Claude)
              │
              ▼
     Provider adapter (Claude / OpenAI / Gemini / Groq)
              │
              ▼
     Caller's own key → actual provider API
              │
              ▼
     Normalized response (same shape, chahe koi bhi provider ho)
```

Ek hi "key detector + adapter" engine dono endpoints (`/research` aur `/chat`) use
karte hain — isliye naya provider add karna ho to bas ek adapter file likhni hai,
baaki system ko haath nahi lagana padega.

## Supported providers (auto-detected from key prefix)

| Provider | Key prefix |
|---|---|
| Claude (Anthropic) | `sk-ant-...` |
| OpenAI | `sk-...` / `sk-proj-...` |
| Gemini (Google) | `AIzaSy...` |
| Groq | `gsk_...` |

Prefix se match na ho to `/detect-key` ya `/chat`/`/research` clean 400 error dega,
saath mein supported list bhi bata dega — silently guess nahi karta.

## Endpoints

### `POST /chat` — multi-turn conversation

```json
// request
{
  "messages": [
    { "role": "user", "content": "What's a good beginner hiking trail?" }
  ],
  "api_key": "sk-ant-...",
  "model": "optional — omit to use provider's default"
}
// response
{
  "provider_detected": "anthropic",
  "model_used": "claude-sonnet-5",
  "response": "...",
  "usage": { "input_tokens": 42, "output_tokens": 180 }
}
```

Har naye turn par poori `messages` history dobara bhejni hai (stateless design —
hum khud conversation store nahi karte, backend engineer ka system karega). Nayi
`assistant` reply aane ke baad, use apni history mein append karke agli request
mein poora array bhejna hai.

### `POST /research` — web search + grounded answer

```json
// request
{
  "query": "best budget wireless earbuds 2026",
  "api_key": "sk-ant-...",
  "num_sources": 5,
  "model": "optional"
}
// response
{
  "query": "...",
  "answer": "...",
  "sources": [{ "title": "...", "url": "...", "snippet": "..." }],
  "provider_detected": "anthropic",
  "model_used": "claude-sonnet-5"
}
```

### `POST /detect-key` — provider pehchaano bina chat kiye

Frontend ko "Detected: Claude" jaisa badge dikhane ke liye, jawab bhejne se pehle.

```json
// request
{ "api_key": "sk-ant-...", "verify": false }
// response
{ "provider": "anthropic", "confidence": "high", "valid": null }
```

`verify: true` bhejoge to ek real (lightweight) call karke confirm karega ki key
actually valid bhi hai, sirf sahi format mein nahi — thoda slow hoga but definitive.

### `GET /prompts/suggestions?category=`

Curated example prompts (categories: `creative`, `coding`, `research`,
`productivity`) — blank chat box ke liye. User pick kare ya ignore karke apna type
kare, dono chalega.

## Setup

```bash
cd research-agent
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env mein bas TAVILY_API_KEY daalni hai — koi LLM key yahan nahi chahiye,
# wo har request ke saath caller apni khud ki bhejega

uvicorn app.main:app --reload --port 8000
```

`http://localhost:8000/docs` par Swagger UI khulega — wahan `/chat` ya `/research`
test karne ke liye apni khud ki (Claude/OpenAI/Gemini/Groq) key use karo.

## Render par deploy karna

Setup pehle jaisa hi hai, bas ab sirf ek env var chahiye:

1. GitHub par push karo
2. Render → **New → Blueprint** → repo select karo (`render.yaml` khud detect ho
   jaayega)
3. Sirf `TAVILY_API_KEY` daalna hoga — koi aur LLM key nahi maangega
4. Deploy karo, jo URL mile wahi backend engineer ko de do

## Security notes — yeh non-negotiable hai

Kyunki yeh API logon ki actual LLM keys handle karti hai:
- Raw key kabhi log mein nahi likhi jaati (poore codebase mein check kar liya hai)
- Key request ke duration tak hi memory mein rehti hai, kahin persist nahi hoti
- HTTPS ke bina production mein mat chalana
- `/chat` aur `/research` par per-IP rate limit lagane ki salah di jaati hai —
  galat keys baar-baar test karna providers ke abuse-detection ko trigger kar
  sakta hai

## Backend engineer ke liye — integration ka summary

```javascript
const response = await fetch("https://<your-render-url>/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: conversationHistory,   // apni taraf se maintain karo
    api_key: userProvidedKey,        // user ne jo bhi diya
  })
});
const data = await response.json();
conversationHistory.push({ role: "assistant", content: data.response });
```

Yehi pattern `/research` ke liye bhi chalega, bas `query` field use hoga
`messages` ki jagah.

## Files

```
app/
  main.py                          /research, /chat, /detect-key, /prompts/suggestions
  config.py                        Sirf TAVILY_API_KEY + tuning settings
  models.py                        Request/response schemas
  services/
    search_service.py              Tavily search
    scraper_service.py             Fallback page scraper
    llm/
      key_detector.py              Prefix match + optional probe validation
      prompt_library.py            Suggested prompts
      adapters/
        base.py                    Common ProviderAdapter interface
        anthropic_adapter.py
        openai_adapter.py
        gemini_adapter.py
        groq_adapter.py
        registry.py                Provider naam → adapter mapping
```
