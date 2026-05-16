# DisSysLab

[![PyPI](https://img.shields.io/pypi/v/dissyslab)](https://pypi.org/project/dissyslab/)
[![Python](https://img.shields.io/pypi/pyversions/dissyslab)](https://pypi.org/project/dissyslab/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**Use plain English to build offices of networks of agents that work for you continuously.**
A chatbot answers when you ask; but your office of agents works for you nonstop 24 x 7. 
Build your personal office staffed by multiple agents that monitor 
and analyze information sources and send results to your apps and devices.

**Mix and match agents that best fit your tasks, budget and privacy needs.**
Agents in your office can be free AI models that you can run on
a laptop;
 powerful AI services such as those provided by Anthropic and
OpenAI; 
 AI models for specialized tasks such as coding; and
Python functions. 

**Construct agent networks of arbitrary complexity ideal for your application.**
Different applications need different types of agent networks.
Some networks are pipelines; some are feed-forward networks with parallel
agents; some have conditional branches; and some have loops.
Build an office with the agent network ideal for your application.
Start by modifying examples of offices in the [`gallery`](dissyslab/gallery/).

---

## Try it: a brief in ten seconds

The fastest demo of the framework needs no API key and no model
download. [`periodic_brief`](dissyslab/gallery/apps/periodic_brief/)
pulls news, weather, and a few stock tickers and renders them into a
single, styled HTML page. Zero LLM calls in the default config — it's
pure orchestration of public APIs, the framework doing what
frameworks do.

**One-line install** (macOS or Linux, requires Python 3.10+):

```bash
curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
```

The installer asks one question: which AI engine do you want?

- **Ollama** — free, local, private. Downloads a ~19 GB model
  (Qwen3) one time, takes 20–40 minutes. After that, $0 forever
  but slow: 15–60 min per office run on a typical Mac.
- **OpenRouter** — hosted Qwen-2.5-7B. Paste an API key from
  <https://openrouter.ai/keys>. A few cents covers a week of runs.
  Office runs finish in 1–5 minutes.
- **Claude** — Anthropic's hosted model. Paste an Anthropic key.
  Highest-quality output, ~25–50¢ per office run.

Pick the one that fits. You can switch later by editing one line in
your shell rc file.

**Then: open a new terminal** (or run `source ~/.zshrc` on macOS /
`source ~/.bashrc` on Linux) so the new PATH takes effect.

**Now run your first office:**

```bash
dsl run periodic_brief
open brief.html
```

About ten seconds. You'll see a single HTML page with three news
headlines from BBC, three from NPR, current weather for Pasadena,
and three stock tickers — all wired together by the office's
plain-English description of itself. No API keys, no LLM calls, no
waiting.

You can copy the `periodic_brief` to a local folder, `my_brief` on your computer and
then execute the office from your local folder as follows:

```bash
dsl init periodic_brief my_brief
cd my_brief
dsl run .
```

`dsl list` shows every office that ships with DisSysLab.

## Then: the real demo — situation_room

Once `periodic_brief` has shown you the bones of the framework, the
office that shows what it's *for* is
[`situation_room`](dissyslab/gallery/apps/situation_room/). Three
news feeds in. One intelligence digest out: articles deduplicated,
severity-classified, entity-extracted, topic-tagged, geolocated,
and written up as 2–4 sentence briefings. Eight plain-English
agents in one file — and you decide which briefings matter, not
an LLM editor.

```bash
dsl run situation_room
```

Speed and cost depend on the engine you picked at install time:

| Engine | Wall time per run | Cost per run |
|---|---|---|
| Ollama (local Qwen) | 15–30 min on a 32 GB Mac | $0 |
| OpenRouter (Qwen-2.5-7B) | 1–5 min, any laptop | pennies |
| Claude | 1–3 min, any laptop | tens of cents |

> *All cost and speed figures above are rough estimates and are
> likely to change. Hosted-model providers update their prices
> regularly — check the provider's pricing page before relying on
> any specific number here. The framework is honest about which
> backend you're using; the actual bill is between you and your
> provider.*

**About cost safety.** Every office in the gallery stops after a
few polling cycles by default — long enough to see a real result,
short enough that you won't accidentally rack up a bill. The
`max_articles=N` and `max_readings=N` parameters in each office's
`office.md` are the safety brakes. Remove them only when you mean
for an office to run continuously (e.g. behind a cron).

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
wiring) usually stays the same. Once you know which of the four
slots you want to touch, the change is one or two lines in
office.md.

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
Sinks: intelligence_display, jsonl_recorder_briefing(...)

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer.
Riley is a writer.

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
Riley's out is intelligence_display, jsonl_recorder_briefing.
```

The office monitors 3 RSS feeds. A deduplicator drops duplicates -- articles
already seen. Each article forks to four agents. Each
adds one annotation to the article — that's the parallel "thinking" layer. The synchronizer
merges the four annotated streams. The writer
composes a briefing — the *response* — and Riley's output fans
out to both sinks at once: live terminal display and a JSONL
archive. Eight agents, one file. Want an LLM-powered editor to
decide which briefings to publish? Drop an `evaluator` between
Riley and the sinks — the role library has one ready. Same
plain-English grammar.

---

## Apps and examples

- **[`gallery/apps/`](dissyslab/gallery/apps/)** — ready-to-run
  offices, organised by whether they need an API key.
  - [`periodic_brief`](dissyslab/gallery/apps/periodic_brief/) —
    no-key, no-LLM HTML brief: news + weather + tickers. The
    ten-second demo.
  - [`situation_room`](dissyslab/gallery/apps/situation_room/) —
    the headline office: three news feeds → intelligence digest.
    Nine plain-English agents in sense → think → respond.
  - [`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/)
    — same office, Claude as the writer for top quality,
    open-weight Qwen everywhere else.
  - See [`gallery/README.md`](dissyslab/gallery/README.md) for the
    full menu (inbox triage, ticket router, competitor watch, lead
    qualifier, new-grad jobs, etc.).

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
  API key into the installer prompt). *Cost: pennies per
  `situation_room` run* with the default Qwen-2.5-7B. Works on any
  laptop because nothing runs locally.
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
> **Qwen-2.5-7B on OpenRouter for every role** (pennies per run),
> or **Qwen for the extractors and Claude only for the writer**
> (the `situation_room_pro` pattern, still pennies per run with
> sharper prose). See
> [`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md) for the
> per-role override recipe.

---

## Documentation

For people who run offices:

- **[`gallery/README.md`](dissyslab/gallery/README.md)** — the full
  app catalog, split into "runs on any laptop with no keys" and
  "shines on a hosted backend".
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
# 1. Install DisSysLab
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install dissyslab

# 2. Try periodic_brief now — no model, no key, just runs
dsl run periodic_brief
open brief.html
```

That gives you a working office in under a minute. To unlock the
heavier offices (`situation_room`, `inbox_triage`, etc.) pick an
engine and configure it:

```bash
# Option A: local, free, slow. ~19 GB one-time model download.
# Install Ollama from https://ollama.com/download, then:
ollama pull qwen3:30b
export DSL_BACKEND=ollama

# Option B: hosted Qwen-2.5-7B via OpenRouter. Pennies per run.
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct

# Option C: Claude. ~25–50¢ per run, highest quality.
export DSL_BACKEND=claude
export ANTHROPIC_API_KEY=sk-ant-...

# Then run any office in the gallery
dsl run situation_room
```

Same result as the shell installer. Read each step before running it.

---

## Also: a teaching framework

DisSysLab is used in an introductory undergraduate distributed
systems class. The same office.md vocabulary — sources, agents,
roles, connections — teaches dataflow, concurrency, parallel
composition, and termination detection to first year students
using distributed systems examples constructed in plain English. 
See [`docs/MAKE_OFFICE.md`](docs/MAKE_OFFICE.md) for
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
