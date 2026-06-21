"""A minimal LangGraph chain example.

Builds a single-node graph that runs an OpenAI agent. Extend by adding more
nodes / edges to ``StateGraph`` to orchestrate multi-step agent workflows.
"""
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.openai_agent import OpenAIAgent
from app.chain.base import BaseChain


class GraphState(TypedDict):
    """State passed between graph nodes."""

    prompt: str
    response: str


class SimpleGraphChain(BaseChain):
    """Wraps a compiled LangGraph graph behind the BaseChain interface."""

    def __init__(self, agent: OpenAIAgent | None = None) -> None:
        self.agent = agent or OpenAIAgent()
        self._graph = self._build()

    def _build(self):
        builder = StateGraph(GraphState)
        builder.add_node("agent", self._agent_node)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)
        return builder.compile()

    async def _agent_node(self, state: GraphState) -> dict[str, Any]:
        response = await self.agent.run(state["prompt"])
        return {"response": response}

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._graph.ainvoke({"prompt": inputs["prompt"], "response": ""})
