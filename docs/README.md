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

A reader new to DisSysLab will find the path of least friction is:

1. Run [`periodic_brief`](../dissyslab/gallery/apps/periodic_brief/)
   and a second office from the
   [gallery](../dissyslab/gallery/README.md). Two examples are
   enough to recognise the structure of an office.
2. Read **[BUILD_APPS.md](BUILD_APPS.md)**, which works through the
   full grammar of `office.md` and a substantial example role.
3. Browse **[SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md)** for
   sources and sinks the framework ships with. Most new offices can
   be assembled from existing components.
4. Edit a copy of a gallery office (`dsl init <name> my_office`)
   and modify it until it does what you want. Many users never need
   to write an office from scratch.

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
| [MAKE_OFFICE.md](MAKE_OFFICE.md) | The Python API for generating offices programmatically rather than writing `office.md` by hand. | When a tool or script needs to produce offices. Most users do not need this. |
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
- *Generate offices programmatically* —
  [MAKE_OFFICE.md](MAKE_OFFICE.md).
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

Notes used during the development of the framework itself, rather
than for running offices, live in the `dev/` folder at the repo
root. Those notes change frequently and are not part of the user
guide.
