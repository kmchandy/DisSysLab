# DisSysLab documentation

If you're new, the [top-level README](../README.md) is the right
starting point — install, pick an AI engine, run your first office.
Come back here when you have a specific question.

## Quick map by audience

There are two kinds of reader. Most of these docs serve both, but
the entry points differ.

**Running an office that ships with DisSysLab** (you're Pat —
small-business owner, journalist, analyst, anyone with continuous
information work):

1. [Top-level README](../README.md) — install + first office.
2. [Gallery README](../dissyslab/gallery/README.md) — every office
   that ships, split into "runs on any laptop, no keys" and "needs an
   API key."
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — common errors keyed on
   the actual error strings. `dsl doctor` from your terminal runs the
   same checks live.
4. [recipes/](recipes/README.md) — short copy-pasteable changes for
   "I want my office to do X."

**Extending DisSysLab with new sources, sinks, roles, or patterns**
(you're Kamala — Python-fluent, building things for others to use):

1. [BUILD_APPS.md](BUILD_APPS.md) — design and wire your own office
   from scratch. Start here.
2. [SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md) — the catalog of
   built-in components and their arguments. Look here before writing
   a new one.
3. [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md) — per-role backend
   override, the Backend Protocol for adding a new LLM provider.
4. [MAKE_OFFICE.md](MAKE_OFFICE.md) — the Python API for
   *generating* offices instead of hand-writing them. Use this when a
   tool needs to emit office.md programmatically.
5. [PATTERN_sense_think_respond.md](PATTERN_sense_think_respond.md) —
   the sense → think → respond pattern that most gallery offices
   instantiate, and the `build_office()` generator that emits new
   instances.
6. [`../RESEARCH_TODO.md`](../RESEARCH_TODO.md) — the year-horizon
   research agenda (community libraries, polyglot AI, chatbots).
   Pick a thread, contribute.

## Recipes — copy-pasteable patterns

Each recipe solves one concrete task by editing two plain-English
files (`office.md` and a role under `roles/`):

- **[Filter for a topic](recipes/filter-for-a-topic.md)** — keep only
  items you care about, discard the rest.
- **[Monitor your inbox](recipes/monitor-your-inbox.md)** — turn
  Gmail messages into briefings, with App Password setup.
- **[Receive webhooks](recipes/receive-webhooks.md)** — listen on a
  local port for posts from GitHub, Stripe, Zapier, or your own
  scripts.
- **[Send messages outside](recipes/send-messages-outside.md)** —
  forward briefings to email, Slack, a webhook, or a JSONL file.
- **[Add an RSS source](recipes/add-an-rss-source.md)** — pull from
  any RSS or Atom feed.
- **[Chain offices](recipes/chain-offices.md)** — let one office's
  output flow into another.
- **[Write a custom role](recipes/write-a-custom-role.md)** —
  describe a new job in plain English and assign it to an agent.

The full index, including recipes added later, is at
[recipes/README.md](recipes/README.md).

## Reference

- **[SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md)** — every component
  the framework ships with, with arguments, env vars, and setup
  instructions.
- **[LANGUAGE_MODELS.md](LANGUAGE_MODELS.md)** — switch the office's
  AI engine (Ollama / OpenRouter / Claude), mix backends per role,
  add a new provider via the Backend Protocol.
- **[BUILD_APPS.md](BUILD_APPS.md)** — design and wire your own
  office: org-chart shapes, prompt-writing tips, when to split into
  sub-offices.
- **[MAKE_OFFICE.md](MAKE_OFFICE.md)** — the Python API for
  generating offices programmatically.
- **[PATTERN_sense_think_respond.md](PATTERN_sense_think_respond.md)** —
  the canonical multi-stage pattern + the `build_office()` generator
  used by most gallery offices.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — error messages and
  fixes.

## Looking for something specific?

- *"How do I use OpenAI / Gemini / Ollama / a local model?"* →
  [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md).
- *"How do I build my own office?"* → [BUILD_APPS.md](BUILD_APPS.md).
- *"How do I generate offices from Python code?"* →
  [MAKE_OFFICE.md](MAKE_OFFICE.md).
- *"How do I send results to Slack / email / a file?"* →
  [send-messages-outside.md](recipes/send-messages-outside.md).
- *"How do I read my Gmail?"* →
  [monitor-your-inbox.md](recipes/monitor-your-inbox.md).
- *"How do I add a new RSS feed?"* →
  [add-an-rss-source.md](recipes/add-an-rss-source.md).
- *"What sources and sinks come with the package?"* →
  [SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md).
- *"How do I connect two offices together?"* →
  [chain-offices.md](recipes/chain-offices.md).
- *"How do I write a role from scratch?"* →
  [write-a-custom-role.md](recipes/write-a-custom-role.md).
- *"I hit an error and don't know what it means."* →
  [TROUBLESHOOTING.md](TROUBLESHOOTING.md), or run `dsl doctor`.
- *"What's coming next in DisSysLab?"* →
  [`../RESEARCH_TODO.md`](../RESEARCH_TODO.md).

Missing? Open an issue on
[GitHub](https://github.com/kmchandy/DisSysLab/issues) — that's the
fastest way to get an answer and to flag a gap in the docs.

---

Internal design notes (for contributors to the framework itself, not
users running offices) live in `dev/` and are not indexed here. They
change frequently.
