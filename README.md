# DisSysLab

[![PyPI](https://img.shields.io/pypi/v/dissyslab)](https://pypi.org/project/dissyslab/)
[![Python](https://img.shields.io/pypi/pyversions/dissyslab)](https://pypi.org/project/dissyslab/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **Free AI assistants that do your information work** — runs on
> your laptop. No subscription. Your data never leaves your
> computer.

A morning intelligence digest. An inbox classifier. A competitor
watcher. DisSysLab is a framework for building **offices of AI
agents** that work for you continuously — described in plain
English, running on free open-source language models.

---

## Try it: your morning intelligence digest in ten minutes

[`situation_room`](dissyslab/gallery/apps/situation_room/) is a
working office. Three news feeds in. One markdown digest out:
articles deduplicated, severity-classified, entity-extracted,
topic-tagged, geolocated, written up as 2-4 sentence briefings,
and reviewed by an editor agent. Free. Local. Private.

**One-line install** (macOS or Linux, requires Python 3.10+):

```bash
curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
```

What that does: installs [Ollama](https://ollama.com), pulls the
Qwen3 model (~19 GB one-time download), installs DisSysLab into a
venv, and adds `dsl` to your shell's PATH. Twenty to forty minutes
wall time, mostly waiting for the model to download.

**Then: open a new terminal** (or run `source ~/.zshrc` on macOS /
`source ~/.bashrc` on Linux) so the new `PATH` takes effect. This
step is what makes the `dsl` command available — the installer
adds it to your shell config, but the change only applies to
shells started afterwards.

**Now run your first office:**

```bash
dsl run dissyslab/gallery/apps/situation_room/
```

After ~10 minutes of pipeline execution you have a digest like
[this sample](dev/experiments/situation_room_sample_day_1.md):

```markdown
## [CRITICAL] Lebanon reports 39 killed in Israeli strikes

*politics · Lebanon · middle_east*

Lebanon reports that Israeli strikes killed 39 people. Fighting
continues between Israel and Hezbollah despite a ceasefire deal
announced last month.

[bbc_world](https://www.bbc.com/news/...)
```

Twenty or so of these every morning. No subscription, no API key,
no recurring cost.

---

## Make it yours

`situation_room` is described in plain English in
[`office.md`](dissyslab/gallery/apps/situation_room/office.md).
Open it. Read it. You can change it.

There's a staircase from Consumer → Builder. You're not on a step
unless you want to be.

**Tweak — 5 minutes, one parameter.** Bump article counts, swap
a feed, or set a polling interval:

```
Sources: techcrunch(max_articles=10, poll_interval=600)
```

**Modify — 30 minutes, swap a component.** Replace the terminal
display with a markdown file, add a topic filter agent, route one
role to a stronger paid model:

```
Sinks: markdown_digest(path="~/digest.md")
```

**Build — a few hours, write new agents.** Describe a new role
in plain English to filter for your industry, watch a competitor,
or summarise whatever stream matters to you. See
[`docs/BUILD_APPS.md`](docs/BUILD_APPS.md).

A worked example of the third tier — overriding *one* role to use
Claude while everything else stays free on Ollama — is at
[`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/).
One file's difference. Roughly $1/month vs $14/month vs $0/month,
depending on how much quality you want where.

---

## What's an office?

An office is a team of AI agents with **roles**, connected by an
**org chart**. You write each role in plain English — the same way
you'd describe a job to a new hire — and you write the org chart
in plain English too. The framework compiles your description into
a running concurrent pipeline.

Here's `situation_room`'s pipeline (excerpted from
[`office.md`](dissyslab/gallery/apps/situation_room/office.md)):

```
Sources: bbc_world(max_articles=5), npr_news(max_articles=5),
         al_jazeera(max_articles=5)
Sinks: intelligence_display, jsonl_recorder_briefing(...),
       jsonl_recorder_discard(...)

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer.
Riley is a writer.
Jordan is an evaluator.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.

Sasha's out is Eve, Sam, Tom, Greta.

Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.

Sync's out is Riley.
Riley's out is Jordan.
Jordan's publish is intelligence_display, jsonl_recorder_briefing.
Jordan's revise is jsonl_recorder_discard.
```

Three RSS feeds fan into a deduplicator. Each unique article forks
to four parallel agents that each add one piece of metadata. The
synchronizer merges those branches. The writer produces a briefing.
The evaluator routes it to display or rejection. Nine agents, one
file.

---

## Apps and examples

- **[`gallery/apps/`](dissyslab/gallery/apps/)** — Pat-facing
  ready-to-run offices.
  - [`situation_room`](dissyslab/gallery/apps/situation_room/) —
    morning intelligence digest from three news feeds (the office
    on this page).
  - [`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/)
    — same office with Claude as the writer for higher-quality
    briefings, free local Qwen for everything else.

- **[`gallery/examples/`](dissyslab/gallery/examples/)** — Builder
  tech demos showing patterns (sub-offices, custom roles, custom
  sinks). Useful when you start writing your own offices.

`dsl list` from the terminal shows every office that ships with
DisSysLab.

---

## Beyond the free path

The default is free local AI via Ollama. The framework also
supports paid hosted backends out of the box:

- **Claude** via Anthropic — set `ANTHROPIC_API_KEY` and
  `DSL_BACKEND=anthropic`.
- **Open-weight models via OpenRouter** — set
  `OPENROUTER_API_KEY` and `DSL_BACKEND=openrouter`. Useful for
  testing larger SLMs without local hardware.
- **OpenAI, Gemini, or your own model** — see
  [`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md) for the
  Backend Protocol (one method, ~30 lines to implement).

You can also **mix backends inside one office**:
`situation_room_pro` runs the writer on Claude and the four
extractors on Qwen.

---

## Documentation

For Consumers:

- **[`situation_room/README.md`](dissyslab/gallery/apps/situation_room/README.md)**
  — what the office does and how to make it yours (the three-tier
  staircase).
- **[Sample digest](dev/experiments/situation_room_sample_day_1.md)**
  — what Pat sees on a typical morning.

For Builders:

- **[`docs/BUILD_APPS.md`](docs/BUILD_APPS.md)** — design and wire
  your own office, from idea to running pipeline.
- **[`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md)** —
  switching, comparing, and mixing backends.
- **[`docs/SOURCES_AND_SINKS.md`](docs/SOURCES_AND_SINKS.md)** —
  every component the framework ships with.
- **[`docs/recipes/`](docs/recipes/)** — short copy-pasteable
  patterns for common tasks.
- **[`docs/MAKE_OFFICE.md`](docs/MAKE_OFFICE.md)** — the
  programmatic path: construct an office from Python.

For framework developers:

- **[`dev/PROMPTING_FOR_SLMS.md`](dev/PROMPTING_FOR_SLMS.md)** —
  the role-decomposition pattern that makes SLMs reliable.
- **[`dev/PLAN_free_ai_for_pat.md`](dev/PLAN_free_ai_for_pat.md)**
  and **[`dev/PLAN_shipping_v1.md`](dev/PLAN_shipping_v1.md)** —
  what we're building and why.

---

## Manual install (without the shell installer)

If you'd rather not run a `curl | bash`:

```bash
# 1. Install Ollama from https://ollama.com/download
# 2. Pull the model
ollama pull qwen3:30b

# 3. Install DisSysLab
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install dissyslab

# 4. Configure
export DSL_BACKEND=ollama

# 5. Run
dsl run dissyslab/gallery/apps/situation_room/
```

Same result. Read each step before running it.

---

## Requirements

- macOS or Linux. (Windows works for the core framework but the
  shell installer assumes a Unix-like environment.)
- Python 3.10 or newer.
- Mac with 16 GB+ RAM, or comparable PC. The `qwen3:30b` model uses
  ~12-14 GB at Q4 quantization; comfortable on a 32 GB Mac.
- ~20 GB free disk for the model.
- An Ollama install (the installer handles this) or a paid LLM API
  key if you prefer the paid path.

---

## License

MIT — see [LICENSE](LICENSE).

---

**DisSysLab is an open framework for describing continuous
multi-agent AI systems in plain English. It runs free locally and
mixes with paid hosted models when you want. The mission is to give
Pat — small-business owner, journalist, analyst, NGO staff, anyone
doing continuous information work — a system that pays its rent in
attention rather than tokens.**
