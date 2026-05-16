# Situation Room Pro

A variant of [`situation_room`](../situation_room/README.md) that
uses **Claude** for the writer role and **free local Qwen** for
everything else. Demonstrates DisSysLab's per-role backend
override: pay where it helps, run free where it doesn't.

## Why this exists

The base `situation_room` runs every role on the same backend
(Qwen3 via Ollama, free). Output is reliable and costs $0/month.

For some Pats, the writer's briefings would be sharper coming from
a stronger model. The four extractors (entity, severity, topic,
location) are closed-list classifications where the role-
decomposition pattern keeps SLM output structured; the lift from
moving them to Claude is small. The writer, generating prose, is
the role that benefits most from a strong model.

`situation_room_pro` makes exactly that one decision change:
Riley uses Claude, the four extractors stay on Qwen, and the
synchronizer + Sasha (deduplicator) run as before.

## Setup

You need both backends configured:

```bash
# Free local backend (default) — your office runs on this for
# four out of five LLM-driven roles.
ollama pull qwen3:30b
export DSL_BACKEND=ollama

# Plus Anthropic for Riley specifically.
echo "ANTHROPIC_API_KEY=sk-ant-..." >> ~/.dissyslab.env  # or your shell config
```

Then run as usual:

```bash
dsl run dissyslab/gallery/apps/situation_room_pro/
```

## Cost

For a typical morning run (10-15 articles):

| Role | Calls per run | Backend | Cost per run |
|---|---|---|---|
| Eve (entities) | ~10 | Qwen (local) | $0 |
| Sam (severity) | ~10 | Qwen (local) | $0 |
| Tom (topic) | ~10 | Qwen (local) | $0 |
| Greta (location) | ~10 | Qwen (local) | $0 |
| Riley (writer) | ~10 | **Claude Sonnet** | a few cents |
| **Total** | ~50 | mixed | a few cents |

Running daily for a month: roughly pennies-to-low-dollars total —
materially less than all-Claude (which is a few dollars to low tens
of dollars per month) and more than all-local (which is $0 in API
spend after the model download). Pat picks the cost/quality point
she wants.

> *Numbers above are rough estimates as of mid-2026. Anthropic and
> other providers change their pricing — check the provider's
> pricing page before relying on any specific figure here.*

## What makes this work

The single file that distinguishes `_pro` from `situation_room` is
[`roles/writer.py`](roles/writer.py). It reads the framework's
writer prompt and re-wraps it with `AI="claude"`. The framework's
[local-roles search](../../../../docs/BUILD_APPS.md) sees this
file first and uses it; the framework-shipped
`dissyslab/roles/writer.md` is shadowed for this office only.

You can apply the same pattern to any role in any office. Drop a
`.py` override in the office's `roles/` folder, read the
framework's prompt, set the backend. Three lines plus a path.

## See also

- [`situation_room/`](../situation_room/README.md) — the
  free-everywhere base office.
- [`docs/LANGUAGE_MODELS.md`](../../../../docs/LANGUAGE_MODELS.md)
  — backends, mixing, and the Backend Protocol.
- [`dev/PROMPTING_FOR_SLMS.md`](../../../../dev/PROMPTING_FOR_SLMS.md)
  — when SLMs handle a role well and when they don't.
