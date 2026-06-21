"""FastAPI endpoints connecting to the agents.

- POST /agent/chat    -> RouterAgent: route -> sub-agent -> presenter (tone).
- POST /agent/math    -> MathAgentChain directly (structured output).
- POST /agent/history -> HistoryAgentChain directly (structured output).
- POST /agent/present -> PresenterAgentChain directly (style content in a tone).
"""
from functools import lru_cache

from fastapi import APIRouter, Depends

from app.agents.router_agent import RouterAgent
from app.chain.history_agent import HistoryAgentChain
from app.chain.math_agent import MathAgentChain
from app.chain.presenter_agent import PresenterAgentChain
from app.schema.agent import AgentAnswer, AgentQuery, AgentResponse, PresentRequest

router = APIRouter(prefix="/agent", tags=["agent"])


@lru_cache
def get_router_agent() -> RouterAgent:
    """Cached RouterAgent (and its sub-agents) shared across requests."""
    return RouterAgent()


@lru_cache
def get_math_agent() -> MathAgentChain:
    """Cached math agent shared across requests."""
    return MathAgentChain()


@lru_cache
def get_history_agent() -> HistoryAgentChain:
    """Cached history agent shared across requests."""
    return HistoryAgentChain()


@lru_cache
def get_presenter_agent() -> PresenterAgentChain:
    """Cached presenter agent shared across requests."""
    return PresenterAgentChain()


@router.post("/chat", response_model=AgentResponse)
async def chat(
    payload: AgentQuery, agent: RouterAgent = Depends(get_router_agent)
) -> AgentResponse:
    """Route the query, solve it, and present the answer in the chosen tone.

    The router uses the session's chat history to route follow-up questions.
    """
    result = await agent.handle(
        payload.query, tone=payload.tone, session_id=payload.session_id
    )
    return AgentResponse(**result)


@router.delete("/sessions/{session_id}", status_code=204)
async def clear_session(
    session_id: str, agent: RouterAgent = Depends(get_router_agent)
) -> None:
    """Clear the chat history for a session."""
    agent.history.clear(session_id)


@router.post("/math", response_model=AgentAnswer)
async def math(
    payload: AgentQuery, agent: MathAgentChain = Depends(get_math_agent)
) -> AgentAnswer:
    """Call the math agent directly (bypassing routing)."""
    result = await agent.invoke({"query": payload.query})
    return AgentAnswer(
        agent="math", answer=result["answer"], details=result["result"].model_dump()
    )


@router.post("/history", response_model=AgentAnswer)
async def history(
    payload: AgentQuery, agent: HistoryAgentChain = Depends(get_history_agent)
) -> AgentAnswer:
    """Call the history agent directly (bypassing routing)."""
    result = await agent.invoke({"query": payload.query})
    return AgentAnswer(
        agent="history", answer=result["answer"], details=result["result"].model_dump()
    )


@router.post("/present", response_model=AgentAnswer)
async def present(
    payload: PresentRequest, agent: PresenterAgentChain = Depends(get_presenter_agent)
) -> AgentAnswer:
    """Call the presenter agent directly to style content in a given tone."""
    result = await agent.invoke({"content": payload.content, "tone": payload.tone})
    return AgentAnswer(
        agent="presenter", answer=result["answer"], details=result["result"].model_dump()
    )
