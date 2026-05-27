# Custom app roadmap: rich output, media, and zero-touch offices

This document plans work toward (1) a **structured, lively output panel** instead of a flat terminal stream, (2) **images and documents** in that output, wired to **office creation chat** uploads, and (3) a longer-term goal: **a short back-and-forth with “New Office” chat** yields a runnable office **without editing files or the shell**. Implementation can follow in phases after this plan is reviewed.

---

## 1. Goals and non-goals

### Goals

- **Readable output**: Turn streamed text into clear structure where appropriate (paragraphs, lists, emphasis) instead of monospace log lines only.
- **Visual output**: Support images (and later other media) in the output area—for example outfit references for **calendar stylist**—without requiring the user to open a separate app.
- **One pipeline for “assets”**: User-uploaded images/PDFs in **Create Office** chat should be storable under the office, referenceable from prompts, and **reusable** when we render rich output (same mental model: “this office has a `media/` folder and the UI knows how to show it”).
- **Progress toward zero-touch**: Each phase should reduce friction between “describe the office in chat” and “Run works end-to-end,” even if early phases still need light manual fixes.

### Non-goals (for early phases)

- Replacing DisSysLab’s **core** message format or all sinks with a proprietary protocol (we should extend or layer on top of what exists).
- **Guaranteed** fully autonomous office synthesis on the first try (LLM + external APIs will always need iteration); the plan targets **repeatable** flows and clear fallbacks.

---

## 2. Current state (baseline)

### Output panel (`OfficeView` + `OfficeOutputFeed`)

- Backend: `GET /api/offices/{name}/output` streams **SSE named events** — `event: log` (JSON `{"text":"..."}`) and `event: block` (markdown / image / json payloads). Lines prefixed with ``__DSLAPP__:`` + JSON on stdout become **block** events; lines that look like Markdown may be promoted to a markdown block (heuristic). When an office is started from this app, the subprocess sets **`DISSYSLAB_APP_SSE=1`**, so **`intelligence_display`** emits **markdown block** lines (same shape as email-style briefings) instead of ANSI “situation room” art.
- Frontend: **Activity** tab renders markdown (via `react-markdown`) and image blocks; **Raw log** shows the same stream as monospace text (ANSI stripped for display so escape codes never leak into the UI). RSS-style poll lines are **humanized** in Activity (short status text instead of raw URLs). Relative image paths under `media/` resolve to ``GET /api/offices/{name}/media/...``.

### Create-office chat (`ChatPanel` + backend)

- Attachments map to **Anthropic** content blocks during the chat.
- On **Create Office**, the same attachment bytes are persisted with ``POST /api/offices`` via optional ``chat_media`` into ``<office>/media/uploads/`` (images + PDF).

### Offices themselves

- Agents still emit plain stdout unless you print **``__DSLAPP__:{...}``** lines or the line matches the markdown heuristic. Sinks can be extended later to emit structured lines without hand-rolling JSON.

---

## 11. Implementation status (custom app v1)

| Item | Status |
|------|--------|
| Typed SSE (`log` / `block`) | Done |
| Activity vs Raw tabs + `react-markdown` | Done |
| ``__DSLAPP__:`` JSON protocol | Done (stdout one line = one JSON object after prefix) |
| Heuristic markdown detection | Done (conservative; tune as needed) |
| `DISSYSLAB_APP_SSE` + `intelligence_display` markdown | Done (set by `POST …/run`; CLI `dsl run` unchanged) |
| Activity: ANSI strip + RSS status humanization | Done (`OfficeOutputFeed.jsx`) |
| Activity: generic `[Source]` humanization (calendar, web scrape, MCP, …) | Done |
| `intelligence_display` URL line: **Link** vs **Apply** (heuristic) | Done |
| ``GET/POST …/media`` for `media/` subtree | Done (POST custom offices only) |
| Persist chat attachments on create | Done (`chat_media` on `POST /api/offices`) |
| Auto-validate `dsl build` in chat | Not done (Theme D) |

### ``__DSLAPP__`` examples (stdout, one line each)

```text
__DSLAPP__:{"t":"markdown","body":"## Briefing\n- First point\n- **Bold** emphasis"}
__DSLAPP__:{"t":"image","src":"media/uploads/abc123_photo.jpg","alt":"Outfit option A"}
```

---

## 3. Design principles

