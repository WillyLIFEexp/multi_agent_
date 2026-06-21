"""Math agent: a tool-using ReAct agent built on LangGraph.

Lives under ``chain`` because it is stateless (no cross-request memory). It
binds the math tools to an OpenAI model and lets the model decide which tools
to call to solve the user's query.
"""
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.chain.base import BaseChain
from app.core.settings.config import get_settings
from app.schema.agent import MathResult
from app.tools import MATH_TOOLS
from app.utility.llm import get_llm

SYSTEM_PROMPT = (
    "You are a precise math assistant. Use the provided tools to compute, "
    "solve equations, differentiate, integrate, and check numerical facts. "
    "Prefer tools over doing arithmetic in your head. Show the final answer "
    "clearly and briefly explain the steps."
)


class MathAgentChain(BaseChain):
    """Stateless math agent that solves queries using math tools."""

    def __init__(self, model: str | None = None, provider: str | None = None) -> None:
        settings = get_settings()
        self.model = model or settings.default_model
        llm = get_llm(provider=provider, model=model)
        # response_format makes the agent emit a structured MathResult alongside
        # its tool-using reasoning.
        self._agent = create_react_agent(
            llm, MATH_TOOLS, prompt=SYSTEM_PROMPT, response_format=MathResult
        )

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        messages = [HumanMessage(content=inputs["query"])]
        state = await self._agent.ainvoke({"messages": messages})
        result: MathResult = state["structured_response"]
        return {"result": result, "answer": result.answer}
