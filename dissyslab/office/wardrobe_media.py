"""Resolve garment media paths declared in ``wardrobe_inventory.json``.

WardrobeAssistant uses **uploaded reference photos** under ``media/uploads/`` (`photo_media`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _norm_rel(rel: str | None) -> str | None:
    if not isinstance(rel, str):
        return None
    s = rel.strip().replace("\\", "/").lstrip("/")
    return s if s else None


def file_under_office(office_dir: Path, rel: str | None) -> Path | None:
    """Resolved path if ``rel`` is a regular file strictly under ``office_dir``."""
    r = _norm_rel(rel)
    if not r:
        return None
    root = Path(office_dir).resolve()
    candidate = (root / r).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def load_wardrobe_items(office_dir: Path) -> list[dict[str, Any]]:
    path = Path(office_dir) / "wardrobe_inventory.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("items")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def resolve_item_display_relative(
    office_dir: Path, item: dict[str, Any]
) -> tuple[str | None, str]:
    """Return ``(relative path from office root, label)``.

    Uses ``photo_media`` (or legacy ``media`` alias). Labels: ``upload``, ``missing``.
    """

    photo = item.get("photo_media", item.get("media"))
    photo_r = _norm_rel(photo) if photo else None
    if photo_r and file_under_office(office_dir, photo_r):
        return photo_r, "upload"

    return None, "missing"


def media_tail_api(relative_under_office: str) -> str:
    """``media/uploads/foo.jpg`` → ``uploads/foo.jpg`` for ``/api/offices/<slug>/media/…``."""
    rel = relative_under_office.strip().replace("\\", "/").lstrip("/")
    prefix = "media/"
    return rel[len(prefix) :] if rel.startswith(prefix) else rel


def markdown_image_url(office_slug: str, relative_under_office: str) -> str:
    tail = media_tail_api(relative_under_office)
    return f"/api/offices/{office_slug}/media/{tail}"


__all__ = [
    "file_under_office",
    "load_wardrobe_items",
    "resolve_item_display_relative",
    "media_tail_api",
    "markdown_image_url",
]
