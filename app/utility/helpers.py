"""Generic helper utilities."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware current UTC timestamp."""
    return datetime.now(timezone.utc)
