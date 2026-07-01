# `app/schema/agent.py`

Read after: _(start here)_ · Read before: [02-utility-llm](02-utility-llm.md) · [index](00-index.md)

**Single responsibility:** Define the Pydantic data contracts — the specialist result shapes, the request bodies, and the HTTP response envelopes — that every other agent file speaks. Pure leaf: imports only `pydantic` and `typing`; imported by the chains, the presenter, the router, and the endpoints.

Start here because these types are the vocabulary of the whole system: a `MathResult` produced in doc 09 is the same object serialized in the router (doc 15) and returned by the endpoint (doc 16).

---

## Block 1 — imports and `Route` (lines 1–6)

```python
from typing import Literal
from pydantic import BaseModel, Field
Route = Literal["math", "history", "fallback"]
```

- **WHAT:** Pulls Pydantic and defines `Route`, the closed set of route labels.
- **WHY a `Literal` alias:** it constrains `AgentResponse.route` to exactly three values, so an impossible route is a validation error, and it documents the routing outcomes in one place. The alternative — a bare `str` — would let a typo like `"maths"` through silently.
- **WHY it stays even though routing is tool-based now:** the router still *reports* which specialist ran using these labels (mapped from tool names in doc 15). The label vocabulary outlived the old classifier; only the `RouteDecision` model that used to be the classifier's output was removed.

## Block 2 — `AgentQuery` (lines 9–20)

```python
class AgentQuery(BaseModel):
    query: str = Field(..., min_length=1, ...)
    tone: str = Field(default="friendly and clear", ...)
    session_id: str = Field(default="default", ...)
```

- **WHAT:** The `/agent/chat` request body.
- **WHY `min_length=1` on `query`:** rejects empty questions at the API boundary with a 422, before any LLM call is made — cheap, fail-fast validation.
- **WHY `tone` and `session_id` have defaults:** they're optional conveniences — a caller can just send `{"query": ...}`. `session_id` defaulting to `"default"` means stateless callers still get a working (shared) conversation bucket; `tone` defaulting keeps the presenter happy without the caller thinking about style.

## Block 3 — `MathResult` / `HistoryResult` (lines 23–37)

```python
class MathResult(BaseModel):
    answer: str = Field(...)
    steps: list[str] = Field(default_factory=list, ...)

class HistoryResult(BaseModel):
    answer: str = Field(...)
    key_facts: list[str] = Field(default_factory=list, ...)
```

- **WHAT:** The structured outputs of the two specialists.
- **WHY both share an `answer` field:** this is a deliberate cross-cutting convention. The router and the chains all read `result.answer` / `result["answer"]` without knowing which specialist produced it (docs 08–10). One shared field name is what makes the `{"result","answer"}` envelope type-agnostic.
- **WHY `default_factory=list` (not `default=[]`):** the classic mutable-default trap — `default=[]` would share one list across all instances. `default_factory=list` gives each instance a fresh list. Correct, deliberate.
- **WHY these are the structured-output targets:** the specialists bind these types via `with_structured_output(...)` (docs 09–10). Being real Pydantic models is what lets the value survive `model_dump()` → JSON → reconstruction across the router's tool boundary (doc 15).

## Block 4 — `PresentedResult` (lines 41–49)

```python
class PresentedResult(BaseModel):
    message: str = Field(...)
    tone: str = Field(...)
    needs_more_info: bool = Field(default=False, ...)
```

- **WHAT:** The presenter's structured output.
- **WHY `message` not `answer`:** the presenter emits reader-facing prose, and the field name reflects that. Note the router/endpoints map `message → answer` in the envelope (doc 11) so callers still read a uniform `answer`.
- **WHY `needs_more_info` exists:** it's a machine-readable flag distinguishing "here's the answer" from "I need you to clarify," so the caller can drive a follow-up loop without parsing prose (doc 11's fallback path).

## Block 5 — `AgentResponse` / `AgentAnswer` (lines 52–70)

```python
class AgentResponse(BaseModel):
    route: Route
    reasoning: str
    answer: str
    details: dict = Field(default_factory=dict, ...)

class AgentAnswer(BaseModel):
    agent: str
    answer: str
    details: dict = Field(default_factory=dict, ...)
```

- **WHAT:** The two HTTP response envelopes — `AgentResponse` for `/chat` (routed), `AgentAnswer` for the direct `/math`, `/history`, `/present` calls.
- **WHY `details: dict` (loose) rather than a typed union:** the chosen specialist's structured result is dumped into `details`, and that shape differs by route (`MathResult` vs `HistoryResult` vs `PresentedResult`). A `dict` avoids a discriminated-union that would have to enumerate every result type. ⚠ PROD: the tradeoff is `details` is unvalidated/undocumented in the OpenAPI schema — clients get no field-level typing for it. A `Union[MathResult, HistoryResult, PresentedResult]` with a discriminator would restore that at the cost of coupling the envelope to every result type.
- **WHY two separate envelopes:** `/chat` reports *routing* (`route`, `reasoning`) which the direct endpoints don't have; the direct endpoints report *which agent* (`agent`) was called explicitly. Different information, different models.

## Block 6 — `PresentRequest` (lines 80–84)

- **WHAT:** The `/agent/present` request body: `content` (required) + `tone` (defaulted).
- **WHY a distinct request model:** the presenter styles *content*, it doesn't answer a *query* — so it needs `content`, not `query`. The separate model encodes that different input contract (doc 11).

---

## Why this shape (tie-back)

These models are the reason the container-internal tool boundary is invisible. When the
router calls a specialist as a tool (doc 15), the tool does `json.dumps(result.model_dump())`
and the router later `json.loads`es it back into `details` — a round-trip that only works
because the results are stable, validated Pydantic models with a shared `answer` field.
Everything downstream (presenter input, API `details`, the uniform `answer`) is shaped by
the decisions in this one leaf file.

Next: [02-utility-llm](02-utility-llm.md) — the other universal dependency: the factory every agent uses to build its chat model. →
