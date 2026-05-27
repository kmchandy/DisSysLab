"""Offline tests for ``wardrobe_media`` helpers."""

from __future__ import annotations

import json
from pathlib import Path

from dissyslab.office import wardrobe_media
from dissyslab.office.office_run_context import build_office_run_context_env


def test_resolve_uses_photo_media(tmp_path: Path) -> None:
    root = tmp_path / "wardrobe_demo"
    (root / "media" / "uploads").mkdir(parents=True)
    (root / "media" / "uploads" / "a.jpg").write_bytes(b"jpeg")
    item = {
        "id": "item_a",
        "photo_media": "media/uploads/a.jpg",
    }
    rel, src = wardrobe_media.resolve_item_display_relative(root, item)
    assert rel == "media/uploads/a.jpg"
    assert src == "upload"


def test_resolve_legacy_media_alias(tmp_path: Path) -> None:
    root = tmp_path / "wardrobe_demo"
    (root / "media" / "uploads").mkdir(parents=True)
    (root / "media" / "uploads" / "x.png").write_bytes(b"png")
    item = {"id": "x", "media": "media/uploads/x.png"}
    rel, src = wardrobe_media.resolve_item_display_relative(root, item)
    assert rel == "media/uploads/x.png"
    assert src == "upload"


def test_inventory_digest_contains_resolved_upload_url(tmp_path: Path) -> None:
    slug = tmp_path / "my_office_slug"
    slug.mkdir()
    (slug / "office.md").write_text("# Office: x\nweatherapi()\n")
    (slug / "media" / "uploads").mkdir(parents=True)
    (slug / "media" / "uploads" / "snap.jpg").write_bytes(b"a")
    inv = {
        "items": [
            {
                "id": "item_shirt",
                "category": "top",
                "description": "test shirt",
                "photo_media": "media/uploads/snap.jpg",
            }
        ]
    }
    (slug / "wardrobe_inventory.json").write_text(json.dumps(inv), encoding="utf-8")
    ctx = build_office_run_context_env(slug)
    blob = ctx.get("OFFICE_WARDROBE_INVENTORY_DIGEST", "")
    assert "/api/offices/my_office_slug/media/uploads/snap.jpg" in blob
    assert ctx.get("OFFICE_RUNTIME_SLUG") == "my_office_slug"
