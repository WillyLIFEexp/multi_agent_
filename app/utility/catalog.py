"""Read only the *header* (YAML frontmatter) of catalog markdown files.

The reader stops at the closing ``---`` fence, so the table/column body of each
file is never loaded into memory — only the ``topic`` / ``description`` metadata
reaches the LLM. This is what lets the KRI selector (``app/chain/kri_selector``)
choose a relevant catalog entry from lightweight headers alone, without a vector
store and without reading schema detail.
"""
from dataclasses import dataclass
from pathlib import Path

# repo_root/docs/data-catalog  (this file is app/utility/catalog.py)
DEFAULT_CATALOG_DIR = Path(__file__).resolve().parents[2] / "docs" / "data-catalog"


@dataclass
class CatalogEntry:
    """One catalog file's header — deliberately no table/column detail."""

    file: str
    topic: str
    description: str


def _read_frontmatter(path: Path) -> str | None:
    """Return the raw frontmatter block, reading only until the closing fence.

    Returns ``None`` if the file does not start with a ``---`` frontmatter block.
    The file body (tables, columns) is never read.
    """
    with path.open(encoding="utf-8") as fh:
        if fh.readline().strip() != "---":
            return None
        lines: list[str] = []
        for line in fh:
            if line.strip() == "---":  # closing fence — stop before the body
                return "\n".join(lines)
            lines.append(line.rstrip("\n"))
    return None  # no closing fence found


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple top-level ``key: value`` pairs from a frontmatter block.

    Indented lines and list items are skipped, so multi-line values (e.g. the
    ``tables:`` list) never leak schema detail into the parsed metadata.
    """
    meta: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line[0] in (" ", "\t", "-") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip()
    return meta


def load_catalog(directory: str | Path | None = None) -> list[CatalogEntry]:
    """Load ``topic``/``description`` headers for every ``*.md`` in ``directory``.

    Files without valid frontmatter are skipped. Only the header is read.
    """
    directory = Path(directory) if directory else DEFAULT_CATALOG_DIR
    if not directory.is_dir():
        return []

    entries: list[CatalogEntry] = []
    for path in sorted(directory.glob("*.md")):
        frontmatter = _read_frontmatter(path)
        if frontmatter is None:
            continue
        meta = _parse_frontmatter(frontmatter)
        entries.append(
            CatalogEntry(
                file=path.name,
                topic=meta.get("topic", path.stem),
                description=meta.get("description", ""),
            )
        )
    return entries
