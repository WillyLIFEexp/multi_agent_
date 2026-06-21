"""Business logic for the Example resource."""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.example import Example
from app.schema.example import ExampleCreate


class ExampleService:
    """Encapsulates persistence operations for Example."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> Sequence[Example]:
        result = await self.session.execute(select(Example))
        return result.scalars().all()

    async def get(self, example_id: int) -> Example | None:
        return await self.session.get(Example, example_id)

    async def create(self, payload: ExampleCreate) -> Example:
        example = Example(**payload.model_dump())
        self.session.add(example)
        await self.session.commit()
        await self.session.refresh(example)
        return example
