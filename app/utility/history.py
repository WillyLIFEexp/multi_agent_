"""Chat history stores, keyed by session id.

Two implementations share one duck-typed interface (``get`` / ``add_user`` /
``add_ai`` / ``clear``):

- ``ChatHistoryStore`` — in-memory, sync; the local/no-Mongo fallback.
- ``MongoChatHistoryStore`` — MongoDB-backed, async; the durable default.

Because one is sync and the other async, callers await results through
``maybe_await`` so they don't need to know which store is wired in.
"""
import inspect
from collections import defaultdict
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


async def maybe_await(value: Any) -> Any:
    """Await ``value`` if it is awaitable, else return it as-is.

    Lets a caller use either the sync ``ChatHistoryStore`` or the async
    ``MongoChatHistoryStore`` without branching on which is present.
    """
    if inspect.isawaitable(value):
        return await value
    return value


class ChatHistoryStore:
    """Stores LangChain messages per session, trimmed to a max length."""

    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages
        self._store: dict[str, list[BaseMessage]] = defaultdict(list)

    def get(self, session_id: str) -> list[BaseMessage]:
        """Return the message history for a session (oldest first)."""
        return list(self._store[session_id])

    def add_user(self, session_id: str, content: str) -> None:
        self._append(session_id, HumanMessage(content=content))

    def add_ai(self, session_id: str, content: str) -> None:
        self._append(session_id, AIMessage(content=content))

    def clear(self, session_id: str) -> None:
        """Forget a session's history."""
        self._store.pop(session_id, None)

    def _append(self, session_id: str, message: BaseMessage) -> None:
        history = self._store[session_id]
        history.append(message)
        if len(history) > self.max_messages:
            del history[: len(history) - self.max_messages]


# Role tags persisted per message; kept minimal since only user/AI turns are stored.
_ROLE_USER = "user"
_ROLE_AI = "ai"


class MongoChatHistoryStore:
    """MongoDB-backed history: one document per session, trimmed to max_messages.

    Stores just the clean transcript (user query + final AI answer) as
    ``{"_id": session_id, "messages": [{"role", "content"}, ...]}``. The
    ``$slice`` on ``$push`` keeps only the most recent ``max_messages`` turns.
    """

    def __init__(self, collection, max_messages: int = 20) -> None:
        self._col = collection
        self.max_messages = max_messages

    async def get(self, session_id: str) -> list[BaseMessage]:
        """Return the message history for a session (oldest first)."""
        doc = await self._col.find_one({"_id": session_id})
        if not doc:
            return []
        return [self._deserialize(m) for m in doc.get("messages", [])]

    async def add_user(self, session_id: str, content: str) -> None:
        await self._append(session_id, _ROLE_USER, content)

    async def add_ai(self, session_id: str, content: str) -> None:
        await self._append(session_id, _ROLE_AI, content)

    async def clear(self, session_id: str) -> None:
        """Forget a session's history."""
        await self._col.delete_one({"_id": session_id})

    async def _append(self, session_id: str, role: str, content: str) -> None:
        await self._col.update_one(
            {"_id": session_id},
            {
                "$push": {
                    "messages": {
                        "$each": [{"role": role, "content": content}],
                        "$slice": -self.max_messages,
                    }
                }
            },
            upsert=True,
        )

    @staticmethod
    def _deserialize(message: dict) -> BaseMessage:
        if message.get("role") == _ROLE_AI:
            return AIMessage(content=message.get("content", ""))
        return HumanMessage(content=message.get("content", ""))
