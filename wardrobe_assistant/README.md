# Wardrobe Assistant (standalone app)

Product home: [`custom_app/wardrobe_stylist.md`](../custom_app/wardrobe_stylist.md) · Engineering checklist: [`custom_app/docs/WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md`](../custom_app/docs/WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md).

## What this app does today

| UX area | Behaviour |
|---------|-----------|
| **Sidebar** | Tabs for every major **secondary** flow in `wardrobe_stylist.md` §L39–L46 **plus** calendar run + office snapshot. |
| **Calendar office** | `Run` / `Stop` the DSL subprocess; live SSE output (same pipeline as Custom App). |
| **Occasion outfits** | No calendar fetch: text in → Anthropic → 1–3 Markdown options + **Pick A/B/C** → writes `wardrobe_state.json` wear counters + history. |
| **Closet stacks** | **Clean / worn / dirty** grids from `wardrobe_state.json`, per-garment wear limit, launder actions. |
| **Outfit history** | Human-readable log of occasion picks (basis for future stylist RAG — not injected into calendar office yet). |
| **Shopping advisor** | **Blind** text suggestions + **evaluate** multi-image uploads vs inventory (multimodal Claude). |
| **Office snapshot** | Read-only `office.md` roles list (editing stays in Custom App for now). |

**Persistence:** `custom_app/user_offices/<slug>/wardrobe_state.json` (auto-created / merged with `wardrobe_inventory.json` ids on first `GET /wardrobe/state`). **Requires user office** `wardrobe_assistant` (gallery offices are read-only elsewhere and do not get these routes).

**Backend routes** (all under `POST/GET /api/offices/{slug}/wardrobe/…` — see `custom_app/backend/wardrobe_routes.py`):

- `GET inventory`, `GET state`, `PUT state`
- `POST occasion-chat`, `POST pick-outfit`, `POST launder`
- `POST shopping/blind`, `POST shopping/evaluate` (multipart `images` + `note`)

## Still not the full long-term spec

- Sketch-only storage / VLM auto-catalog (see `wardrobe_stylist.md` L21–L24) — **not** implemented here.
- Outfit history is **not yet** fed back into the calendar `wardrobe_stylist` prompt automatically.
- In-app JSON editor for full `wardrobe_inventory.json` (vs Custom App **AI Customize**) — future work.

## Run (development)

1. **Backend** (sets `ANTHROPIC_API_KEY` in env or `.env`):

   ```bash
   cd custom_app/backend
   uvicorn main:app --reload --port 8000
   ```

2. **SPA** (proxies `/api` → port 8000, CORS allows `:5173`):

   ```bash
   cd wardrobe_assistant
   npm install
   npm run dev
   ```

3. Open **http://localhost:5173**

Custom App for all offices + file editor: **http://localhost:3000**

## Configuration

- Default slug: `WARDROBE_OFFICE_SLUG` in [`src/lib/api.js`](src/lib/api.js).
- Proxy target: [`vite.config.js`](vite.config.js).

## Build

```bash
npm run build
npm run preview
```

Production: serve static build behind same origin as API or extend `allow_origins` in `custom_app/backend/main.py`.
