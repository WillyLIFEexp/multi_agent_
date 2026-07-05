"""KRI selector: pick the most relevant data-catalog entry for a query.

Stateless, so it lives under ``chain``. It reads only the *header* (topic +
description) of each catalog file via ``app.utility.catalog`` — never the table
or column detail — formats those headers into the prompt, and asks a
structured-output LLM to choose the single best-matching entry.

No vector store: the candidate set is small, so the headers are simply inserted
into the prompt. The graph is a single node, mirroring the history agent:

    START ──► select ──► END
"""
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.chain.base import BaseChain
from app.schema.agent import KRISelection
from app.utility.catalog import CatalogEntry, load_catalog
from app.utility.llm import get_llm

SYSTEM_PROMPT = (
    "You are a data-catalog assistant. You are given a numbered list of catalog "
    "entries, each with a topic and a short description. The underlying table and "
    "column details are intentionally hidden — choose using the descriptions only. "
    "Pick the SINGLE entry whose data would best help with the user's request and "
    "copy its 'topic' and 'file' values EXACTLY as shown. If none of the entries "
    "is relevant, set both 'topic' and 'file' to 'none'. Always explain your choice "
    "in 'reasoning'. Never invent a topic or filename that is not in the list."
)


class KRISelectorState(TypedDict):
    """State threaded between the selector graph's nodes."""

    query: str
    catalog: str
    result: KRISelection | None


def _format_catalog(entries: list[CatalogEntry]) -> str:
    """Render entry headers (topic + description only) as a numbered list."""
    return "\n".join(
        f"[{i}] topic: {e.topic}\n    file: {e.file}\n    description: {e.description}"
        for i, e in enumerate(entries, start=1)
    )


class KRISelectorChain(BaseChain):
    """Choose the best catalog entry for a query from lightweight headers."""

    def __init__(
        self,
        model: str | None = None,
        provider: str | None = None,
        catalog_dir: str | None = None,
    ) -> None:
        self._catalog_dir = catalog_dir
        self._llm = get_llm(
            provider=provider, model=model, temperature=0
        ).with_structured_output(KRISelection)
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(KRISelectorState)
        builder.add_node("select", self._select)
        builder.add_edge(START, "select")
        builder.add_edge("select", END)
        return builder.compile()

    async def _select(self, state: KRISelectorState) -> dict[str, Any]:
        """Ask the LLM to pick the best entry given the query + headers."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"User request:\n{state['query']}\n\n"
                    f"Catalog entries:\n{state['catalog']}"
                )
            ),
        ]
        result: KRISelection = await self._llm.ainvoke(messages)
        return {"result": result}

    @staticmethod
    def _validate(result: KRISelection, entries: list[CatalogEntry]) -> KRISelection:
        """Guard against a hallucinated file: keep the pick only if it exists.

        Falls back to matching on topic, otherwise reports 'none' so callers
        never receive a filename that isn't in the catalog.
        """
        by_file = {e.file: e for e in entries}
        if result.file in by_file:
            return result
        for entry in entries:
            if entry.topic.lower() == result.topic.lower():
                return result.model_copy(update={"file": entry.file})
        return result.model_copy(update={"topic": "none", "file": "none"})

    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        entries = load_catalog(self._catalog_dir)
        if not entries:
            result = KRISelection(
                topic="none", file="none", reasoning="No catalog entries were found."
            )
            return {"result": result, "answer": result.reasoning, "candidates": []}

        state = await self._graph.ainvoke(
            {
                "query": inputs["query"],
                "catalog": _format_catalog(entries),
                "result": None,
            }
        )
        result = self._validate(state["result"], entries)
        if result.file == "none":
            answer = f"No catalog entry fits this request. {result.reasoning}"
        else:
            answer = f"Use '{result.topic}' ({result.file}) — {result.reasoning}"
        return {
            "result": result,
            "answer": answer,
            "candidates": [e.file for e in entries],
        }
