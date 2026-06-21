"""Pydantic schemas for the Example resource."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExampleBase(BaseModel):
    name: str
    description: str | None = None


class ExampleCreate(ExampleBase):
    """Payload for creating an Example."""


class ExampleRead(ExampleBase):
    """Representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
