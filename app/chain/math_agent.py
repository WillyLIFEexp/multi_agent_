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

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
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
        return {"result": self._repair_answer(result)}

    @staticmethod
    def _repair_answer(result: MathResult) -> MathResult:
        """Recover the ``answer`` field when a small model leaves a placeholder there.

        The finalizer reliably fills ``steps`` (e.g. "1 + 2 = 3") but weaker models
        sometimes drop a placeholder ("path/to/...", "") into ``answer``. When that
        happens, derive the answer deterministically from the last step's result so
        the field is never empty or nonsensical.
        """
        answer = (result.answer or "").strip()
        placeholder_markers = ("path/", "/final", "placeholder", "variable", "net_result")
        looks_bad = (
            answer in ("", ",", ", ")
            or any(marker in answer.lower() for marker in placeholder_markers)
        )
        if not looks_bad or not result.steps:
            return result
        last_step = result.steps[-1]
        derived = last_step.split("=")[-1].strip() if "=" in last_step else last_step.strip()
        return result.model_copy(update={"answer": derived}) if derived else result

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
