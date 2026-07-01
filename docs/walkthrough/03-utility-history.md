# `app/utility/history.py`

Read after: [02-utility-llm](02-utility-llm.md) · Read before: [04-tools-calculator](04-tools-calculator.md) · [index](00-index.md)

**Single responsibility:** An in-memory, per-session conversation store — `ChatHistoryStore` keeps a trimmed list of LangChain messages keyed by `session_id`. It depends only on `langchain_core.messages`; it is owned by the router (doc 15), which is the *only* stateful component in the system.

---

## Block 1 — imports (lines 6–8)

```python
from collections import defaultdict
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
```

- **WHAT:** `defaultdict` for auto-creating per-session lists; the LangChain message types stored.
- **WHY store `BaseMessage` objects (not plain strings):** the history is fed straight back into the router's agent as `[*history, HumanMessage(query)]` (doc 15). Storing already-typed `HumanMessage`/`AIMessage` means no re-wrapping on read, and it preserves the role distinction the LLM needs to interpret the conversation.

## Block 2 — `__init__` and the store (lines 14–16)

```python
def __init__(self, max_messages: int = 20) -> None:
    self.max_messages = max_messages
    self._store: dict[str, list[BaseMessage]] = defaultdict(list)
```

- **WHAT:** A dict from `session_id` to a message list, with a per-session cap.
- **WHY `defaultdict(list)`:** `get`/`_append` can touch any session id without first checking existence — a new session transparently starts with an empty list. The alternative (`dict` + `setdefault`/existence checks) is more boilerplate for the same effect.
- **WHY a `max_messages` cap:** unbounded history would grow the prompt every turn — rising cost, latency, and eventually context-window overflow. The cap bounds the prompt size. ⚠ PROD: trimming by raw message count is crude — it can cut mid-exchange (drop a user turn but keep its answer) and ignores token length. A token-aware or summarizing window is the sturdier approach.

## Block 3 — `get()` (lines 18–20)

```python
def get(self, session_id: str) -> list[BaseMessage]:
    return list(self._store[session_id])
```

- **WHAT:** Returns a **copy** of the session's messages.
- **WHY `list(...)` (a copy) not the internal list:** handing out the live list would let a caller mutate the store's internals (and would alias the list the router then appends to mid-request). Returning a shallow copy makes reads safe against accidental mutation. Deliberate defensiveness.

## Block 4 — `add_user` / `add_ai` / `clear` (lines 22–30)

```python
def add_user(self, session_id, content): self._append(session_id, HumanMessage(content=content))
def add_ai(self, session_id, content):   self._append(session_id, AIMessage(content=content))
def clear(self, session_id):             self._store.pop(session_id, None)
```

- **WHAT:** Typed append helpers and a session eraser.
- **WHY separate `add_user`/`add_ai` rather than one `add(message)`:** the call sites (router `handle`, doc 15) think in terms of "record the user's query" and "record the AI's answer," not in terms of message classes. These helpers keep the role-tagging correct and centralized — a caller can't accidentally store a user turn as an AI turn.
- **WHY `pop(session_id, None)`:** idempotent clear — deleting a non-existent session is a no-op, not a `KeyError`, so the `DELETE /sessions/{id}` endpoint (doc 16) is safe to call blindly.

## Block 5 — `_append()` and trimming (lines 32–36)

```python
def _append(self, session_id, message):
    history = self._store[session_id]
    history.append(message)
    if len(history) > self.max_messages:
        del history[: len(history) - self.max_messages]
```

- **WHAT:** Appends, then trims the oldest overflow so the list never exceeds `max_messages`.
- **WHY `del history[:n]` (in-place slice delete) rather than reassigning:** it mutates the same list object the store holds, so the trimming is visible everywhere without touching the dict. Slicing off the front keeps the *most recent* messages — the right ones to keep for continuity.

---

## Why this shape (tie-back)

This store is where the "orchestrator vs chain" split (doc 12) becomes concrete: the
specialists are stateless (they hold no memory), and *all* conversation state lives here,
owned by the router. That is what lets the specialists be shared singletons behind cached
providers (doc 16) with no cross-session leakage, while the router still routes follow-ups
with context by prepending `get(session_id)` to each agent call (doc 15). It's in-memory
and process-local by design — fine for one container, and the obvious first thing to swap
(for Redis/DB) when scaling beyond one.

Next: [04-tools-calculator](04-tools-calculator.md) — the first of the math tools the math agent can call. →
