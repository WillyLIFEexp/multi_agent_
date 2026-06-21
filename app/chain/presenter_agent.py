"""Presenter agent: rewrites a sub-agent's result for the user in a given tone.

Lives under ``chain`` (stateless). It takes the raw/structured result produced
by another sub-agent and uses the LLM to construct a polished, reader-friendly
message in the requested tone of speech. Returns a structured ``PresentedResult``.
"""
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.chain.base import BaseChain
from app.schema.agent import PresentedResult
from app.utility.llm import get_llm

SYSTEM_PROMPT = (
    "You are a presentation assistant. Rewrite the provided content into a clear, "
    "final answer for the user, written in the requested tone of speech. Preserve "
    "all facts, numbers and steps faithfully; do not invent or change information. "
    "Set 'message' to the rewritten answer, 'tone' to the tone you applied, and "
    "'needs_more_info' to false."
)

FALLBACK_SYSTEM_PROMPT = (
    "You are a helpful assistant handling a query that did not match the math or "
    "history specialists. If the request is unclear, ambiguous, or missing details "
    "needed to answer well, ask the user a single concise clarifying question and "
    "set 'needs_more_info' to true. Otherwise, answer the question directly and "
    "helpfully and set 'needs_more_info' to false. Write your reply in the requested "
    "tone of speech. Set 'message' to your reply and 'tone' to the tone applied."
)


class PresenterAgentChain(BaseChain):
    """Stateless agent that styles content into a reader-friendly message."""

    def __init__(self, model: str | None = None, provider: str | None = None) -> None:
        self._llm = get_llm(provider=provider, model=model).with_structured_output(
            PresentedResult
        )

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        content = inputs["content"]
        tone = inputs.get("tone", "friendly and clear")
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Tone of speech: {tone}\n\nContent to present:\n{content}"
            ),
        ]
        result: PresentedResult = await self._llm.ainvoke(messages)
        return {"result": result, "answer": result.message}

    async def respond(
        self,
        query: str,
        tone: str = "friendly and clear",
        history: list[BaseMessage] | None = None,
    ) -> dict[str, Any]:
        """Fallback handling: answer the query directly or ask for more info.

        Used by the router when no specialist sub-agent fits the query. Prior
        conversation ``history`` is included so follow-ups stay coherent.
        """
        messages = [
            SystemMessage(content=FALLBACK_SYSTEM_PROMPT),
            *(history or []),
            HumanMessage(content=f"Tone of speech: {tone}\n\nUser query:\n{query}"),
        ]
        result: PresentedResult = await self._llm.ainvoke(messages)
        return {"result": result, "answer": result.message}
