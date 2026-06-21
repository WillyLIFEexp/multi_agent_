"""Aggregates all v1 routers under a single APIRouter."""
from fastapi import APIRouter

from app.routers.v1 import agent, examples, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(examples.router)
api_router.include_router(agent.router)

__all__ = ["api_router"]
