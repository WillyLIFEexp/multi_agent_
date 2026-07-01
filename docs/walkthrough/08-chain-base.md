# `app/chain/base.py`

Read after: [07-tools-init](07-tools-init.md) · Read before: [09-chain-math_agent](09-chain-math_agent.md) · [index](00-index.md)

**Single responsibility:** Define the one-method contract — `async invoke(inputs) -> outputs` — that every specialist implements. Pure leaf (stdlib only); imported by all three chains, the router (which wraps chains as tools), and the HTTP endpoints.

13 lines whose importance is inversely proportional to their size: it is the uniform seam that lets the router treat every specialist identically.

---

## Block 1 — imports (lines 1–3)

```python
from abc import ABC, abstractmethod
from typing import Any
```

- **WHAT:** Machinery for an abstract base class plus `Any` for the loosely-typed I/O dicts.
- **WHY it's needed:** `ABC` + `abstractmethod` make `BaseChain` non-instantiable and force subclasses to provide `invoke`. Without them this is a docstring with no teeth.
- **WHY THIS over the alternative:** the alternative is `typing.Protocol` (structural typing) or duck typing. `Protocol` would let each chain satisfy the interface without inheriting. The tradeoff: `ABC` gives a **runtime** guarantee — instantiating a subclass that forgot `invoke` fails at construction, not at first call mid-request — and makes intent explicit at each `class X(BaseChain)`. For a system where a missing method would surface as a 500 inside a request, failing loudly at construction beats `Protocol`'s decoupling. Deliberate.

## Block 2 — `class BaseChain(ABC)` (lines 6–7)

- **WHAT:** Declares the abstract base. No state, no `__init__`.
- **WHY it's needed:** it's the single named type the endpoints annotate against and the shape the router relies on when wrapping specialists as tools. That shared supertype is what lets math, history, and presenter be handled by one code path.
- **WHY no `__init__`:** each concrete chain constructs very differently (math compiles a multi-node graph; history a one-node graph; presenter binds a structured LLM). Forcing a common constructor would leak those differences upward. A state-free base means the only thing subclasses share is behavior, not data — the right coupling.

## Block 3 — `async def invoke(self, inputs) -> dict` (lines 9–12)

```python
@abstractmethod
async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the chain end-to-end and return its outputs."""
    raise NotImplementedError
```

- **WHAT:** the one required method. Async, dict in, dict out.
- **WHY async:** every implementation does network I/O to an LLM provider. A sync signature would force `asyncio.run`/thread-pool gymnastics inside the async FastAPI stack. Mandatory.
- **WHY `dict -> dict` instead of typed params:** the loose contract lets callers always pass `{"query": ...}` and always read `{"result": ..., "answer": ...}` regardless of which specialist answered — even though the three return *different* result types (docs 01, 09–11). A strongly-typed generic (`invoke(query: str) -> ChainOutput[T]`) would catch key typos at check time but thread generics through every layer.
  - **⚠ PROD:** the `{"query"}` / `{"result","answer"}` keys are an *implicit, unchecked* contract. `TypedDict`s for inputs/outputs would keep the flexibility while making it lint-checkable.
- **WHY `raise NotImplementedError` under `@abstractmethod`:** belt-and-suspenders — protects a subclass that calls `super().invoke(...)`. Conventional.

---

## Why this shape (tie-back)

Two things lean directly on this contract: (1) **the router wraps specialists as tools** —
`solve_math`/`answer_history` are thin closures calling `chain.invoke({"query": ...})` and
reading `["result"]` (doc 15); because both chains honor the identical contract, the two
tool wrappers are byte-for-byte parallel. (2) **the direct endpoints are uniform** —
`/agent/math` and `/agent/history` both do `await agent.invoke({"query": ...})` (doc 16).
The result types differ; the envelope is constant. That constancy is the whole job of
these 13 lines.

Next: [09-chain-math_agent](09-chain-math_agent.md) — the first concrete implementation: an explicit LangGraph workflow fulfilling this contract. →
