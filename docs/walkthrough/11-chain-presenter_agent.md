# `app/chain/presenter_agent.py`

Read after: [10-chain-history_agent](10-chain-history_agent.md) · Read before: [12-agents-base](12-agents-base.md) · [index](00-index.md)

**Single responsibility:** The presenter — a stateless chain that rewrites a specialist's structured result into a polished, tone-adjusted message (`invoke`), and *also* handles the case where no specialist fit (`respond`). Implements `BaseChain.invoke()` (doc 08) but adds a second method. Constructed by `RouterAgent.__init__` (doc 15) and `/agent/present` (doc 16). Unlike math/history, it is **never** wrapped as a routable tool.

The chain that stays a plain in-process step while math and history become tools — understanding *why* is the point.

---

## Block 1 — imports (lines 7–13)

```python
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from app.chain.base import BaseChain
from app.schema.agent import PresentedResult
from app.utility.llm import get_llm
```

- **WHAT:** the toolless-LLM import set plus `BaseMessage` — the type of the conversation-history list `respond()` accepts.
- **WHY `BaseMessage` here and not in the specialists:** the fallback path threads prior turns into the prompt, so it types a `list[BaseMessage]`. The specialists never see history (stateless, single-shot); the presenter's fallback does, because answering "now do the other one" coherently needs context.

## Block 2 — `SYSTEM_PROMPT` (lines 15–21)

- **WHAT:** rewrite provided content into a final answer in the requested tone, *preserving all facts/numbers/steps faithfully*, setting `message`, `tone`, `needs_more_info=false`.
- **WHY "preserve, do not invent" is load-bearing:** the presenter runs *downstream* of a specialist that already computed the truth (a `MathResult` with exact steps). If it paraphrases `x^2` into "x squared, roughly" it corrupts a correct answer. The clause constrains it to a *styling* transform, not a reasoning one — without it you've added a second LLM that can silently break a right answer.

## Block 3 — `FALLBACK_SYSTEM_PROMPT` (lines 23–30)

- **WHAT:** a different prompt for queries matching no specialist: if unclear, ask one concise clarifying question and set `needs_more_info=true`; otherwise answer directly and set it `false`.
- **WHY a separate prompt:** styling ("restyle known content") and fallback ("you are the answerer of last resort; decide if you even can") are genuinely different tasks. Folding both into one would muddy the model's job and the `needs_more_info` signal.
- **WHY `needs_more_info` exists:** a machine-readable flag distinguishing "here's your answer" from "I need more from you" without parsing prose.

## Block 4 — `__init__` (lines 36–39)

```python
self._llm = get_llm(...).with_structured_output(PresentedResult)
```

- **WHAT:** one structured-output LLM bound to `PresentedResult`.
- **WHY structured output here too:** the presenter must return `tone` and `needs_more_info` as reliable fields, not buried in prose. Validated Pydantic over regex.

## Block 5 — `invoke()` (lines 41–51)

```python
content = inputs["content"]
tone = inputs.get("tone", "friendly and clear")
...
return {"result": result, "answer": result.message}
```

- **WHAT:** the `BaseChain` styling path. Takes `content` (a specialist's `model_dump()`, or the router's recovered `details`) and a `tone`; returns `{"result","answer"}` where `answer` is `result.message`.
- **WHY `inputs["content"]` required but `inputs.get("tone", ...)` defaulted:** content is mandatory — nothing to present without it, so a hard `KeyError` is correct. Tone is a preference with a sensible default. The asymmetry encodes which input is essential.
- **WHY `answer` maps to `result.message`:** `PresentedResult` has no `answer` field — its user-facing text lives in `message`. Mapping `message → answer` keeps the doc-08 envelope uniform so callers read `["answer"]` regardless of the underlying field.

## Block 6 — `respond()` (lines 53–70)

```python
async def respond(self, query, tone="friendly and clear", history=None):
    messages = [SystemMessage(FALLBACK_SYSTEM_PROMPT), *(history or []), HumanMessage(...)]
    return {"result": result, "answer": result.message}
```

- **WHAT:** the fallback entry point: takes a raw `query` (not pre-computed content) plus optional `history`, runs the *fallback* prompt, returns the same envelope.
- **WHY a second method instead of overloading `invoke`:** `invoke` is the polymorphic `BaseChain` contract callers treat uniformly. `respond` is presenter-*specific* (different inputs). Cramming both into `invoke` would need a mode flag and break the "all chains look alike" contract the router relies on. Keeping `respond` separate means the presenter satisfies `BaseChain` for styling *and* offers a richer API for the fallback path.
- **WHY `respond` takes `history` but `invoke` doesn't:** styling a known result needs no context; answering a novel question coherently after prior turns does. The `*(history or [])` splat injects prior messages between the system prompt and the new query.
- **Statelessness still holds:** the presenter stores no history — it's *passed in* by the router (which owns the store, doc 03/15). Memory lives in exactly one place.

---

## Why this shape (tie-back)

The presenter is the deliberate exception to "make specialists tools." It runs on
**every** turn — the specialist path calls `invoke` to restyle, the no-tool path calls
`respond` to answer — so exposing it as a routable tool would be pointless: the router
would *always* call it, which is just a post-step by another name. So it has no tool
wrapper and no entry in the router's tool list; the router calls it directly after the
`create_agent` loop finishes (doc 15). This is the architecture drawing the line between
"a specialist the router *chooses*" (math, history → tools) and "a helper the router
*always* uses" (presenter → in-process step).

Next: [12-agents-base](12-agents-base.md) — leaving `chain/` for `agents/`: the `BaseAgent` contract and the orchestrator/chain split. →
