"""
Wardrobe Assistant API — occasion chat, closet stacks, outfit history, shopping.

Only **user offices** under ``custom_app/user_offices/{name}/`` are mutable.
Persisted beside ``wardrobe_inventory.json`` as ``wardrobe_state.json``.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, Union

import anthropic
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

_BACKEND_DIR = Path(__file__).resolve().parent
_CUSTOM_APP_DIR = _BACKEND_DIR.parent
USER_OFFICES_DIR = _CUSTOM_APP_DIR / "user_offices"

WARDROBE_STATE_FILE = "wardrobe_state.json"
WARDROBE_INVENTORY_FILE = "wardrobe_inventory.json"
OPTIONS_MARKER = "<<<WARDROBE_OPTIONS>>>"

_ALLOWED_IMAGE_MEDIA = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})
MAX_SHOP_IMAGE_BYTES = 8 * 1024 * 1024

router = APIRouter(prefix="/api/offices/{name}/wardrobe", tags=["wardrobe"])


def _user_office_dir(name: str) -> Path:
    d = USER_OFFICES_DIR / name.strip()
    if not d.is_dir() or not (d / "office.md").exists():
        raise HTTPException(status_code=404, detail=f"User office '{name}' not found")
    return d.resolve()


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _inventory_item_ids(inv: dict[str, Any] | None) -> list[str]:
    if not inv or not isinstance(inv.get("items"), list):
        return []
    out = []
    for row in inv["items"]:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            out.append(row["id"])
    return out


def _default_wear_record() -> dict[str, Any]:
    return {"stack": "clean", "wears_since_launder": 0, "max_wears_before_dirty": 5}


def merge_state_with_inventory(
    inv: dict[str, Any] | None, office_dir: Path
) -> tuple[dict[str, Any], bool]:
    path = office_dir / WARDROBE_STATE_FILE
    raw = _read_json_optional(path) or {}
    data: dict[str, Any] = {
        "version": 1,
        "wear_by_item": dict(raw.get("wear_by_item") or {}),
        "outfit_history": list(raw.get("outfit_history") or []),
    }
    ids = _inventory_item_ids(inv)
    changed = False
    wear = data["wear_by_item"]
    for gid in ids:
        if gid not in wear:
            wear[gid] = _default_wear_record()
            changed = True
    if changed:
        _atomic_write_json(path, data)
    return data, changed


def _extract_options_blob(text: str) -> tuple[str, list[dict[str, Any]] | None]:
    if OPTIONS_MARKER not in text:
        return text.strip(), None
    head, _, tail = text.partition(OPTIONS_MARKER)
    tail_st = tail.strip()
    opts: list[dict[str, Any]] | None = None
    try:
        blob = json.loads(tail_st)
        if isinstance(blob, dict) and isinstance(blob.get("options"), list):
            opts = blob["options"]
    except json.JSONDecodeError:
        opts = None
    return head.strip(), opts


def _call_claude(
    system: str, user_content: Union[str, list[dict[str, Any]]], model: str = "claude-opus-4-5"
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    blocks = (
        user_content
        if isinstance(user_content, list)
        else [{"type": "text", "text": user_content or "."}]
    )
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": blocks}],
    )
    chunks: list[str] = []
    for block in resp.content:
        if hasattr(block, "text"):
            chunks.append(block.text)
    return "".join(chunks).strip()


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------


@router.get("/inventory")
def wardrobe_get_inventory(name: str) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    if inv is None:
        raise HTTPException(status_code=404, detail=f"No {WARDROBE_INVENTORY_FILE} in this office")
    return {"office": name, "inventory": inv}


@router.get("/state")
def wardrobe_get_state(name: str) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    state, _ = merge_state_with_inventory(inv, office_dir)
    return {"office": name, "state": state, "inventory": inv}


class WardrobeStatePut(BaseModel):
    state: dict[str, Any]


@router.put("/state")
def wardrobe_put_state(name: str, payload: WardrobeStatePut) -> dict[str, str]:
    office_dir = _user_office_dir(name)
    s = payload.state
    if not isinstance(s.get("wear_by_item"), dict) or not isinstance(s.get("outfit_history"), list):
        raise HTTPException(
            status_code=400, detail="state needs wear_by_item (object) and outfit_history (array)"
        )
    cleaned = {
        "version": int(s.get("version", 1)),
        "wear_by_item": s["wear_by_item"],
        "outfit_history": s["outfit_history"],
    }
    _atomic_write_json(office_dir / WARDROBE_STATE_FILE, cleaned)
    return {"status": "saved"}


class OccasionPayload(BaseModel):
    occasion: str = Field(..., min_length=1)
    notes: str = ""


@router.post("/occasion-chat")
def wardrobe_occasion_chat(name: str, payload: OccasionPayload) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    if inv is None:
        raise HTTPException(status_code=400, detail="Add wardrobe_inventory.json first")
    inv_txt = json.dumps(inv, indent=2)
    oc = payload.occasion.strip()
    nt = payload.notes.strip()

    tail_inst = (
        f"After ALL Markdown, output ONE line exactly `{OPTIONS_MARKER}` then ONLY compact JSON: "
        '{"options":[{"id":"A","title":"...","garment_ids":["item_*"],"short_label":"..."},'
        '{"id":"B",...},{"id":"C",...}]}'
        ". No prose after JSON."
    )
    img_hint = (
        f"Markdown images MUST look like `/api/offices/{name}/media/uploads/<file>` "
        f'matching inventory `photo_media` (inventory says `media/uploads/foo.png` → '
        f"`![alt](/api/offices/{name}/media/uploads/foo.png)`)."
    )
    system_parts = [
        "You help pick outfits from a fixed wardrobe inventory JSON. NO calendar.",
        "Use ONLY garment ids from inventory items[].id.",
        "Produce exactly THREE Markdown sections: `### Option A`, `### Option B`, `### Option C`.",
        img_hint,
        "Layer tops left→right in wear order when multiple tops; bottoms similarly.",
        "### Inventory JSON",
        inv_txt,
    ]
    if nt:
        system_parts.extend(["### Extra constraints", nt])
    system_parts.extend(["### Structured tail", tail_inst])
    system = "\n".join(system_parts)

    user_blocks: list[dict[str, Any]] = [{"type": "text", "text": f"Occasion:\n{oc}"}]
    raw = _call_claude(system, user_blocks)
    md, opts = _extract_options_blob(raw)
    return {"office": name, "markdown": md or raw, "options": opts}


class PickOccasionPayload(BaseModel):
    occasion: str
    picked_id: str
    options: list[dict[str, Any]]


@router.post("/pick-outfit")
def wardrobe_pick_outfit(name: str, payload: PickOccasionPayload) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    state, _ = merge_state_with_inventory(inv, office_dir)

    pid = payload.picked_id.strip().upper()
    chosen = None
    for o in payload.options:
        oid = str(o.get("id", "")).strip().upper()
        if oid == pid:
            chosen = o
            break
    if chosen is None:
        raise HTTPException(status_code=400, detail=f"No option '{payload.picked_id}'")

    garment_ids = [x for x in (chosen.get("garment_ids") or []) if isinstance(x, str) and x.strip()]
    ids_set = set(_inventory_item_ids(inv))
    unknown = [g for g in garment_ids if g not in ids_set]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown garment ids: {unknown}")

    wear = state["wear_by_item"]
    for gid in garment_ids:
        rec = wear.setdefault(gid, _default_wear_record())
        mx = max(1, int(rec.get("max_wears_before_dirty", 5)))
        rec["max_wears_before_dirty"] = mx
        n = int(rec.get("wears_since_launder", 0)) + 1
        rec["wears_since_launder"] = n
        if n >= mx:
            rec["stack"] = "dirty"
        else:
            if rec.get("stack") == "clean":
                rec["stack"] = "worn"

    hist = state["outfit_history"]
    hist.append(
        {
            "id": str(uuid.uuid4()),
            "source": "occasion_chat",
            "occasion": payload.occasion.strip(),
            "picked": pid,
            "title": chosen.get("title") or chosen.get("short_label") or "",
            "garment_ids": garment_ids,
        }
    )
    state["outfit_history"] = hist[-200:]
    _atomic_write_json(office_dir / WARDROBE_STATE_FILE, state)
    return {"office": name, "state": state}


class LaunderPayload(BaseModel):
    item_ids: list[str]


@router.post("/launder")
def wardrobe_launder(name: str, payload: LaunderPayload) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    state, _ = merge_state_with_inventory(inv, office_dir)
    wear = state["wear_by_item"]
    for gid in payload.item_ids:
        if gid in wear:
            wear[gid]["stack"] = "clean"
            wear[gid]["wears_since_launder"] = 0
    _atomic_write_json(office_dir / WARDROBE_STATE_FILE, state)
    return {"office": name, "state": state}


class ShoppingBlindPayload(BaseModel):
    style_notes: str = ""


@router.post("/shopping/blind")
def wardrobe_shopping_blind(name: str, payload: ShoppingBlindPayload) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    if inv is None:
        raise HTTPException(status_code=400, detail="Need wardrobe_inventory.json")
    extras = payload.style_notes.strip()
    inv_txt = json.dumps(inv, indent=2)
    system_parts = [
        "Suggest 6–10 concrete garments or accessories to BUY based ONLY on wardrobe JSON.",
        "Use Markdown headings and bullets.",
        "### Wardrobe inventory",
        inv_txt,
    ]
    if extras:
        system_parts.extend(["### User style vibe", extras])
    system = "\n".join(system_parts)
    raw = _call_claude(system, "Blind purchase ideas now.")
    return {"office": name, "markdown": raw}


@router.post("/shopping/evaluate")
async def wardrobe_shopping_evaluate(
    name: str,
    note: str = Form(""),
    images: list[UploadFile] = File(),
) -> dict[str, Any]:
    office_dir = _user_office_dir(name)
    inv = _read_json_optional(office_dir / WARDROBE_INVENTORY_FILE)
    if inv is None:
        raise HTTPException(status_code=400, detail="Need wardrobe_inventory.json")
    if not images:
        raise HTTPException(status_code=400, detail="Attach at least one image")

    inv_txt = json.dumps(inv, indent=2)
    system = "\n".join(
        [
            "Evaluate candidate purchase garment photos versus existing wardrobe inventory JSON.",
            "Respond in Markdown: ## Summary, ## Overlap duplicates, ## Pairing opportunities.",
            "Reference garment ids where possible.",
            "### Wardrobe inventory",
            inv_txt,
        ]
    )

    media_blocks: list[dict[str, Any]] = []
    for uf in images[:8]:
        data = await uf.read()
        if not data:
            continue
        if len(data) > MAX_SHOP_IMAGE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image {uf.filename}: too large (max {MAX_SHOP_IMAGE_BYTES // (1024 * 1024)} MB)",
            )
        mt = (uf.content_type or "image/jpeg").strip().lower()
        if mt not in _ALLOWED_IMAGE_MEDIA:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported type {mt!r} for {uf.filename}",
            )
        b64_clean = base64.b64encode(data).decode("ascii")
        media_blocks.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mt, "data": b64_clean},
            }
        )
    if not media_blocks:
        raise HTTPException(status_code=400, detail="Could not read any images")

    nt = note.strip()
    lead_txt = nt or "Assess whether these candidate purchases complement the wardrobe."
    user_blocks: list[dict[str, Any]] = [{"type": "text", "text": lead_txt}] + media_blocks
    raw = _call_claude(system, user_blocks)
    return {"office": name, "markdown": raw}
