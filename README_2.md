# DisSysLab

[![PyPI](https://img.shields.io/pypi/v/dissyslab)](https://pypi.org/project/dissyslab/)
[![Python](https://img.shields.io/pypi/pyversions/dissyslab)](https://pypi.org/project/dissyslab/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **Describe a continuous office of AI agents in plain English.**
> Sense → think → respond. Each agent uses the AI best suited to its
> job.

---

DisSysLab — `dsl` for short — turns a plain-English description of
an office of AI agents into a running system that keeps working in
the background. Five ideas anchor the design.

**Plain-English authoring.** An office is a single file — `office.md`
— that says what sources it watches, who its agents are, what they
do, and how they're wired together. You write English; the framework
compiles it. No Python required for the common case.

**Offices, not chatbots.** A chatbot answers when you ask. An office
is a team of AI agents with named roles, connected by an org chart,
working on something for you. Offices compose: an office can contain
sub-offices, the way a real organisation contains teams.

**Continuous, not ephemeral.** Offices keep running. Some watch a
feed forever and act when something matters. Others batch through a
daily load (news, email, calendar) and stop. Either way, the office
is a worker, not a conversation.

**Sense → think → respond.** Every office takes the same shape: it
*senses* the world (RSS, email, webhooks, files, sockets), *thinks*
in the form of one or more AI-driven agents that classify, extract,
summarise, decide — and, when the problem calls for it, loops back
to sense more before deciding — and then *responds* by writing
somewhere (a markdown file, a Slack channel, a database, a
downstream office). The shape is general enough to include feedback
cycles, not just one-way pipelines.

**The right AI for each agent.** Each agent in your office picks its
engine independently. Use free local Qwen for the cheap extractors,
a hosted OpenRouter model for the writer, Claude for the editor — or
any combination. The same office.md runs against any of them. New
engines (a killer SLM, your own fine-tune, a research model) plug in
as a Backend Protocol implementation, ~30 lines.

---

## Try it: the headline office

[`situation_room`](dissyslab/gallery/apps/situation_room/) is a
working office. Three news feeds in. One markdown digest out:
articles deduplicated, severity-classified, entity-extracted,
topic-tagged, geolocated, written up as 2–4 sentence briefings, and
reviewed by an editor agent.

**One-line install** (macOS or Linux, requires Python 3.10+):

```bash
curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
```

What that does: installs [Ollama](https://ollama.com), pulls the
Qwen3 model (~19 GB one-time download), installs DisSysLab into a
venv, and adds `dsl` to your shell's PATH. Twenty to forty minutes
wall time, mostly waiting for the model to download.

**Then: open a new terminal** (or run `source ~/.zshrc` on macOS /
`source ~/.bashrc` on Linux) so the new PATH takes effect.

**Now run your first office:**

```bash
dsl run situation_room
```

That runs the version packaged inside DisSysLab. To get your own
copy you can edit:

```bash
dsl init situation_room my_situation
cd my_situation
dsl run .
```

`dsl list` shows every office that ships with DisSysLab.

You should see a digest like
[this sample](dev/experiments/situation_room_sample_day_1.md):

```markdown
## [CRITICAL] Lebanon reports 39 killed in Israeli strikes

*politics · Lebanon · middle_east*

Lebanon reports that Israeli strikes killed 39 people. Fighting
continues between Israel and Hezbollah despite a ceasefire deal
announced last month.

[bbc_world](https://www.bbc.com/news/...)
```

Twenty or so of these every morning.

> **A note on speed.** `situation_room` makes ~18 LLM calls (four
> parallel extractors per article, plus writer and evaluator). The
> curl one-liner installs the *free local* path — Qwen on Ollama —
> which is the slow path: on a 32 GB Mac it's 15–30 minutes; on
> lighter hardware it can be unusable. **The fast path is OpenRouter:
> ~5 minutes setup and 2–4 cents per run, regardless of your laptop.**
> Same office.md, same model family (Qwen3.5-A3B), just running on
> someone else's GPU. Set `DSL_BACKEND=openrouter` and an API key.
> See [docs/LANGUAGE_MODELS.md](docs/LANGUAGE_MODELS.md).
> For a quick first taste on any machine without picking an engine,
> try [`periodic_brief`](dissyslab/gallery/apps/periodic_brief/):
> news + weather → `brief.md` in ~30 seconds, no LLM in the default
> config.

---

## Make it yours

`situation_room` is described in plain English in
[`office.md`](dissyslab/gallery/apps/situation_room/office.md).
Open it. Read it. You can change it. Most of what people want comes
from changing one or more of just four things:

**1. Sources** — swap a news feed for Gmail or a webhook; add or
remove a source entirely.
**2. Parallel thinkers** — add, remove, or replace the agents that
extract entities, severity, topic, location. Each one annotates
the message with one more fact.
**3. Writer** — change the prompt to produce a different style of
briefing: executive summary, technical alert, blog draft, customer
email.
**4. Sinks** — where the result goes: terminal, markdown file,
Slack channel, Notion page, downstream office.

The rest of the office (the deduplicator, the synchronizer, the
evaluator, the wiring) usually stays the same. Once you know which
of the four slots you want to touch, the change is one or two lines
in office.md.

A staircase of effort:

**Tweak — 5 minutes, one parameter.** Bump article counts, swap a
feed, set a polling interval.

```
Sources: techcrunch(max_articles=10, poll_interval=600)
```

**Modify — 30 minutes, swap a component.** Replace the terminal
display with a markdown file, add a topic filter agent, route one
role to a stronger paid model.

```
Sinks: markdown_digest(path="~/digest.md")
```

**Build — a few hours, write new agents.** Describe a new role in
plain English for your industry, your competitor, your inbox. See
[`docs/BUILD_APPS.md`](docs/BUILD_APPS.md).

A worked example of the third tier — overriding *one* role to use
Claude while everything else stays on a cheap open model — is at
[`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/).
One file's difference.

---

## What's an office?

An office is a team of AI agents with **roles**, connected by an
**org chart**. You write each role in plain English — the same way
you'd describe a job to a new hire — and you write the org chart in
plain English too. The framework compiles your description into a
running concurrent system.

Here's `situation_room`'s wiring (excerpted from
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

Three RSS feeds *sense* the world. A deduplicator drops articles
already seen. Each unique article forks to four agents that each
add one annotation — that's the *thinking* layer. The synchronizer
merges the four annotated streams back together. The writer
composes a briefing. The evaluator decides whether to publish or
set aside — the *response*. Nine agents, one file. Add a feedback
edge from the evaluator back to the writer and you have a revise
loop; the same plain-English grammar covers both shapes.

---

## Apps and examples

- **[`gallery/apps/`](dissyslab/gallery/apps/)** — ready-to-run
  offices.
  - [`situation_room`](dissyslab/gallery/apps/situation_room/) —
    the headline office: three news feeds → intelligence digest.
  - [`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/)
    — same office, Claude as the writer for top quality,
    open-weight Qwen everywhere else.
  - [`periodic_brief`](dissyslab/gallery/apps/periodic_brief/) —
    multi-source morning brief (news + weather + optional email and
    calendar) into one markdown file.

- **[`gallery/examples/`](dissyslab/gallery/examples/)** — smaller
  tech demos showing patterns (sub-offices, custom roles, custom
  sinks). Useful when you start writing your own offices.

`dsl list` from the terminal groups every office by section.

---

## Pick your engine

Every agent in an office can run on a different LLM. Pick from the
built-in backends or plug in your own. The three real first-time
choices, with honest setup times and ongoing costs:

- **OpenRouter** — hosted, pay-per-token, runs on someone else's
  GPU. *Setup: ~5 minutes* (sign up, $5 minimum credit, paste an
  API key, set two env vars). *Cost: ~2–4 cents per
  `situation_room` run.* Works on any laptop because nothing runs
  locally.
- **Claude (Anthropic)** — hosted, top quality. *Setup: ~5 minutes
  from a clean machine, ~1 minute if you already have a Claude
  account.* *Cost: pennies per run when used for a single role;
  a few dollars a month if every agent uses Claude.* Same any-laptop
  story as OpenRouter.
- **Ollama** — free, local, private. *Setup: 20–40 minutes mostly
  spent downloading the ~19 GB Qwen3 model.* *Cost: $0 ongoing
  after the one-time download.* Works well on a 32 GB Mac (or
  comparable PC); lighter offices like `periodic_brief` work on
  much less. Default in the curl one-liner.
- **OpenAI, Gemini, your own model** — see
  [`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md) for the
  Backend Protocol (one method, ~30 lines to implement).

Switch all agents at once:

```bash
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
```

Switch only one agent inside one office by overriding its role
file — [`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/)
shows this in one file's difference.

> **A note on cost.** Setting `DSL_BACKEND=anthropic` (Claude) on
> a fan-out office like `situation_room` means ~18 Claude calls per
> run — roughly 50 cents to two dollars depending on the model and
> the article. That can add up quickly if you run the office on a
> cron. For everyday operation, the cheapest reasonable path is
> **Qwen on OpenRouter for every role** (a few cents per run), or
> **Qwen for the extractors and Claude only for the writer**
> (the `situation_room_pro` pattern, pennies per run). See
> [`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md) for the
> per-role override recipe.

---

## Documentation

For people who run offices:

- **[`situation_room/README.md`](dissyslab/gallery/apps/situation_room/README.md)**
  — what the office does, what's in its office.md line by line, and
  the three-tier staircase for making it yours.
- **[Sample digest](dev/experiments/situation_room_sample_day_1.md)**
  — what a real morning's output looks like.

For people who build offices:

- **[`docs/BUILD_APPS.md`](docs/BUILD_APPS.md)** — design and wire
  your own office, from idea to running system.
- **[`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md)** —
  switching, comparing, and mixing backends.
- **[`docs/SOURCES_AND_SINKS.md`](docs/SOURCES_AND_SINKS.md)** —
  every source and sink component the framework ships with.
- **[`docs/recipes/`](docs/recipes/)** — short copy-pasteable
  patterns for common tasks.
- **[`docs/MAKE_OFFICE.md`](docs/MAKE_OFFICE.md)** — the
  programmatic path: construct an office from Python.

For people who extend the framework:

- **[`dev/PROMPTING_FOR_SLMS.md`](dev/PROMPTING_FOR_SLMS.md)** — the
  role-decomposition pattern that makes small models reliable.

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
dsl run situation_room
```

Same result. Read each step before running it.

---

## Also: a teaching framework

DisSysLab is used in an introductory undergraduate distributed
systems class. The same office.md vocabulary — sources, agents,
roles, connections — teaches dataflow, concurrency, parallel
composition, and feedback loops in plain English before students
touch Python. See [`docs/MAKE_OFFICE.md`](docs/MAKE_OFFICE.md) for
the programmatic path used in coursework.

---

## Requirements

- macOS or Linux. Windows works for the core framework, but the
  shell installer assumes a Unix-like environment.
- Python 3.10 or newer.
- For running `situation_room` locally on Ollama: a Mac with 32 GB
  RAM (or comparable PC) and ~20 GB free disk. Smaller machines
  can still run the lighter offices or point `DSL_BACKEND` at
  OpenRouter or another hosted backend.

---

## License

MIT — see [LICENSE](LICENSE).

---

**DisSysLab is an open framework for describing continuous offices
of AI agents in plain English. The unit of design is
sense → think → respond. The mission is to give Pat — small-business
owner, journalist, analyst, NGO staff, anyone doing continuous
information work — a system that pays its rent in attention rather
than tokens.**
