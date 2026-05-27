# Wardrobe stylist — implementation plan

This document is the **engineering checklist** for **[`wardrobe_stylist.md`](../wardrobe_stylist.md)** (authoritative product narrative). Every table below maps **directly** to sentences or bullets in that file: line references are to `wardrobe_stylist.md` unless noted.

**Legend**

| Status | Meaning |
|--------|---------|
| **Done** | Shipped and usable today (may still need UX polish). |
| **Partial** | Some slice exists; the spec sentence is not fully satisfied. |
| **Not started** | No meaningful implementation yet. |
| **Deferred** | Explicitly postponed (see Notes). |

**Where code lives**

| Layer | Path / role |
|-------|-------------|
| DSL office (agents, calendar, wardrobe JSON, sinks) | `custom_app/user_offices/wardrobe_assistant/` |
| Shared HTTP API (run/stop/SSE, offices, media, chat) | `custom_app/backend/main.py` |
| Generic office browser + editor + Run UI | `custom_app/frontend/` |
| Standalone Wardrobe UI (intended superset) | `wardrobe_assistant/` (Vite app) |

---

## Scope reality check (read this first)

[`wardrobe_stylist.md` §“separate folder…” (L35–L36)](../wardrobe_stylist.md) says the **`wardrobe_assistant/`** React app should eventually **“be able to do all the above”** (primary pipeline) **and extend** with secondary features.

**What exists today:** **`wardrobe_assistant/`** sidebar delivers **Occasion outfits** (`POST /wardrobe/occasion-chat` + pick → `wardrobe_state.json`), **Closet stacks** (`GET/PUT state`, launder), **History**, **Shopping** (blind text + image evaluate), plus **Calendar office** Run/SSE and **Office snapshot**. **Not yet:** auto sketch pipeline, in-SPA full inventory editor, injecting outfit history into calendar stylist prompts, richer garment-composer layout primitives.

That gap is **expected** until items in **§5** (“Suggested implementation order”) are shipped **in the SPA + backend**. The plan orders work to match **`wardrobe_stylist.md`**, not to oversell today’s scaffold.

---

## 1. Primary pipeline — “This is a system of agents…” (`wardrobe_stylist.md` L9–L31)

### 1.1 Calendar monitoring (L10)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| Monitor the user’s calendar for upcoming events | L10 | **Done** | `Sources: calendar(...)` in `user_offices/wardrobe_assistant/office.md`. ICS URL is user-owned. |

### 1.2 Per-event context: date, weather, place default (L11–L13)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| For each event: date / time | L11 | **Done** | `roles/calendar_analyst.md`; `office_run_context` + NL prompts. |
| Weather for **time and place**; place from event or default (**Pasadena CA** when missing) | L11–L13 | **Partial** | NOAA MapClick + Open-Meteo digests; analyst role encodes Pasadena default. Fully automatic ICS→coords for every venue is not done. |

### 1.3 Wardrobe access: text and/or pictures (L14–L20)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| Wardrobe from **text descriptions or list** of clothes | L15–L18 | **Partial** | **`wardrobe_inventory.json`** + `photo_media`; AI Customize can edit JSON/roles. No dedicated “wardrobe CRUD” UX in either React app. |
| User inputs via **chatbot in the React app** | L18 | **Partial** | **Custom App:** generic **AI Customize** chat (not wardrobe-specific flows). **Standalone:** no chat yet. |
| User **uploads pictures**; **agents process images and build a list** of clothes | L19–L20 | **Not started** | Uploads land under `media/uploads/`; **no** automated vision→normalized inventory job. |
| Generate **2D flat sketches** per item; **associate** with descriptions; long-term **store sketches not raw photos** (L21–L24) | L21–L24 | **Deferred** | **Explicitly contradicted for “now”** at top of [`wardrobe_stylist.md`](../wardrobe_stylist.md): current implementation uses **reference photos** via `photo_media`. Sketch-only storage TBD with an image model pipeline. |

### 1.4 Outfit suggestions + layout (L25–L29)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| Suggest outfits from wardrobe using **weather, event type, date** | L25–L26 | **Done** | `wardrobe_stylist` + digests in `office_run_context` / `dsl run`. |
| **React app** shows how the outfit looks (using sketches in the long-term story) | L26 | **Partial** | **Custom App / standalone:** SSE **Activity** panel = markdown + images / `__DSLAPP__` blocks. **Not** a bespoke garment composer UI. |
| Layout: **top/shirt above**, **bottom below** | L27 | **Partial** | Enforced in **prompts** (`roles/wardrobe_stylist.md`); fragile if the model emits broken tables. Dedicated UI rails TBD. |
| **Multiple tops** in **one row**, L→R wear order; **bottoms** likewise (L28) | L28 | **Partial** | Same: prompt + SSE display polish (see `OfficeOutputFeed` / backend markdown expansion). |

### 1.5 Display + email (L29)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| Show outfit on screen **in the React app** | L29 | **Partial** | Same as §1.4 “React app” row. |
| **Email** outfit and layout | L29 | **Done** | `gmail_sink` + `roles/summary_compiler.md` (env: Gmail credentials). |

### 1.6 Note: implement primary in `user_offices/wardrobe_assistant` (L33–L34)

| Spec | Src | Status | Notes |
|------|-----|--------|-------|
| Primary behavior should live in **`custom_app/user_offices/wardrobe_assistant`**, extend **calendar_stylist** patterns, reuse current **image** handling | L33–L34 | **Partial** | Office exists and runs; gaps are **§1.3 vision catalog**, **§1.4 dedicated layout UI**, and full **§7–8** standalone experience. |

---

## 2. Standalone app mandate (`wardrobe_stylist.md` L35–L36)

