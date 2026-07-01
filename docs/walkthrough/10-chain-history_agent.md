# `app/chain/history_agent.py`

Read after: [09-chain-math_agent](09-chain-math_agent.md) · Read before: [11-chain-presenter_agent](11-chain-presenter_agent.md) · [index](00-index.md)

**Single responsibility:** The history specialist — a stateless, *toolless* LangGraph workflow that turns a history query into a structured `HistoryResult`. Implements `BaseChain.invoke()` (doc 08); wrapped as the `answer_history` tool by the router (doc 15) and called by `/agent/history` (doc 16).

Read right after math because it's the same `StateGraph` machinery with the tool-loop stripped away — it isolates what's *essential* (a compiled graph producing a validated result) from what's *incidental* (the reason/act loop).

---

## Block 1 — imports (lines 14–19)

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from app.chain.base import BaseChain
from app.schema.agent import HistoryResult
from app.utility.llm import get_llm
```

- **WHAT:** `StateGraph`/`START`/`END`, the `BaseChain` supertype, the `HistoryResult` schema, the LLM factory.
- **WHY THIS vs math's imports:** note what's *absent* — no `ToolNode`, no `add_messages`, no `MATH_TOOLS`, no `bind_tools`. History answers from the model's own knowledge, so there's no tool loop and no message-accumulation channel. The smaller surface is a direct signal of the simpler workflow.

## Block 2 — `SYSTEM_PROMPT` (lines 22–27)

- **WHAT:** instructs the model to answer with dates/context, split output into `answer` (prose) and `key_facts`, and flag uncertainty.
- **WHY it's needed:** double duty — sets the persona *and* names the two `HistoryResult` fields so the structured step populates both. Without the "populate 'answer' with… and 'key_facts' with…" sentence the model dumps everything into `answer`.
- **⚠ PROD:** the "say so if uncertain" clause is mitigation, not a fix — a pure-LLM history agent has no retrieval grounding, so its correctness ceiling is whatever the base model knows. Real deployments would add a retrieval node (see below).

## Block 3 — `HistoryState` (lines 30–34)

```python
class HistoryState(TypedDict):
    query: str
    result: HistoryResult | None
```

- **WHAT:** the graph's state: input `query`, output `result`.
- **WHY no `messages` channel / no reducer:** there's no conversation to accumulate — it's a single LLM call. A plain `query in / result out` state is all it needs. Contrast doc 09, where the `add_messages` reducer existed *only* to feed the tool loop. Removing tools removes the reason for the message channel.

## Block 4 — `__init__` and `_build_graph()` (lines 39–55)

```python
self._llm = get_llm(...).with_structured_output(HistoryResult)
self._graph = self._build_graph()
...
builder.add_node("answer", self._answer)
builder.add_edge(START, "answer")
builder.add_edge("answer", END)
```

- **WHAT:** binds one structured-output LLM and compiles a single-node graph `START → answer → END`.
- **WHY a graph at all for one node:** honestly, a bare LLM call would work. The graph is here so history *mirrors* math's shape and stays trivially extensible — you could insert a `retrieve` node before `answer` (the fix for the grounding weakness) without touching `invoke` or any caller. That's the deliberate intent: a consistent, extensible skeleton, not accidental over-engineering. Be honest that today it's a thin wrapper; its value is future edit-ability and uniformity with the math agent.
- **WHY one LLM (vs math's two):** with no tool loop there's no need for a tool-bound model — the single structured LLM does the whole job in one node.

## Block 5 — `_answer()` and `invoke()` (lines 57–70)

```python
async def _answer(self, state):
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(state["query"])]
    return {"result": await self._llm.ainvoke(messages)}

async def invoke(self, inputs):
    state = await self._graph.ainvoke({"query": inputs["query"], "result": None})
    return {"result": state["result"], "answer": state["result"].answer}
```

- **WHAT:** the `answer` node builds a two-message prompt and returns the structured `HistoryResult`; `invoke` runs the graph and returns the canonical `{"result","answer"}`.
- **WHY `result.answer` maps to `"answer"`:** `HistoryResult` shares the field name `answer` with `MathResult`, so the router's `_inspect` and text surfaces read `["answer"]` without knowing which specialist produced it (doc 01's uniform envelope).
- **Statelessness:** each call seeds a fresh state — no memory. Safe to share behind the cached tool.

---

## Why this shape (tie-back)

The history agent is the cleanest proof that "specialists = LangGraph" is cheap: strip the
tools and you have a one-node graph returning a validated Pydantic model. Wrapped as the
`answer_history` tool (doc 15), its result `model_dump()`s to JSON, rides back through the
router agent's context, and is recovered by `_inspect` — exactly like math, because both
honor the same `invoke` contract and both return an `answer` field. Tools-or-no-tools is a
private detail invisible to the router.

Next: [11-chain-presenter_agent](11-chain-presenter_agent.md) — the third chain, which stays a plain in-process step (never a routable tool) and adds a second `respond()` entry point. →
