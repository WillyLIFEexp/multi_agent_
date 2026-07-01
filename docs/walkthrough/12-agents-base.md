# `app/agents/base.py`

Read after: [11-chain-presenter_agent](11-chain-presenter_agent.md) · Read before: [13-agents-openai_agent](13-agents-openai_agent.md) · [index](00-index.md)

**Single responsibility:** Define the `BaseAgent` contract for *orchestrators* — components that coordinate work and may hold state — as distinct from the stateless `BaseChain` steps. Imports nothing internal; implemented by `OpenAIAgent` (doc 13) and `RouterAgent` (doc 15).

Short file, but it marks the boundary that explains why the router lives in `agents/` and the specialists live in `chain/`.

---

## Block 1 — imports (lines 1–3)

```python
from abc import ABC, abstractmethod
from typing import Any
```

- **WHAT:** ABC machinery plus `Any` for the flexible `**kwargs`.
- **WHY:** same rationale as `BaseChain` (doc 08) — a runtime-enforced abstract contract that fails at construction if a subclass forgets `run`, rather than mid-request.

## Block 2 — `class BaseAgent(ABC)` and `name` (lines 6–9)

```python
class BaseAgent(ABC):
    name: str = "base"
```

- **WHAT:** the base class with a class-level `name` identifier (overridden to `"chat"` in `OpenAIAgent`, `"router"` in `RouterAgent`).
- **WHY a `name` attribute:** gives each agent a stable label for logging / responses without an instance method. Class-level with a default means every subclass has one even if it doesn't set it. (The direct endpoints in doc 16 pass explicit `agent="math"` labels, but the class `name` is the agent's own identity.)
- **WHY a separate base from `BaseChain`:** this is the crux. `BaseChain.invoke(inputs) -> outputs` models a *stateless step* in a pipeline. `BaseAgent.run(prompt) -> str` models an *actor* that takes a user prompt, produces an answer, and is allowed to own state (the router owns a `ChatHistoryStore`). Collapsing them into one base would blur "stateless transform" and "stateful orchestrator" — the very distinction that keeps memory in exactly one place. Two bases, two roles.

## Block 3 — `__init__(self, model=None)` (lines 11–12)

- **WHAT:** stores an optional `model` name on the instance.
- **WHY on the base:** every agent is parameterized by which model it runs, so it's the one genuinely shared construction state — unlike `BaseChain`, which stayed state-free because its subclasses shared no common construction. Agents *do* share "which model," so it belongs here.

## Block 4 — `run(self, prompt, **kwargs) -> str` (lines 14–17)

```python
@abstractmethod
async def run(self, prompt: str, **kwargs: Any) -> str: ...
```

- **WHAT:** the one required method: async, prompt string in, string answer out.
- **WHY `str -> str` (vs the chain's `dict -> dict`):** an agent is the *outer* interface — "ask a question, get an answer" — so a plain string in/out is the natural shape. The richer structured envelope (`route`, `details`, …) is exposed by the router's own `handle()`, not by `run`. `run` is the lowest-common-denominator agent call; `handle` is the router's fuller API. Keeping `run` minimal lets any agent (including `OpenAIAgent`) satisfy the contract.
- **WHY `**kwargs`:** different agents accept different extras; the varargs keep the base usable without enumerating every subclass's parameters. The tradeoff is looser typing at an outermost, human-facing entry point — acceptable.

---

## Why this shape (tie-back)

The specialists became **tools** and the presenter a **step** — both `BaseChain`
(stateless, doc 08). The router is different in kind: it holds conversation memory and
*orchestrates* those pieces (runs the `create_agent` loop, inspects its messages, calls
the presenter). `BaseAgent` is the contract for that orchestrator role. The clean
`chain/` vs `agents/` split — stateless steps vs stateful coordinator — is exactly why
memory lives only in the router and the specialists stay freely reusable.

Next: [13-agents-openai_agent](13-agents-openai_agent.md) — the simplest concrete `BaseAgent`, which shows the contract in isolation before the router complicates it. →
