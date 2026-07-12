"""MongoDB clients and the LangGraph checkpointer, as shared singletons.

Two clients are held because the pieces have different needs:

- an **async** ``AsyncMongoClient`` for the application memory store
  (``MongoChatHistoryStore``), which does real ``await``-ed I/O, and
- a **sync** ``MongoClient`` for ``MongoDBSaver``: this version of
  ``langgraph-checkpoint-mongodb`` ships a single saver that requires a sync
  client but exposes async methods (``aput`` / ``aget_tuple`` / ``adelete_thread``)
  that LangGraph calls during ``.ainvoke``.

Both are created once in the app lifespan (mirroring ``database/session.py``) and
read by the ``@lru_cache`` DI providers when they build agents on the first
request. If MongoDB is unreachable, ``init_mongo`` logs a warning and leaves the
singletons unset, so callers fall back to the in-memory store and an unpersisted
graph — this keeps ``uv run`` dev working without a running MongoDB.
"""
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.collection import AsyncCollection

from langgraph.checkpoint.mongodb import MongoDBSaver

from app.core.infra.logging import get_logger
from app.core.settings.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Fail fast in dev when nothing is listening, instead of the 30s default.
_SERVER_SELECT_TIMEOUT_MS = 3000

_async_client: AsyncMongoClient | None = None
_sync_client: MongoClient | None = None
_checkpointer: MongoDBSaver | None = None


async def init_mongo() -> None:
    """Connect to MongoDB and build the checkpointer; degrade gracefully on failure."""
    global _async_client, _sync_client, _checkpointer

    async_client = AsyncMongoClient(
        settings.mongodb_url, serverSelectionTimeoutMS=_SERVER_SELECT_TIMEOUT_MS
    )
    try:
        await async_client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001 - any connection failure ⇒ degrade
        await async_client.close()
        logger.warning(
            "MongoDB unavailable at %s (%s); using in-memory memory + no checkpointer.",
            settings.mongodb_url,
            exc,
        )
        return

    _async_client = async_client
    _sync_client = MongoClient(
        settings.mongodb_url, serverSelectionTimeoutMS=_SERVER_SELECT_TIMEOUT_MS
    )
    _checkpointer = MongoDBSaver(
        _sync_client,
        db_name=settings.mongodb_db_name,
        ttl=settings.mongodb_checkpoint_ttl,
    )
    logger.info("MongoDB connected: db=%s", settings.mongodb_db_name)


async def close_mongo() -> None:
    """Close both clients on shutdown."""
    global _async_client, _sync_client, _checkpointer
    if _async_client is not None:
        await _async_client.close()
    if _sync_client is not None:
        _sync_client.close()
    _async_client = _sync_client = _checkpointer = None


def get_checkpointer() -> MongoDBSaver | None:
    """The shared MongoDB checkpointer, or None when MongoDB is unavailable."""
    return _checkpointer


def get_history_collection() -> AsyncCollection | None:
    """The async chat-history collection, or None when MongoDB is unavailable."""
    if _async_client is None:
        return None
    return _async_client[settings.mongodb_db_name][settings.mongodb_history_collection]
