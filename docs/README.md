# DisSysLab user guide

This folder is the user manual for DisSysLab. The
[top-level README](../README.md) is the place to start — it covers
installation, the first office to run, and the framework's core
design ideas. Come here after the first office runs successfully,
when the question is *how do I build my own?* or *how do I do
this specific thing?*

The documents below assume DisSysLab is already installed and that
`dsl run periodic_brief` produced a brief on your terminal.

## Where to start

A reader new to DisSysLab has two on-ramps. Pick the one that
matches whether you already have an LLM API key.

**No key yet — explore the gallery first:**

1. Run [periodic_brief](../dissyslab/gallery/apps/periodic_brief/).
   It produces a styled morning HTML brief with zero LLM calls
   — news headlines, weather, stock tickers — in about ten
   seconds. This shows the framework running without any setup.
2. Browse the [gallery](../dissyslab/gallery/README.md). Each
   office in `apps/` is a working example you can read.

**Have an LLM API key — let Claude draft an office for you:**

1. `dsl new my_office` — describe what you want; Claude drafts
   `office.md` plus the role files.
2. `dsl run my_office` to see Claude's draft execute.
3. Iterate by editing the English in `office.md` or `roles/*.md`.
   Nine times out of ten the office you want is one or two edits
   away from Claude's first draft.

**Then, for either reader:**

- [BUILD_APPS.md](BUILD_APPS.md) — the `office.md` grammar and
  what each piece does.
- [SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md) — the sources and
  sinks the framework ships with. Most new offices can be
  assembled from existing components.
- `dsl init <name> my_office` to copy a gallery office close to
  what you want and modify it. Many users never need to write an
  office from scratch.

When something does not work, [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
indexes the common errors by their exact text. The command
`dsl doctor` runs the same checks live in your terminal.

## Documents in this folder

| Document | Subject | When to read |
|---|---|---|
| [BUILD_APPS.md](BUILD_APPS.md) | Designing and wiring your own office, from idea to running system. Includes the full `office.md` grammar and a worked example of a substantial role. | Before writing your first office from scratch. |
| [SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md) | Every source and sink component the framework ships with, with arguments, environment variables, and setup notes. | Reference. Consult before writing a custom source or sink. |
| [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md) | Choosing and mixing LLM backends (`anthropic`, `openai`, `gemini`, `openrouter`, `ollama`), per-role backend overrides, named variants (`_creative`, `_precise`), and the Backend Protocol for adding a new provider. | Before changing the office's AI engine or adding a new provider. |
| [PATTERN_sense_think_respond.md](PATTERN_sense_think_respond.md) | The canonical multi-stage pattern that most gallery offices instantiate. Includes a Python helper for generating new instances of the pattern. | When the office you want resembles `sense → think → respond`. |
| [EXTENDING.md](EXTENDING.md) | When to use English (Claude), when to write Python, when to promote to the framework library. The layered framework surface, named for the three audiences. | When you are unsure where your changes belong (local office vs. framework). |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Error messages from `dsl run` and `dsl build`, with the cause and the remedy for each. | When something goes wrong. The companion command is `dsl doctor`. |

## Recipes

The [recipes/](recipes/) folder holds short, copy-pasteable
solutions to common tasks. Each recipe edits one or two plain
English files — typically an `office.md` and a role under
`roles/`:

| Recipe | What it does |
|---|---|
| [Filter for a topic](recipes/filter-for-a-topic.md) | Keep items that mention something specific, discard the rest. |
| [Monitor your inbox](recipes/monitor-your-inbox.md) | Turn Gmail messages into briefings, with App Password setup. |
| [Receive webhooks](recipes/receive-webhooks.md) | Listen on a local port for posts from GitHub, Stripe, Zapier, or your own scripts. |
| [Send messages outside](recipes/send-messages-outside.md) | Forward briefings to email, Slack, a webhook, or a JSONL file. |
| [Add an RSS source](recipes/add-an-rss-source.md) | Read items from any RSS or Atom feed. |
| [Chain offices](recipes/chain-offices.md) | Let one office's output flow into another. |
| [Write a custom role](recipes/write-a-custom-role.md) | Describe a new job in plain English and assign it to an agent. |

## Lookup by task

For frequently asked questions, the relevant section of the
documentation is named below.

- *Pick an LLM backend* —
  [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md).
- *Use a different backend for one specific agent* —
  [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md), the per-role override
  section.
- *Build a new office from scratch* —
  [BUILD_APPS.md](BUILD_APPS.md).
- *Read Gmail messages* —
  [recipes/monitor-your-inbox.md](recipes/monitor-your-inbox.md).
- *Send results to Slack, email, or a file* —
  [recipes/send-messages-outside.md](recipes/send-messages-outside.md).
- *Add a new RSS feed* —
  [recipes/add-an-rss-source.md](recipes/add-an-rss-source.md).
- *Connect two offices together* —
  [recipes/chain-offices.md](recipes/chain-offices.md).
- *Write a role from scratch* —
  [recipes/write-a-custom-role.md](recipes/write-a-custom-role.md).
- *Diagnose an error* —
  [TROUBLESHOOTING.md](TROUBLESHOOTING.md), or run `dsl doctor`.

If a question is not answered here, please open an issue on
[GitHub](https://github.com/kmchandy/DisSysLab/issues). Gaps in
the documentation are easier to fix when they are reported.

---

For framework internals — design and implementation notes for each
core module — see [internals/](internals/). Those documents are for
developers reading the source, not for users building offices.

Notes used during the day-to-day development of the framework, rather
than for running offices, live in the `dev/` folder at the repo
root. Those notes change frequently and are not part of the user
guide.
