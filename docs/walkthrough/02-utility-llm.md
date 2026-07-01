# `app/utility/llm.py`

Read after: [01-schema-agent](01-schema-agent.md) · Read before: [03-utility-history](03-utility-history.md) · [index](00-index.md)

**Single responsibility:** A provider factory — `get_llm(provider, model, temperature)` returns a LangChain `BaseChatModel` for OpenAI, Azure, or Ollama. It depends only on settings; it is called by every chain, the presenter, both agents, and the router. It is the one place the app decides *which* LLM it talks to.

---

## Block 1 — imports and `LLMProvider` (lines 12–24)

```python
from enum import Enum
from langchain_core.language_models import BaseChatModel
from app.core.settings.config import get_settings

class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    OLLAMA = "ollama"
```

- **WHAT:** Defines the supported backends as a `str`-mixin enum and imports the abstract `BaseChatModel` return type.
- **WHY a `str` Enum:** `class LLMProvider(str, Enum)` members compare equal to their string values, so `LLMProvider("openai")` works and the enum is JSON/`.env`-friendly. It gives you a closed set (typo-proof) while still accepting plain strings from config.
- **WHY return the abstract `BaseChatModel`:** the whole point of the factory is that callers stay provider-agnostic. Annotating the return as the base type (not `ChatOpenAI`) means no caller can accidentally depend on an OpenAI-specific method — swapping providers can't break them.

## Block 2 — `get_llm(...)` signature and defaulting (lines 27–47)

```python
def get_llm(provider=None, model=None, temperature=None, **kwargs) -> BaseChatModel:
    settings = get_settings()
    provider = LLMProvider((provider or settings.llm_provider).lower())
    temperature = settings.temperature if temperature is None else temperature
```

- **WHAT:** Resolves each argument against settings when not explicitly passed; normalizes the provider string and coerces it into the enum.
- **WHY `temperature is None` rather than `temperature or settings.temperature`:** `0.0` is a valid, meaningful temperature but falsy. `or` would silently replace an explicit `0.0` with the settings default. The explicit `is None` check preserves a caller's `temperature=0` — which matters because the router (doc 15) *depends* on `temperature=0` for deterministic routing.
- **WHY `.lower()` on the provider:** tolerates `"OpenAI"` / `"OPENAI"` from env or callers; the enum values are lowercase. Small robustness win.
- **WHY `**kwargs` passthrough:** lets callers forward provider-specific options (e.g. `bind_tools` is done outside, but things like `max_tokens`) without the factory enumerating every model's parameters. The tradeoff is looser typing — acceptable for a thin factory.

## Block 3 — the three provider branches (lines 49–81)

```python
if provider is LLMProvider.OPENAI:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model or settings.default_model, temperature=..., api_key=..., **kwargs)
if provider is LLMProvider.AZURE:
    from langchain_openai import AzureChatOpenAI
    if not settings.azure_openai_endpoint: raise ValueError(...)
    return AzureChatOpenAI(...)
if provider is LLMProvider.OLLAMA:
    from langchain_ollama import ChatOllama
    return ChatOllama(model=..., base_url=..., ...)
```

- **WHAT:** Constructs the right chat model per provider, each with a provider-appropriate default model/deployment.
- **WHY the imports are *inside* the branches (lazy):** `langchain_openai` and `langchain_ollama` are heavyweight and optional. Importing lazily means an OpenAI-only deployment never pays to import the Ollama stack (and vice versa), and a missing optional dependency only errors if you actually select that provider. Module-top imports would force all provider SDKs to be installed and imported even when unused.
- **WHY the explicit Azure endpoint check:** Azure fails in confusing ways deep inside the SDK if the endpoint is missing. The upfront `raise ValueError("AZURE_OPENAI_ENDPOINT is required...")` turns that into a clear, early message. Note only Azure gets this guard — OpenAI relies on the SDK's own key error, and Ollama has a working localhost default.
- **WHY per-provider default model (`model or settings.default_model` vs `settings.ollama_model`):** each backend names models differently (`gpt-4o-mini` vs `llama3.1` vs an Azure *deployment* name), so each branch falls back to the setting appropriate for it.

## Block 4 — the final `raise` (line 83)

```python
raise ValueError(f"Unsupported LLM provider: {provider}")
```

- **WHAT:** Unreachable in practice (the enum coercion above would already have raised on a bad value), but it satisfies the type checker that all paths return-or-raise and guards against a future enum member added without a branch.
- **WHY keep it:** defensive completeness; if someone adds `GEMINI` to the enum but forgets a branch, this gives a clear failure instead of an implicit `None` return.

---

## Why this shape (tie-back)

Every agent in this codebase is provider-portable *because* of this factory. The math
agent binds tools onto `get_llm(...)`, the history/presenter chains bind structured output
onto it, and the router passes `temperature=0` through it (docs 09–11, 15). None of them
name a provider — so switching the whole app from OpenAI to a local Ollama is a single
`.env` change, not a code change. The lazy per-branch imports and the `is None`
temperature handling are the two non-obvious details that make that portability actually
hold.

Next: [03-utility-history](03-utility-history.md) — the last primitive: the per-session memory store the router owns. →
