"""Router agent: a LangChain ``create_agent`` that routes via tool-calling.

The router is an agent built with ``langchain.agents.create_agent``. The math and
history specialists are exposed to it as **tools**; the agent's own reasoning
decides which (if any) to call — this replaces an explicit classification step.
After the agent finishes, an in-process presenter restyles the chosen
specialist's structured result into the requested tone.

Data flow for ``handle()``:
  1. load the session's chat history,
  2. run the ``create_agent`` router over ``history + query`` (it may call the
     ``solve_math`` / ``answer_history`` tool),
  3. inspect the resulting messages to recover which tool ran and its structured
     payload,
  4. run the presenter (specialist path) or its fallback (no tool) for the tone,
  5. record the turn back into history.
"""
import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.agents.base import BaseAgent
from app.chain.history_agent import HistoryAgentChain
from app.chain.math_agent import MathAgentChain
from app.chain.presenter_agent import PresenterAgentChain
from app.core.settings.config import get_settings
from app.database.mongo import get_checkpointer, get_history_collection
from app.utility.history import (
    ChatHistoryStore,
    MongoChatHistoryStore,
    maybe_await,
)
from app.utility.llm import get_llm

ROUTER_SYSTEM_PROMPT = (
    "You are a routing assistant with two specialist tools:\n"
    "- `solve_math` for arithmetic, algebra, calculus, equations, statistics.\n"
    "- `answer_history` for historical events, people, dates, eras, civilizations.\n"
    "When the query fits a specialist, call exactly one tool, then give the final "
    "answer using the tool's result. If neither specialist fits, answer the user "
    "directly and helpfully. Never fabricate a tool result."
)

# Map a tool name to the route label reported in the API response.
_TOOL_ROUTES = {"solve_math": "math", "answer_history": "history"}


class RouterAgent(BaseAgent):
    """Routes a query to math/history via tool-calling, then presents the answer."""

    name = "router"

    def __init__(
        self,
        model: str | None = None,
        provider: str | None = None,
        history_store=None,
    ) -> None:
        settings = get_settings()
        super().__init__(model=model or settings.default_model)

        # The specialists run in-process; they are wrapped as tools for the agent.
        self._math = MathAgentChain(model=model, provider=provider)
        self._history = HistoryAgentChain(model=model, provider=provider)
        self._presenter = PresenterAgentChain(model=model, provider=provider)

        # None when MongoDB is unavailable ⇒ the agent runs without a checkpoint,
        # and cross-turn context is spliced from the memory store instead (below).
        self._checkpointer = get_checkpointer()
        self._agent = create_agent(
            get_llm(provider=provider, model=model, temperature=0),
            tools=self._build_tools(),
            system_prompt=ROUTER_SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
        )
        # Durable transcript for routing/fallback context and the /sessions API.
        # Falls back to the in-memory store when MongoDB is unavailable.
        if history_store is not None:
            self.history = history_store
        else:
            collection = get_history_collection()
            self.history = (
                MongoChatHistoryStore(collection)
                if collection is not None
                else ChatHistoryStore()
            )

    def _build_tools(self) -> list:
        """Wrap the specialist chains as tools the router agent can call.

        Each tool returns the specialist's structured result as JSON so it flows
        back into the agent's context and can be recovered afterwards for the
        presenter and the API ``details`` field.
        """
        math_agent = self._math
        history_agent = self._history

        @tool
        async def solve_math(query: str) -> str:
            """Solve a math problem (arithmetic, algebra, calculus, equations, statistics).

            Args:
                query: The math question to solve.
            """
            out = await math_agent.invoke({"query": query})
            return json.dumps(out["result"].model_dump())

        @tool
        async def answer_history(query: str) -> str:
            """Answer a history question (events, people, dates, eras, civilizations).

            Args:
                query: The history question to answer.
            """
            out = await history_agent.invoke({"query": query})
            return json.dumps(out["result"].model_dump())

        return [solve_math, answer_history]

    async def run(self, prompt: str, **kwargs: Any) -> str:
        """Route and answer, returning just the final presented text."""
        result = await self.handle(prompt)
        return result["answer"]

    async def handle(
        self,
        query: str,
        tone: str = "friendly and clear",
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Route (via tool-calling), then present the answer in the requested tone.

        Reads the session history so follow-ups route with context, and records
        this turn afterwards. If the agent called a specialist tool, the presenter
        restyles that structured result; otherwise the presenter answers the
        query directly (fallback), which may ask for more information.
        """
        history = await maybe_await(self.history.get(session_id))

        # With a checkpointer, the thread already holds prior turns, so pass only
        # the new message. Without one (no Mongo), splice history from the store
        # so follow-ups still route with context.
        if self._checkpointer is not None:
            input_messages = [HumanMessage(content=query)]
        else:
            input_messages = [*history, HumanMessage(content=query)]
        config = {"configurable": {"thread_id": session_id}}
        state = await self._agent.ainvoke({"messages": input_messages}, config)
        messages = state["messages"]
        route, details, reasoning = self._inspect(messages)

        if route is None:
            presented = await self._presenter.respond(query, tone=tone, history=history)
            result = {
                "route": "fallback",
                "reasoning": reasoning or "No specialist matched; answered directly.",
                "answer": presented["answer"],
                "details": presented["result"].model_dump(),
            }
        else:
            # Prefer the structured payload; fall back to the agent's final text.
            content = details if details is not None else messages[-1].content
            presented = await self._presenter.invoke({"content": content, "tone": tone})
            result = {
                "route": route,
                "reasoning": reasoning or f"Routed to the {route} specialist.",
                "answer": presented["answer"],
                "details": details or {},
            }

        await maybe_await(self.history.add_user(session_id, query))
        await maybe_await(self.history.add_ai(session_id, result["answer"]))
        return result

    @staticmethod
    def _inspect(messages: list) -> tuple[str | None, dict | None, str]:
        """Recover (route, structured details, reasoning) for the CURRENT turn.

        Scans newest-first and takes the most recent tool call (route + reasoning)
        and the most recent tool result (details). This matters because the router
        is checkpointed: ``messages`` accumulates every prior turn, so scanning
        oldest-first would return a stale earlier turn's tool result.
        """
        route: str | None = None
        details: dict | None = None
        reasoning = ""
        for msg in reversed(messages):
            if details is None and isinstance(msg, ToolMessage):
                try:
                    details = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    details = None
            elif route is None and isinstance(msg, AIMessage) and msg.tool_calls:
                route = _TOOL_ROUTES.get(msg.tool_calls[0]["name"], route)
                if isinstance(msg.content, str) and msg.content.strip():
                    reasoning = msg.content.strip()
            if route is not None and details is not None:
                break
        return route, details, reasoning
