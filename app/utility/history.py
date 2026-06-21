"""In-memory chat history store, keyed by session id.

Gives history-aware components (e.g. the router agent) access to prior turns of
a conversation. Process-local and not persisted; swap for Redis/DB to scale out.
"""
from collections import defaultdict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


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