1. **Layered rendering**: Keep a **“raw / debug”** view (optional tab or collapsible) so power users and course staff can still see the exact subprocess log when something breaks.
2. **Contract over cleverness**: Prefer a **small, documented JSON envelope** (or NDJSON record types) for “render this block as markdown” / “show this image” rather than heuristics on arbitrary log text.
3. **Security**: Never treat subprocess stdout as HTML. **Markdown** should go through a safe pipeline (e.g. `react-markdown` + restricted plugins, no raw HTML or `rehype-raw` unless tightly controlled). **Images** must come from **allowed URLs** or **paths under the office directory** served by the backend—not arbitrary `file:` or remote SSRF vectors without an allowlist.
4. **Backward compatibility**: Offices that only print plain lines should **look the same or better** (wrapped text, subtle typography), not broken.

---

## 4. Theme A — Structured, “lively” text output

### Problem

Stdout lines mix framework noise (`Rebuilt …`, `[kalshi] …`) with user-facing briefings. Flat monospace rows do not express headings, bullets, or emphasis.

### Direction

**Phase A1 — Presentation layer (minimal backend change)**

- Introduce a **Markdown-capable** renderer for lines that are detected as “document-shaped” (e.g. start with `#`, `-`, `*`, or match a ` ``` ` fence), with a safe markdown library and CSS tuned to the app theme.
- Heuristic mode is fragile but unblocks demos quickly; pair with **Phase A2** quickly.

**Phase A2 — Typed stream records (recommended core)**

- Define a **JSON line protocol** (NDJSON) emitted on a **dedicated channel** or prefixed on stdout, e.g.:

  ```json
  {"t":"render","fmt":"markdown","body":"…"}
  {"t":"log","level":"info","body":"…"}
  ```

  Options:

  | Approach | Pros | Cons |
  |----------|------|------|
  | **A. Prefix on stdout** e.g. `__APP__:{json}` | No second pipe | Must filter in bridge; risk of clash with prints |
  | **B. Second stream (stderr vs stdout)** | Clean separation | Requires discipline in Python sinks |
  | **C. Side channel file or socket** | Cleanest | More infra |

  **Recommendation**: Start with **A or B** with a strict prefix / channel convention, documented for sink authors; the FastAPI bridge parses and forwards **typed SSE events** (`event: render` vs `event: log`) to the client.

**Phase A3 — Sink / framework hook (optional, cleaner)**

- Add or extend a **sink** (e.g. `app_display_sink`) that writes NDJSON to stdout or to a small local socket consumed by the custom app child wrapper—so agents don’t hand-craft prefixes. Longer lead time; aligns with DisSysLab’s sink model.

### Frontend

- Replace “array of strings” with **array of typed blocks**: `{ kind: 'log', text }`, `{ kind: 'markdown', text }`, `{ kind: 'divider' }`.
- **Tabs or split**: “Briefing” (rendered) vs “Raw log” (terminal style).

### Acceptance (Theme A)

- A long markdown briefing renders with headings and lists; framework one-liners stay in Raw or appear as muted log lines.

---

## 5. Theme B — Pictures (and docs) in the output panel

### Use cases

- **Calendar stylist**: Show 1–3 outfit images next to text (from static assets, URLs, or generated placeholders).
- **General**: Charts later; PDFs inline or as linked cards.

### Image sources (explicit product decision)

1. **Public HTTPS URLs** in structured output (user/agent provides URL; UI renders `<img>` with `referrerPolicy` / size limits).
2. **Office-scoped static files**: `user_offices/<name>/media/outfit1.jpg` — backend route `GET /api/offices/{name}/media/{path}` with **path traversal hardening** (resolve under office root only).
3. **Inline base64** (avoid for large images; prefer files + URLs for performance and caching).

### Protocol sketch

Extend NDJSON from Theme A2:

```json
{"t":"render","fmt":"markdown","body":"## Tuesday\nWear …"}
{"t":"image","src":"/api/offices/calendar_stylist/media/looks/tuesday.png","alt":"Tuesday outfit"}
```

### Backend

- **Serve media** from office directory with auth if the app ever leaves localhost (for now, same-origin is enough but design for auth).
- **Size limits** and MIME allowlist (images only first).

### Frontend

- Markdown renderer with **custom component** for `image` blocks (lazy-load, max height, lightbox optional).

### Acceptance (Theme B)

- Dropping an image into the office folder + referencing it from a structured message shows in the output panel without pasting a data URL into chat.

---

## 6. Theme C — Sync uploads with office creation and with output

**Implemented (create flow):** On **Create office**, the UI sends every attachment from every user message (in order). The backend writes ``media/uploads/image_0.<ext>``, ``image_1.<ext>``, … (``document_0.pdf`` for PDFs) so roles and ``__DSLAPP__`` URLs can match on disk.

### Target flow (remaining polish)

1. User attaches images/PDFs in **New Office** or **Customize** chat.
2. Backend optionally **saves** attachments under `user_offices/<name>/media/uploads/…` (dedupe names, store manifest JSON or manifest section in `office.md` front-matter—TBD).
3. Claude’s system prompt or appended context includes **paths and URLs** the model may emit in generated `office.md` / roles (e.g. “images live at `media/uploads/photo1.jpg`”).
4. **Output panel** resolves those paths via the same media route as Theme B.

### API sketch (planning only)

- `POST /api/offices/{name}/media` — multipart upload, returns `{ "path": "media/uploads/xyz.png", "url": "/api/offices/{name}/media/uploads/xyz.png" }`.
- Chat payload extended so the UI can signal **“persist these attachments to this office”** when the office name is known (create flow: after name chosen; or mid-thread if we allow provisional dir).

### Docs / prompts

- Update `CLAUDE_CONTEXT_OFFICE.md` (or equivalent) so Claude knows: **where assets go**, **how to reference them in roles**, and **not to embed secrets**.
- If an office uses the **`console_input`** source, **`default_message="..."`** must appear in `office.md`: the app runs subprocesses without interactive stdin, so that literal is the one-shot “user line” for **Run**.

### Acceptance (Theme C)

- Attach outfit JPEG in chat → appears under office `media/` → generated role text references it → Run shows image in structured output.

---

## 7. Theme D — “Few prompts → whole office” (north star)

This depends on A–C plus **reliability** and **validation**.

### Building blocks

1. **Structured office spec in chat**: Multi-step wizard (goal → sources/sinks → agents → connections) with Claude filling `office.md` + roles; human confirms at each step.
2. **Automatic validation**: After each generation, run **`dsl build`** (or compiler API) in-process; surface errors back into chat as “fix suggestions” without opening the editor.
3. **Role library hints**: Dropdown or tags for “start from situation_room / calendar_stylist template” to reduce hallucinated source names.
4. **Secrets outside chat**: Env panel already exists; plan should **forbid** pasting keys into `office.md` in generated content (lint rule).

### Phases toward the north star

| Phase | User-visible outcome |
|-------|----------------------|
| D1 | “Validate office” button + chat can read `dsl build` stderr and suggest edits |
| D2 | Wizard collects intent; Claude produces v1 office; one-click **Run** after successful build |
| D3 | Iterative repair loop in chat (edit same files until build passes) |
| D4 | Optional: generate **media placeholders** and ask user to upload replacements |

### Acceptance (Theme D, incremental)

- From empty folder to first successful **Run** with **no manual file edit** for at least one **template-backed** scenario (e.g. single-source analyst → console).

---

## 8. Suggested implementation order

1. **A2 + frontend blocks + Raw tab** — highest leverage; unblocks markdown and future media without fighting heuristics forever.
2. **B2 media API + image blocks** — unlocks calendar stylist–style demos.
3. **C persist chat uploads** — connects creation UX to output UX.
4. **A3 or sink** — only if prefix-based stream feels too brittle at scale.
5. **D1–D3** — validation and repair loops for zero-touch narrative.

---

## 9. Risks and open questions

- **Stdout interleaving**: Multiple threads printing at once can mangle NDJSON lines; may need a **single writer** or locking in the subprocess bridge (or move to structured sink only for “user visible” channel).
- **LLM output variability**: Markdown in JSON must be escaped correctly; consider **base64** for body or length limits + streaming chunk protocol.
- **Performance**: Large images in SSE; prefer **URLs** to static files over huge JSON events.
- **Licensing**: Outfit photos must be user-owned or licensed; app should not ship copyrighted lookbooks by default.
- **Open question**: Should “rich output” mirror **`intelligence_display`** HTML cards from the framework, or stay a **separate** custom-app channel? Long-term alignment with `intelligence_display` could reduce duplicate UI logic—worth a spike.

---

## 10. Summary

| Theme | Essence | First concrete step |
|-------|---------|------------------------|
| **A** Structured text | Typed events + markdown rendering + raw fallback | NDJSON contract + SSE event types + `react-markdown` |
| **B** Images | Safe `src` (office media or HTTPS) + `<img>` blocks | `GET /api/offices/{name}/media/...` + `{t:"image"}` |
| **C** Chat ↔ files | Persist uploads under office `media/` | `POST` media + prompt updates |
| **D** Zero-touch | Validate/build loop in chat | Call `dsl build` after generation, feed errors to Claude |

This file is the planning baseline; adjust priorities after a quick spike on **NDJSON over SSE** (Theme A2) to confirm feasibility with the current subprocess stdout bridge.
