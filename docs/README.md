# DisSysLab documentation

This is the index for everything in `docs/`. If you're new, the
top-level [README](../README.md) is the right starting point — it
walks you from `pip install` to a running office in about ten
minutes. Come back here when you have a specific question.

(Internal design notes for contributors live in `dev/` and are not
indexed here. They change frequently and aren't aimed at users
running offices.)

## Getting started

- **[Top-level README](../README.md)** — install, set your API key,
  run your first office.
- **[GETTING_STARTED.md](../GETTING_STARTED.md)** — longer
  walkthrough, end-to-end, with explanations of every step.
- **[5-minute micro-course](https://kmchandy.github.io/DisSysLab/office_microcourse.html)** —
  watch what an office looks like before you install.
- **Browse offices** — run `dsl list` from the terminal, or open the
  [gallery README](../dissyslab/gallery/README.md).

## Recipes — copy-pasteable patterns

Each recipe is a short page that solves one concrete task by editing
two plain-English files (`office.md` and a role under `roles/`).

- **[Filter for a topic](recipes/filter-for-a-topic.md)** — keep only
  the items you care about; discard the rest.
- **[Monitor your inbox](recipes/monitor-your-inbox.md)** — turn
  Gmail messages into briefings, with App Password setup.
- **[Receive webhooks](recipes/receive-webhooks.md)** — listen on a
  local port for posts from GitHub, Stripe, Zapier, or your own
  scripts.
- **[Send messages outside](recipes/send-messages-outside.md)** —
  forward briefings to email, Slack, a webhook, or a JSONL file.
- **[Add an RSS source](recipes/add-an-rss-source.md)** — pull from
  any RSS or Atom feed (BBC, Hacker News, your favorite blog).
- **[Chain offices](recipes/chain-offices.md)** — let one office's
  output flow into another, building larger systems from smaller
  ones.
- **[Write a custom role](recipes/write-a-custom-role.md)** —
  describe a new job in plain English and assign it to an agent.

The full recipe index, including any recipes added later, is at
[recipes/README.md](recipes/README.md).

## Reference

- **[Sources and sinks](SOURCES_AND_SINKS.md)** — every component the
  framework ships with, with arguments, environment variables, and
  setup instructions. Look here when you want to know what the
  built-in `bbc_world`, `gmail_source`, `webhook_sink`, etc. accept.
- **[Language models](LANGUAGE_MODELS.md)** — switch from Claude
  (the default) to OpenAI, Gemini, Ollama, or another model; mix
  backends inside one office; compare models on the same task.
- **[Build apps](BUILD_APPS.md)** — design and wire your own
  offices: org-chart shapes, prompt-writing tips, when to split
  into sub-offices, and how to extend with custom Python roles.
- **[Troubleshooting](TROUBLESHOOTING.md)** — common errors when
  installing or running DisSysLab, keyed on the actual error
  strings, with the remedy for each.

## Looking for something specific?

- **"How do I use OpenAI / Gemini / Ollama / a local model?"** →
  [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md).
- **"How do I build my own office?"** →
  [BUILD_APPS.md](BUILD_APPS.md).
- **"How do I send results to Slack / email / a file?"** →
  [send-messages-outside.md](recipes/send-messages-outside.md).
- **"How do I read my Gmail?"** →
  [monitor-your-inbox.md](recipes/monitor-your-inbox.md).
- **"How do I add a new RSS feed?"** →
  [add-an-rss-source.md](recipes/add-an-rss-source.md).
- **"What sources and sinks come with the package?"** →
  [SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md).
- **"How do I connect two offices together?"** →
  [chain-offices.md](recipes/chain-offices.md).
- **"How do I write a role from scratch?"** →
  [write-a-custom-role.md](recipes/write-a-custom-role.md).
- **"I hit an error and don't know what it means."** →
  [TROUBLESHOOTING.md](TROUBLESHOOTING.md), or run `dsl doctor`.

If your question isn't covered here, open an issue on
[GitHub](https://github.com/kmchandy/DisSysLab/issues) — that's the
fastest way to get an answer and to flag a gap in the docs.
