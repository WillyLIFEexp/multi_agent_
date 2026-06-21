"""History agent: a pure-LLM tutor returning structured output.

Lives under ``chain`` because it is stateless. It answers history questions
from the model's own knowledge (no tools) and returns a structured
``HistoryResult``.
"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.chain.base import BaseChain
from app.schema.agent import HistoryResult
from app.utility.llm import get_llm

SYSTEM_PROMPT = (
    "You are a knowledgeable and engaging history teacher. Answer the student's "
    "question accurately with relevant dates and context. Populate 'answer' with "
    "the explanation and 'key_facts' with the notable dates, names and facts. "
    "If a claim is uncertain or debated, say so."
)


class HistoryAgentChain(BaseChain):
    """Stateless history tutor backed purely by the LLM, structured output."""

    def __init__(self, model: str | None = None, provider: str | None = None) -> None:
        self._llm = get_llm(provider=provider, model=model).with_structured_output(
            HistoryResult
        )

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=inputs["query"]),
        ]
        result: HistoryResult = await self._llm.ainvoke(messages)
        return {"result": result, "answer": result.answer}
