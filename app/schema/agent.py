"""Schemas for the multi-agent routing endpoint."""
from typing import Literal

from pydantic import BaseModel, Field

Route = Literal["math", "history", "fallback"]


class AgentQuery(BaseModel):
    """Incoming user query."""

    query: str = Field(..., min_length=1, description="The user's question.")
    tone: str = Field(
        default="friendly and clear",
        description="Tone of speech for the final, reader-facing answer.",
    )
    session_id: str = Field(
        default="default",
        description="Conversation id; the router uses its history to route.",
    )


class MathResult(BaseModel):
    """Structured output of the math sub-agent."""

    answer: str = Field(..., description="The final answer to the math problem.")
    steps: list[str] = Field(
        default_factory=list, description="Ordered steps showing the working."
    )


class HistoryResult(BaseModel):
    """Structured output of the history sub-agent."""

    answer: str = Field(..., description="The answer to the history question.")
    key_facts: list[str] = Field(
        default_factory=list, description="Relevant dates, names and facts."
    )


class KRISelection(BaseModel):
    """The catalog entry the selector judged most relevant to the query."""

    topic: str = Field(
        ..., description="Topic of the chosen catalog entry, or 'none' if nothing fits."
    )
    file: str = Field(
        ..., description="Markdown filename of the chosen entry, or 'none'."
    )
    reasoning: str = Field(
        ..., description="Why this entry (or none) best fits the user's request."
    )


class PresentedResult(BaseModel):
    """Structured output of the presenter sub-agent."""

    message: str = Field(..., description="Final response written for the user to read.")
    tone: str = Field(..., description="The tone of speech that was applied.")
    needs_more_info: bool = Field(
        default=False,
        description="True if the message is a clarifying question to the user.",
    )


class AgentResponse(BaseModel):
    """Response returned by the router endpoint."""

    route: Route
    reasoning: str
    answer: str  # final, tone-adjusted message for the user
    details: dict = Field(
        default_factory=dict, description="Structured output of the chosen sub-agent."
    )


class AgentAnswer(BaseModel):
    """Response returned when a specific sub-agent is called directly."""

    agent: str
    answer: str
    details: dict = Field(
        default_factory=dict, description="Structured output of the sub-agent."
    )


class PresentRequest(BaseModel):
    """Input for calling the presenter sub-agent directly."""

    content: str = Field(..., min_length=1, description="Content to present.")
    tone: str = Field(default="friendly and clear", description="Tone of speech.")
