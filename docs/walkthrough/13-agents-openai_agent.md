# `app/agents/openai_agent.py`

Read after: [12-agents-base](12-agents-base.md) · Read before: [14-chain-graph](14-chain-graph.md) · [index](00-index.md)

**Single responsibility:** A concrete single-shot chat agent — one system prompt + one user turn → one answer — implementing `BaseAgent` (doc 12) over any provider from `get_llm` (doc 02). It is **not** part of the `/agent/chat` flow; it's the minimal `BaseAgent` implementation and the thing `SimpleGraphChain` (doc 14) wraps. Included for completeness.

Read it as "what the `BaseAgent` contract looks like with nothing else going on" — a baseline before the router (doc 15) adds tools, routing, memory, and a presenter.

---

## Block 1 — imports (lines 1–8)

```python
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.base import BaseAgent
from app.core.settings.config import get_settings
from app.utility.llm import get_llm
```

- **WHAT:** the `BaseAgent` supertype, settings, the LLM factory, and the two message types.
- **WHY only these:** no tools, no graph, no schema. A single-shot agent needs just a model and a way to phrase one exchange — the sparse imports advertise how little this agent does.

## Block 2 — `class OpenAIAgent(BaseAgent)` and `__init__` (lines 11–25)

```python
class OpenAIAgent(BaseAgent):
    name = "chat"
    def __init__(self, model=None, system_prompt="You are a helpful assistant.", provider=None):
        settings = get_settings()
        super().__init__(model=model or settings.default_model)
        self.system_prompt = system_prompt
        self._llm = get_llm(provider=provider, model=model)
```

- **WHAT:** sets the agent's `name`, resolves the model via settings, stores a configurable system prompt, and builds a plain (unbound) chat model.
- **WHY the name `OpenAIAgent` despite being provider-agnostic:** slightly misleading — it goes through `get_llm`, so it works with Azure or Ollama too. The name reflects the default/original provider, not a hard dependency. ⚠ (naming nit, not a bug) `ChatAgent` would describe it better.
- **WHY `system_prompt` is a constructor arg (not a module constant):** unlike the specialists (whose prompts are fixed to their job), this is a *general* agent — the caller decides its persona at construction. Making it a parameter is what makes the class reusable for different single-shot tasks.
- **WHY a bare `get_llm(...)` with no `bind_tools`/`with_structured_output`:** this agent neither calls tools nor returns structured data — it just chats. The unadorned model is the whole point; contrast the specialists (docs 09–11) that decorate the model for their needs.

## Block 3 — `run()` (lines 27–33)

```python
async def run(self, prompt: str, **kwargs: Any) -> str:
    messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=prompt)]
    response = await self._llm.ainvoke(messages, **kwargs)
    return response.content
```

- **WHAT:** builds a two-message exchange, invokes the model, returns the text.
- **WHY it returns `response.content` (a string):** this is the `BaseAgent.run` contract (doc 12) — string in, string out. No envelope, no structure, because a single-shot chat has nothing structured to report.
- **WHY forward `**kwargs` to `ainvoke`:** lets a caller pass per-call options (e.g. `temperature` override, `max_tokens`) through to the model without the agent enumerating them — the same passthrough philosophy as `get_llm`.
- **Statelessness:** no history, no memory — every `run` is independent. That's the definitional difference from the router, which *is* a `BaseAgent` but chooses to own a `ChatHistoryStore`. `BaseAgent` *permits* state; it doesn't require it, and this agent declines it.

---

## Why this shape (tie-back)

`OpenAIAgent` is the control case that makes the router's complexity legible: both are
`BaseAgent`s with a `run(prompt) -> str`, but this one is a single model call with no
tools, no routing, and no memory, while the router (doc 15) is the same contract wrapped
around a `create_agent` loop, specialist tools, message inspection, a presenter, and a
history store. Seeing the contract satisfied trivially here clarifies that everything
extra in the router is a *choice*, not an obligation of being an agent. It also has an
independent role: it's the unit `SimpleGraphChain` (doc 14) runs inside a LangGraph node.

Next: [14-chain-graph](14-chain-graph.md) — a minimal LangGraph that wraps this agent behind the `BaseChain` interface, bridging the agent and chain worlds. →
