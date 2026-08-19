"""Model router with automatic failover between providers/models.

When one model hits its rate limit (429), quota, or connection error, the
router automatically moves to the next candidate so a single exhausted
quota never blocks the app. Supports Groq (always) and OpenRouter free
models (only when OPENROUTER_API_KEY is set).
"""
import os
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_clients: dict = {}


def _client(provider: str) -> Groq:
    if provider not in _clients:
        if provider == "groq":
            _clients["groq"] = Groq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            _clients["openrouter"] = Groq(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url=_OPENROUTER_BASE,
            )
    return _clients[provider]


def groq_models() -> list:
    """Ordered Groq candidates; the primary model is tried first."""
    configured = os.getenv("GROQ_MODELS")
    if configured:
        return [m.strip() for m in configured.split(",") if m.strip()]
    primary = os.getenv("GROQ_MODEL") or "groq/compound-mini"
    return [primary, "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "groq/compound"]


def openrouter_models() -> list:
    """OpenRouter free models; only used if a key is configured."""
    if not os.getenv("OPENROUTER_API_KEY"):
        return []
    configured = os.getenv("OPENROUTER_MODELS")
    if configured:
        return [m.strip() for m in configured.split(",") if m.strip()]
    return [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.5-flash:free",
        "deepseek/deepseek-chat:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ]


def candidate_models(model=None) -> list:
    """(provider, model) list in the order to try, deduplicated."""
    candidates: list = []
    seen = set()

    def add(provider: str, name: str):
        if name and name not in seen:
            seen.add(name)
            candidates.append((provider, name))

    if model:
        provider = "openrouter" if model.startswith("openrouter/") else "groq"
        add(provider, model)
    for name in groq_models():
        add("groq", name)
    for name in openrouter_models():
        add("openrouter", name)
    return candidates


def _is_failover_error(err: Exception) -> bool:
    """True for errors worth retrying on another model."""
    text = str(err).lower()
    return any(
        marker in text
        for marker in ("429", "rate limit", "rate_limit", "too many", "connection",
                       "timeout", "does not exist", "not found", "quota")
    )


def complete(messages: list, model=None, temperature: float = 0.0, max_tokens: int = 512):
    """Try each candidate model/provider until one succeeds.

    Returns the raw completion object (with ``.choices[0].message``) or
    raises the last error if every candidate fails.
    """
    candidates = candidate_models(model)
    if not candidates:
        raise RuntimeError("No LLM providers configured. Set GROQ_API_KEY (or OPENROUTER_API_KEY).")

    last_error = None
    for provider, name in candidates:
        try:
            return _client(provider).chat.completions.create(
                messages=messages,
                model=name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:  # noqa: BLE001 - intentional failover across models
            last_error = e
            if not _is_failover_error(e):
                raise
            print(f"[LLM ROUTER] {provider}/{name} failed ({e}). Trying next model...")
            time.sleep(0.5)
    raise RuntimeError(f"All {len(candidates)} models failed. Last error: {last_error}")