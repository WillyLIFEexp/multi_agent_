"""History agent: a pure-LLM tutor built as an explicit LangGraph graph.

Lives under ``chain`` because it is stateless. It answers history questions from
the model's own knowledge (no tools), so its workflow is deliberately a single
node:

    START ──► answer ──► END

``answer`` is a structured-output LLM call that fills a ``HistoryResult``. The
graph is kept explicit (rather than a bare LLM call) so it mirrors the math
agent's shape and is trivial to extend later (e.g. add a retrieval node before
``answer`` without touching callers).
"""
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.chain.base import BaseChain
from app.schema.agent import HistoryResult
from app.utility.llm import get_llm

SYSTEM_PROMPT = (
    "You are a knowledgeable and engaging history teacher. Answer the student's "
    "question accurately with relevant dates and context. Populate 'answer' with "
    "the explanation and 'key_facts' with the notable dates, names and facts. "
    "If a claim is uncertain or debated, say so."
)


class HistoryState(TypedDict):
    """State threaded between the history graph's nodes."""

    query: str
    result: HistoryResult | None


class HistoryAgentChain(BaseChain):
    """Stateless history tutor backed purely by the LLM, as a LangGraph graph."""

    def __init__(self, model: str | None = None, provider: str | None = None) -> None:
        self._llm = get_llm(provider=provider, model=model).with_structured_output(
            HistoryResult
        )
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(HistoryState)
        builder.add_node("answer", self._answer)
        builder.add_edge(START, "answer")
        builder.add_edge("answer", END)
        return builder.compile()

    async def _answer(self, state: HistoryState) -> dict[str, Any]:
        """Produce the structured HistoryResult for the query."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state["query"]),
        ]
        result: HistoryResult = await self._llm.ainvoke(messages)
        return {"result": result}

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        state = await self._graph.ainvoke({"query": inputs["query"], "result": None})
        result: HistoryResult = state["result"]
        return {"result": result, "answer": result.answer}
