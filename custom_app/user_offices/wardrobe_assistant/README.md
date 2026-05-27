# wardrobe_assistant

Calendar ICS + NOAA **MapClick** scrape + **`wardrobe_inventory.json`** + optional **multi-city Open-Meteo snapshots** (`wardrobe_run_config.json`) inform `wardrobe_stylist` → **`intelligence_display`**, **`wardrobe_outfits.jsonl`**, Gmail.

## Office files

| File | Purpose |
|------|---------|
| `office.md` | DSL wiring (sources, sinks, agents, connections). |
| `roles/*.md` | LLM personas. |
| **`wardrobe_inventory.json`** | **Canonical garment list** with **`photo_media`** paths (`media/uploads/image_*.png` in repo demo; JPG from chat uploads locally). Injected into every NL role at run-start. |
| **`wardrobe_run_config.json`** | `open_meteo_cities` array → prefetched rows appended as “Multi-city weather”. |

### Wardrobe images (`media/uploads/`)

Outfit tables and `__DSLAPP__` image blocks should use **`/api/offices/<office_name>/media/uploads/...`** URLs. The prefetch digest lists **Resolved Markdown** lines built from **`photo_media`** for each garment. After **AI Customize** swaps photos, attachments are saved to `media/uploads/` before Claude runs; ask Claude to emit an updated **`wardrobe_inventory.json`** fenced block when paths or items change. After manual edits under `media/uploads/`, keep `photo_media` in sync in the JSON.

**Git:** demo garment **PNGs** under `media/uploads/` are tracked; **`.jpg`** originals stay local (`custom_app/.gitignore`).

## Prefetch mechanics

`dsl run` (and thus the Custom App **Run**) calls `dissyslab.office.office_run_context.apply_office_run_context_to_environ(...)`, merging optional env payloads into Claude system prompts (`OFFICE_*_DIGEST` keys). **`python build/run.py` skips this** unless you export those vars yourself — prefer **`dsl run`**.

### Weather layering

| Layer | Source | Typical use |
|-------|--------|--------------|
| NOAA tombstones | `web_scraper` MapClick (`forecast.weather.gov`) | Multi-day wording + night/day splits for Pasadena-adjacent commutes |
| Open-Meteo snapshots | Derived from wardrobe config city list | “What’s NYC like right now when this flight arrives?” sanity check |

Tune cities in **`wardrobe_run_config.json`**; keep the MapClick URL near your habitual campus climate or swap latitude/longitude in `office.md` if you seldom leave that microclimate.

## Gmail & calendar knobs

Duplicate personalisation steps from `calendar_stylist`: swap ICS URLs, **`gmail_sink` `to=`**, Gmail env vars, etc.
