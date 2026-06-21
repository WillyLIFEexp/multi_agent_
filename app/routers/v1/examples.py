"""CRUD endpoints for the Example resource."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.schema.example import ExampleCreate, ExampleRead
from app.services.example_service import ExampleService

router = APIRouter(prefix="/examples", tags=["examples"])


def get_service(session: AsyncSession = Depends(get_session)) -> ExampleService:
    return ExampleService(session)


@router.get("", response_model=list[ExampleRead])
async def list_examples(service: ExampleService = Depends(get_service)):
    return await service.list()


@router.get("/{example_id}", response_model=ExampleRead)
async def get_example(
    example_id: int, service: ExampleService = Depends(get_service)
):
    example = await service.get(example_id)
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Example not found"
        )
    return example


@router.post("", response_model=ExampleRead, status_code=status.HTTP_201_CREATED)
async def create_example(
    payload: ExampleCreate, service: ExampleService = Depends(get_service)
):
    return await service.create(payload)
