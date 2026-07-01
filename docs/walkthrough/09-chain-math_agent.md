# `app/chain/math_agent.py`

Read after: [08-chain-base](08-chain-base.md) · Read before: [10-chain-history_agent](10-chain-history_agent.md) · [index](00-index.md)

**Single responsibility:** The math specialist — a stateless, tool-using **LangGraph `StateGraph`** that turns a math query into a structured `MathResult`. Implements `BaseChain.invoke()` (doc 08); constructed by the router as the `solve_math` tool (doc 15) and by `/agent/math` (doc 16); calls `MATH_TOOLS` (doc 07) and the LLM factory (doc 02).

The first explicit graph, so it earns the most detail.

---

## Block 1 — imports (lines 20–30)

```python
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from app.chain.base import BaseChain
from app.schema.agent import MathResult
from app.tools import MATH_TOOLS
from app.utility.llm import get_llm
```

- **WHAT:** `StateGraph`/`START`/`END` build the workflow; `add_messages` is the message-channel reducer; `ToolNode` executes tool calls; plus the `BaseChain` supertype, the `MathResult` schema, the tools, and the LLM factory.
- **WHY THIS over the alternative:** the shortcut is `langgraph.prebuilt.create_react_agent`, which builds this exact loop for you. Hand-building the `StateGraph` is more code but makes the control flow (reason → act → respond) *visible and editable* — you can insert a validation node or swap the finalizer without fighting a prebuilt's opinions. That explicitness is the reason for using LangGraph here rather than a one-liner. `ToolNode` is still reused because re-implementing correct tool dispatch (matching `tool_call_id`s, formatting `ToolMessage`s, parallel calls) is error-prone — the right granularity is "hand-build the graph, reuse the node primitives."

## Block 2 — `SYSTEM_PROMPT` and `RESPOND_PROMPT` (lines 33–46)

- **WHAT:** `SYSTEM_PROMPT` tells the model to prefer tools over mental arithmetic and to *stop calling tools when done*; `RESPOND_PROMPT` is injected in the final node to force the `answer`/`steps` split.
- **WHY two prompts:** the loop and the finalizer are different jobs — "use tools then stop" vs "summarize into these two fields." One combined prompt would blur the stop condition and the formatting instruction.
- **WHY the explicit "stop calling tools" clause:** it's the loop's termination pressure — the conditional edge only exits when the model emits a message with *no* tool calls, so the prompt must actively encourage stopping.

## Block 3 — `MathState` (lines 49–53)

```python
class MathState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    result: MathResult | None
```

- **WHAT:** the graph's state — running conversation + final structured output.
- **WHY `Annotated[..., add_messages]`:** the annotation attaches a **reducer**. When a node returns `{"messages": [x]}`, LangGraph *appends* via `add_messages` (with id-based dedup) instead of overwriting. Without it, each node would clobber the history and the tool loop would lose context. This one annotation makes the loop accumulate reasoning + tool results correctly.
- **WHY a separate `result` channel:** the structured `MathResult` isn't a message; its own channel lets the finalizer write it once and `invoke` read it cleanly, instead of parsing it back out of the message list.

## Block 4 — `__init__` (lines 58–68)

```python
self._llm_tools = get_llm(...).bind_tools(MATH_TOOLS)
self._llm_struct = get_llm(...).with_structured_output(MathResult)
self._graph = self._build_graph()
```

- **WHAT:** builds two LLM handles — one bound to tools (drives the loop), one bound to the schema (produces the final `MathResult`) — then compiles the graph once.
- **WHY two LLM objects:** you can't cleanly get both tool-calling and guaranteed structured output from one bound call per node. The loop node needs tool-calling; the finalizer needs structured output. Two purpose-built handles keep each node doing one thing. Cost: two configs in memory — negligible.
- **WHY compile in `__init__` (eager):** the compiled graph is reusable and stateless across requests, so compiling once and reusing per `invoke` avoids rebuilding the graph every call. ⚠ PROD: `get_llm()` runs here, so `MathAgentChain()` fails immediately if the provider key is missing — fine in a single-container app that needs the key to serve anything.

## Block 5 — `_build_graph()` (lines 70–83)

```python
builder.add_node("reason", self._reason)
builder.add_node("act", ToolNode(MATH_TOOLS))
builder.add_node("respond", self._respond)
builder.add_edge(START, "reason")
builder.add_conditional_edges("reason", self._route, {"act": "act", "respond": "respond"})
builder.add_edge("act", "reason")
builder.add_edge("respond", END)
```

- **WHAT:** start at `reason`; branch to `act` or `respond`; `act` loops back to `reason`; `respond` ends.
- **WHY this topology:** the ReAct loop made explicit. `act → reason` (not `act → respond`) is the crucial edge: after tools run, control returns to the model to decide whether it needs *more* tools or is ready to answer. A `reason → act → respond` (no loop) would allow only one round of tool use and break multi-step problems.
- **WHY `add_conditional_edges` with a mapping:** the branch is data-dependent (did the model request tools?), which a static edge can't express; the `{"act":..., "respond":...}` dict maps the router function's return to the next node, keeping the branch declarative.

## Block 6 — `_reason` / `_route` / `_respond` (lines 85–104)

- **`_reason`** — calls the tool-bound LLM on the messages, returns `{"messages": [response]}`; the reducer appends it. The "think/decide" node.
- **`_route`** — pure function: `if getattr(last, "tool_calls", None): return "act" else "respond"`. **WHY `getattr` with default:** not every message type guarantees `tool_calls`; the defensive access avoids `AttributeError` and treats "no tool calls" as the exit condition — the loop's termination test.
- **`_respond`** — appends `RESPOND_PROMPT`, calls the *structured* LLM to emit a `MathResult`, returns `{"result": result}`. **WHY a separate structured call vs `create_react_agent(response_format=...)`:** in this hand-built graph the finalizer is its own node, so structuring is an explicit, modifiable step. The tradeoff vs the prebuilt's `response_format` is one extra LLM call — bought for an explicit, inspectable workflow.
  - **⚠ PROD:** that extra call is real latency/cost per query. If it matters, bind `with_structured_output` onto the loop model and capture the final structured turn instead of adding a node — at the cost of the explicitness.

## Block 7 — `invoke()` (lines 106–117)

```python
state = await self._graph.ainvoke({"messages": [SystemMessage(SYSTEM_PROMPT), HumanMessage(query)], "result": None})
return {"result": state["result"], "answer": state["result"].answer}
```

- **WHAT:** seeds the state, runs the graph, returns the canonical `{"result","answer"}` dict.
- **WHY seed `result: None`:** the `TypedDict` channel must exist before nodes read/write it; seeding makes the initial state well-formed.
- **Statelessness:** each call builds a fresh state — no memory carries between queries. Safe to share across sessions and callers.

---

## Why this shape (tie-back)

Because the router routes by **tool-calling**, this graph runs *inside* the `solve_math`
tool (doc 15): the tool calls `invoke()`, gets the `MathResult`, and `json.dumps`es it
back into the router agent's context. Two properties make that clean — the graph returns a
**validated Pydantic model** (serializes/recovers losslessly, doc 01) and it is
**stateless** (one shared instance serves every request with no cross-talk). The explicit
`StateGraph` is the "specialists = LangGraph" half of the architecture; the uniform
`invoke` return is what lets it plug into a tool without the router knowing its internals.

Next: [10-chain-history_agent](10-chain-history_agent.md) — the same pattern with the tool-loop removed, isolating what's essential vs incidental. →
