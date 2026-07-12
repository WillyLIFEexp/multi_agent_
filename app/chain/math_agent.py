"""Math agent: a tool-using workflow built as an explicit LangGraph graph.

Lives under ``chain`` because it is stateless (no cross-request memory). Instead
of a prebuilt ReAct helper, it wires its own ``StateGraph`` so the reason/act
loop and the final structuring step are visible nodes:

    reason ──(tool calls?)──► act ──► reason
       │
       └──(no tool calls)──► respond ──► END

- ``reason``  : the LLM (with math tools bound) decides what to do next.
- ``act``     : a ``ToolNode`` executes any tool calls the LLM requested.
- ``respond`` : a final structured-output call distils the conversation into a
  validated ``MathResult``.
"""
from typing import Annotated, Any, TypedDict
from uuid import uuid4

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.chain.base import BaseChain
from app.core.settings.config import get_settings
from app.database.mongo import get_checkpointer
from app.schema.agent import MathResult
from app.tools import MATH_TOOLS
from app.utility.llm import get_llm

SYSTEM_PROMPT = (
    "You are a precise math assistant. Use the provided tools to compute, "
    "solve equations, differentiate, integrate, and check numerical facts. "
    "Prefer tools over doing arithmetic in your head. When you have enough "
    "information, stop calling tools and give the final answer."
)

RESPOND_PROMPT = (
    "You are finalizing the math result. The conversation above already contains "
    "the correct answer, computed by the tools and stated in the assistant's last "
    "message — do NOT recompute or invent anything.\n"
    "- 'answer': copy the exact final value verbatim (e.g. the number 3, or an "
    "expression like 3x^2). It must be a real value, never a variable name, a "
    "file path, a placeholder, or an empty string.\n"
    "- 'steps': the ordered working, each step ending in its result, with the "
    "last step showing the final answer (e.g. '1 + 2 = 3'). Never leave it empty."
)


class MathState(TypedDict):
    """State threaded between the math graph's nodes."""

    messages: Annotated[list[AnyMessage], add_messages]
    result: MathResult | None


class MathAgentChain(BaseChain):
    """Stateless math agent that solves queries via an explicit tool-loop graph."""

    def __init__(
        self,
        model: str | None = None,
        provider: str | None = None,
        checkpointer=None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.default_model
        # One model bound to the tools (drives the loop) and one bound to the
        # structured schema (produces the final MathResult).
        self._llm_tools = get_llm(provider=provider, model=model).bind_tools(MATH_TOOLS)
        self._llm_struct = get_llm(
            provider=provider, model=model
        ).with_structured_output(MathResult)
        # None when MongoDB is unavailable ⇒ graph runs unpersisted.
        self._checkpointer = checkpointer or get_checkpointer()
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(MathState)
        builder.add_node("reason", self._reason)
        builder.add_node("act", ToolNode(MATH_TOOLS))
        builder.add_node("respond", self._respond)
        builder.add_edge(START, "reason")
        builder.add_conditional_edges(
            "reason", self._route, {"act": "act", "respond": "respond"}
        )
        builder.add_edge("act", "reason")
        builder.add_edge("respond", END)
        return builder.compile(checkpointer=self._checkpointer)

    async def _reason(self, state: MathState) -> dict[str, Any]:
        """Let the LLM decide the next step (possibly requesting tool calls)."""
        response = await self._llm_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    @staticmethod
    def _route(state: MathState) -> str:
        """Loop back to tools while the LLM keeps requesting them, else finish."""
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "act"
        return "respond"

    async def _respond(self, state: MathState) -> dict[str, Any]:
        """Distil the tool-augmented conversation into a structured MathResult."""
        messages = [*state["messages"], HumanMessage(content=RESPOND_PROMPT)]
        result: MathResult = await self._llm_struct.ainvoke(messages)
        return {"result": self._repair(result, state["messages"])}

    @staticmethod
    def _repair(result: MathResult, messages: list[AnyMessage]) -> MathResult:
        """Backstop the finalizer with the conversation's ground truth.

        Weak models sometimes return an empty or placeholder ``MathResult`` even
        though the tools already computed the answer. Rebuild ``steps`` from the
        tool calls and their results, and ``answer`` from the last step (or the
        model's final text), so a completed calculation is never dropped.
        """
        # Pair each tool call's expression with its result → "expr = result" steps.
        call_args: dict[str, str] = {}
        tool_steps: list[str] = []
        final_text = ""
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for call in msg.tool_calls:
                    arg = next(iter((call.get("args") or {}).values()), "")
                    call_args[call.get("id", "")] = str(arg)
            elif isinstance(msg, ToolMessage):
                expr = call_args.get(msg.tool_call_id, "")
                content = str(msg.content).strip()
                tool_steps.append(f"{expr} = {content}".strip(" ="))
            elif isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
                final_text = msg.content.strip()

        steps = result.steps or tool_steps

        answer = (result.answer or "").strip()
        placeholder_markers = ("path/", "/final", "placeholder", "variable", "net_result")
        if answer in ("", ",", ", ") or any(m in answer.lower() for m in placeholder_markers):
            if steps and "=" in steps[-1]:
                answer = steps[-1].split("=")[-1].strip()
            elif final_text:
                answer = final_text

        return result.model_copy(update={"answer": answer, "steps": steps})

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        # Single-shot: a fresh thread_id per call so each run is checkpointed
        # independently, with no state bleeding between unrelated queries.
        config = {"configurable": {"thread_id": str(uuid4())}}
        state = await self._graph.ainvoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=inputs["query"]),
                ],
                "result": None,
            },
            config,
        )
        result: MathResult = state["result"]
        return {"result": result, "answer": result.answer}
