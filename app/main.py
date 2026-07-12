"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.infra.logging import configure_logging, get_logger
from app.core.settings.config import get_settings
from app.database.mongo import close_mongo, init_mongo
from app.database.session import init_db
from app.routers.v1 import api_router as api_router_v1

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    await init_db()
    await init_mongo()
    yield
    await close_mongo()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.include_router(api_router_v1, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