| Spec (paraphrase) | Src | Status | Notes |
|-------------------|-----|--------|-------|
| **Separate folder** `wardrobe_assistant` (**DisSysLab repo:** `DisSysLab/wardrobe_assistant/`) | L35 | **Partial** | Folder + Vite app exist. |
| **Full-stack React on its own**, **extension** of the wardrobe office | L35 | **Partial** | Frontend only today; **depends on** `custom_app/backend` for API. |
| Must **“do all the above”** (primary pipeline UX + behavior surface) | L36 | **Partial** | Dedicated tabs cover occasion chat + stacks + shopping + calendar run. **Gaps:** bespoke layout composer UI, full inventory editor in SPA, history→stylist RAG hookup, sketch pipeline. |
| **Then extend** with functionalities in **§3** (below) | L36 | **Partial** | Closet + occasion + shopping tabs ship; wear budgeting + laundering live in `wardrobe_state.json`. Purchase photo eval uses Anthropic vision. |

---

## 3. Secondary tasks (“Secondary tasks include:” `wardrobe_stylist.md` L37–L46)

Intro (L38): **other buttons on the display** + different behaviors.

### 3.1 Event-free outfit generation + pick (L39)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| **Regular** outfit generation **without** fetching calendar events first | L39 | **Partial** | `POST /wardrobe/occasion-chat` uses **Anthropic + `wardrobe_inventory.json`**; Wardrobe SPA **Occasion outfits** tab. |
| User **picks** one of the suggestions | L39 | **Partial** | **Pick option A/B/C** buttons call `POST /wardrobe/pick-outfit`; requires model-emitted JSON tail (`<<<WARDROBE_OPTIONS>>>` spec in prompt). |

### 3.2 Wardrobe DB update on pick + clean vs worn (L39–L40)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| On pick, **update the wardrobe database** | L39–L40 | **Partial** | Persisted **`wardrobe_state.json`** beside inventory (does not mutate `wardrobe_inventory.json`). |
| Track **what was worn** vs **still clean** | L40 | **Partial** | `wear_by_item[].stack`: **clean \| worn \| dirty**, `wears_since_launder`; pick increments wears. |

### 3.3 Stacks on display + laundering + reuse (L41)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| Show **clean stack** vs **worn stack** on the display | L41 | **Partial** | **Closet stacks** tab (also shows **dirty** when over wear budget). |
| **Re-add to clean** after laundered | L41 | **Partial** | `POST /wardrobe/launder` (+ per-stack / per-garment UI). |
| **Reuse** garments with **per-item wear budget** (e.g. jeans **5 wears** → “dirt pile”) | L41 | **Partial** | **`max_wears_before_dirty`** per item; crosses → **dirty**. |

### 3.4 Past outfits → future suggestions (L42)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| **Track outfits worn over time**; use for **future suggestions** | L42 | **Partial** | SPA **Outfit history** reads `state.outfit_history`. **Still missing:** summarize/inject rolling window into **`wardrobe_stylist`** calendar runs (DSL). JSONL archival remains separate surface. |

### 3.5 Shopping helpers (L43–L46)

| Spec (paraphrase) | Src | Status | Notes / implementation |
|-------------------|-----|--------|------------------------|
| **Blind suggestion:** agents suggest great **additions** from style + wardrobe + outfit gaps | L44–L45 | **Partial** | `POST /wardrobe/shopping/blind`; **Shopping advisor** tab. |
| User **uploads images** of candidate purchases → **duplicate** check + **combinability** with wardrobe | L45–L46 | **Partial** | `POST /wardrobe/shopping/evaluate` (multipart) + multimodal Claude. |

---

## 4. Cross-cutting gaps called out in `wardrobe_stylist.md` header

| Topic | Src | Status | Notes |
|-------|-----|--------|-------|
| **Reference photos** vs **flat sketches** | `wardrobe_stylist.md` L3–L4 | **As documented** | Product paragraphs L21–L24 remain **long-term vision**; repo implements **photos + `photo_media`** until sketch pipeline exists. |

---

## 5. Suggested implementation order (aligned to product, not folder names)

1. **Primary DSL + Custom App (in progress):** keep improving `user_offices/wardrobe_assistant` + run context + prompts for weather, inventory, and email (§1).  
2. **Standalone parity for §1 UX:** `wardrobe_assistant/` grows real **screens** (inventory summary, media, richer run affordances)—**incremental:** *Office & roles* tab reads `GET /api/offices/{slug}` for YAML description + role list; **`wardrobe_inventory.json` still edited via Custom App** until an editor ships.
3. **Occasion chat + pick** (§3.1) + **state file / API** for picks (§3.2).  
4. **Clean / worn / launder + wear limits + stack UI** (§3.2–3.3).  
5. **Structured outfit history + optional RAG for stylist** (§3.4).  
6. **Shopping flows** (§3.5).  
7. **Vision catalog + sketch pipeline** when product prioritizes it (§1.3–1.4 deferred items).

---

## 6. Summary scorecard (mirror of `wardrobe_stylist.md`)

| Area | Coverage |
|------|----------|
| Primary agents + email (§1, L9–L31) | **Mostly done** in DSL; **Partial** on dedicated React layout, auto photo→catalog, sketches. |
| Standalone app “all the above + extend” (L35–L36) | Spec still **far from done**. **Incremental:** Run/SSE + **Office & roles** tab (`GET /api/offices/{slug}`). |
| Secondary L37–L46 | **Not started** (except **Partial** outfit logging via JSONL). |

---

*Last updated to align section numbering and requirements with **`custom_app/wardrobe_stylist.md`** (L9–L46) and to state explicitly that the current **`wardrobe_assistant/`** SPA does not yet implement that full scope.*
