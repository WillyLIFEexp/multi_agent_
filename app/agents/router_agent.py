"""Router agent: decides which sub-agent should handle a query and dispatches.

Lives under ``agents`` (not ``chain``) because it orchestrates the sub-agents.
It uses the LLM's structured-output capability to classify the query, then
delegates to the matching stateless chain.
"""
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.base import BaseAgent
from app.chain.history_agent import HistoryAgentChain
from app.chain.math_agent import MathAgentChain
from app.chain.presenter_agent import PresenterAgentChain
from app.core.settings.config import get_settings
from app.schema.agent import RouteDecision
from app.utility.history import ChatHistoryStore
from app.utility.llm import get_llm

ROUTER_SYSTEM_PROMPT = (
    "You are a routing classifier. Decide which specialist should answer the "
    "user's query:\n"
    "- 'math': arithmetic, algebra, calculus, equations, numbers, statistics.\n"
    "- 'history': historical events, people, dates, eras, civilizations.\n"
    "- 'fallback': anything else, or when the query is ambiguous/unclear and you "
    "cannot confidently pick math or history.\n"
    "Pick the single best route."
)


class RouterAgent(BaseAgent):
    """Classifies a query and routes it to math, history, or the presenter fallback."""

    name = "router"

    def __init__(
        self,
        model: str | None = None,
        provider: str | None = None,
        history_store: ChatHistoryStore | None = None,
    ) -> None:
        settings = get_settings()
        super().__init__(model=model or settings.default_model)
        self._classifier = get_llm(
            provider=provider, model=model, temperature=0
        ).with_structured_output(RouteDecision)
        self._chains = {
            "math": MathAgentChain(model=model, provider=provider),
            "history": HistoryAgentChain(model=model, provider=provider),
        }
        self._presenter = PresenterAgentChain(model=model, provider=provider)
        # The router carries conversation memory so it can route follow-ups.
        self.history = history_store or ChatHistoryStore()

    async def decide(
        self, query: str, history: list[BaseMessage] | None = None
    ) -> RouteDecision:
        """Classify the query into a route, considering prior conversation."""
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            *(history or []),
            HumanMessage(content=query),
        ]
        return await self._classifier.ainvoke(messages)

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
        """Route, solve, then present the answer in the requested tone.

        The router reads the session's chat history to inform routing (so a
        follow-up like "now solve it" is routed using earlier context), then
        records this turn back into the history.

        Steps: read history -> classify -> run the chosen sub-agent (structured
        output) -> run the presenter sub-agent to construct the reader-facing
        message. If no specialist fits (route 'fallback'), the presenter handles
        the query directly: it answers or asks the user for more information.
        """
        history = self.history.get(session_id)
        decision = await self.decide(query, history)

        if decision.route not in self._chains:
            presented = await self._presenter.respond(query, tone=tone, history=history)
            result = {
                "route": "fallback",
                "reasoning": decision.reasoning,
                "answer": presented["answer"],
                "details": presented["result"].model_dump(),
            }
        else:
            sub = await self._chains[decision.route].invoke({"query": query})
            structured = sub["result"]
            presented = await self._presenter.invoke(
                {"content": structured.model_dump(), "tone": tone}
            )
            result = {
                "route": decision.route,
                "reasoning": decision.reasoning,
                "answer": presented["answer"],
                "details": structured.model_dump(),
            }

        self.history.add_user(session_id, query)
        self.history.add_ai(session_id, result["answer"])
        return result
