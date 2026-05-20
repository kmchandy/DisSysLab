# Situation Room

> A continuously-running office that turns three world-news feeds
> into a morning intelligence digest. Pick your engine — free local
> Qwen, hosted OpenRouter, Claude, or your own.

## What this office does

Every morning (or as often as you run it), Situation Room pulls
articles from BBC World, NPR, and Al Jazeera. It deduplicates them,
classifies severity, extracts named entities, tags topic and
location, and writes a short briefing for each article. The
briefings are rendered in your terminal as an intelligence
digest and also archived as JSONL.
The office instantiates the
sense → think → respond pattern — see
[`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for how to modify it.

## Run it

Install DisSysLab and pick an engine following the
[top-level README](../../../../README.md) — one curl one-liner,
one engine choice (Ollama, OpenRouter, or Claude). Then:

```bash
dsl run situation_room
```

Wall time and cost depend on the engine you picked:

| Engine | Wall time per run | Cost per run |
|---|---|---|
| Ollama (local Qwen3) | 15–30 min on a 32 GB Mac | $0 |
| OpenRouter (Qwen-2.5-7B) | 1–5 min, any laptop | pennies |
| Claude | 1–3 min, any laptop | tens of cents |

> *All numbers above are estimates and will drift as providers
> update prices.*

First run is slowest because the engine cold-starts. Re-running
the office reuses the loaded model and goes faster.

## What's in office.md

Open [`office.md`](office.md) alongside this section — every line is
explained below. 

**The header.** Every office starts with one line naming itself:

```
# Office: situation_room
```

That name is what `dsl run` prints when it starts. Nothing else
depends on it.

**Sources — where messages come from.**

```
Sources: bbc_world(max_articles=1), npr_news(max_articles=1), al_jazeera(max_articles=1)
```

A *source* is anything that produces messages: an RSS feed, a
weather station, your Gmail inbox, an MCP server, a webhook
listener. The framework ships a catalogue of named sources you
just refer to by name — `bbc_world`, `npr_news`, `weather`,
`gmail`, `stocks`, `hacker_news`, and more. The
parentheses are arguments: `max_articles=1` means "fetch one
article per run." Change it to 10 and the office processes 10 articles
per run.

**Sinks — where messages end up.**

```
Sinks: intelligence_display, jsonl_recorder_briefing(path="briefings.jsonl")
```

Results are sent to a sink: a terminal printer, a markdown file
writer, a Slack channel, a Gmail outbox. Same registry pattern as
sources. This office uses two sinks — one for live terminal
output, one to record every briefing to disk as JSONL.

**Agents — named characters with roles.**

```
Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer.
Riley is a writer.
```

Each line names an *agent* and assigns it a *role*. ``Sasha is a
deduplicator`` means that the behaviour of agent Sasha is
specified by the `deduplicator` role." Each role is specified by
a job description. Roles and their specifications are found in
the framework's built-in role library (in
`dissyslab/roles/`) and this office's own `roles/` folder.
Extend the library of roles to fit the types of applications
that you build and reuse role specs from your library.

`writer`, `entity_extractor`, `severity_classifier`,
`topic_tagger`, and `geolocator` are in the built role library.
 `synchronizer` is
custom to this office. The framework doesn't know what names are
"right" — `Sasha`, `Eve`, `Riley` are just local labels you use in
the wiring.

**Connections — the wiring.**

```
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.
```

Each line reads as English. The default outport of a source is
called `destination`, so `bbc_world's destination is Sasha` says
"send each article BBC produces to Sasha." On the receiving side,
sinks and most agents have a default inport, so we just write
`Sasha` rather than `Sasha's <port-name>`. Three feeds all feeding
one deduplicator means the framework automatically fans them in.

```
Sasha's out is Eve, Sam, Tom, Greta.
```

One source, four destinations. The framework automatically
fans Sasha's output out to all four extractors. Each extractor
sees every article and adds its own field (entities, severity,
topic, location). This is parallel work — no extra Python, no
threading code.

```
Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.
```

Now the four parallel streams merge back together. `Sync's
entities` is a *named input port* on the Sync agent. The
synchronizer waits until it has one of each (entities, severity,
topic, location) for the same article and emits a single combined
message. Named ports are how an agent tells you "I expect a few
different kinds of input, here's what to call each one."

```
Sync's out is Riley.
Riley's out is intelligence_display, jsonl_recorder_briefing.
```

Standard pipe: synchronizer to writer, then the writer's output
fans out to both sinks at once. Pat sees every briefing in the
terminal *and* gets a JSONL archive on disk to re-read later. No
editorial filter — you're the editor.

**That's the whole framework.** Sources, sinks, agents, roles,
connections. Seven lines of agents + nine lines of connections
described an eight-agent pipeline with fan-out, fan-in, and
synchronization — no Python required. The same vocabulary
describes every office in the gallery.

> *Want an LLM-powered editor in the loop?* The role library ships
> an `evaluator` that decides publish-vs-revise per briefing — see
> the Tier-2 "filter with an evaluator" example below for the
> wiring. It adds one LLM call per article; the default office
> skips it so Pat sees raw output.

When you're ready to write your own, [`docs/BUILD_APPS.md`](../../../docs/BUILD_APPS.md)
walks through it from scratch.

## Make it yours

You don't need to use Situation Room as it ships. The office is
described in plain English in `office.md`, and you can change as
much or as little as you want. There are three levels of change,
in order of how much you'd touch.

### Tier 1 — Tweak  *(5 minutes, one parameter)*

Change one number or one name in `office.md` and re-run. No new
files; no new concepts.

**Examples.**

*Pull more articles per feed:*

```
Sources: bbc_world(max_articles=10), npr_news(max_articles=10), al_jazeera(max_articles=10)
```

*Use different feeds:*

```
Sources: techcrunch(max_articles=5), mit_tech_review(max_articles=5), venturebeat_ai(max_articles=5)
```

The framework ships with named RSS sources for `bbc_world`,
`bbc_tech`, `npr_news`, `al_jazeera`, `hacker_news`, `techcrunch`,
`mit_tech_review`, `venturebeat_ai`, `nasa_news`, `python_jobs`,
and more. Pick the ones that match what you care about.

*Poll continuously instead of one-shot:*

```
Sources: bbc_world(max_articles=10, poll_interval=600)
```

Adding `poll_interval=600` makes the source re-check the feed
every 10 minutes. `dsl run` then runs forever, producing new
briefings as new articles appear. (Ctrl-C to stop.)

After any tweak, re-run:

```bash
dsl run dissyslab/gallery/situation_room/
```

If the change works, you're done. If something errors, the error
usually tells you what's wrong in plain English.

### Tier 2 — Modify  *(30 minutes, swap an existing component)*

Replace one source, role, or sink with another from the
framework's library. Still no new code; one or two edits to
`office.md`.

**Examples.**

*Write a daily markdown digest instead of streaming to terminal:*

Change the `Sinks:` line to use `markdown_digest`:

```
Sinks: markdown_digest(path="~/morning_digest.md")
```

And update the connection at the bottom:

```
Riley's out is markdown_digest.
```

Now each run writes one markdown file you can open over coffee.

*Add an LLM-powered editor that filters briefings before they hit the digest:*

```
Agents:
...
Riley is a writer.
Jordan is an evaluator.   # new agent

Sinks: markdown_digest(path="~/morning_digest.md"), jsonl_recorder_discard(path="rejected.jsonl")

Connections:
...
Riley's out is Jordan.
Jordan's publish is markdown_digest.
Jordan's revise is jsonl_recorder_discard.
```

Jordan is an `evaluator` from the role library — it has two
outports, `publish` and `revise`, and its prompt decides which
each briefing earns. Routing decisions live in the role's prompt,
not in glue code. The rejected briefings are still recorded so
you can audit what got dropped.

*Add a topic filter between Sasha and the extractors:*

```
Agents:
Sasha is a deduplicator(by="url").
Felix is a topic_filter.   # new agent
Eve is an entity_extractor.
...

Connections:
Sasha's out is Felix.
Felix's keep is Eve, Sam, Tom, Greta.
Felix's drop is discard.
```

You'd also need `dissyslab/roles/topic_filter.md` — the framework
ships one as an example, or write your own (see Tier 3).

*Use Claude for the hardest role, keep everything else on Qwen:*

In `roles/writer.py` (or in this office's `roles/writer.py`
override), specify the backend:

```python
from dissyslab.office_v2 import nl_role
role = nl_role(prompt_text, AI="claude")
```

Now Riley calls Claude while the four extractors stay on free
local Qwen. Cost is pennies per day; quality on the most
visible role is a step up. The gallery's `situation_room_pro`
office demonstrates this pattern.

### Tier 3 — Build  *(a few hours, write a new role or office)*

Write a custom role prompt for your domain, or compose a
completely different office. This is where you become a Builder.

**Example: a competitor mention filter.**

You watch a couple of feeds for any mention of a specific
competitor. Create `dissyslab/gallery/situation_room/roles/competitor_filter.md`:

```
# Role: competitor_filter

You read one news article at a time and decide whether it
mentions a specific competitor.

Your job. Add one new field, "mentions_competitor", whose
value is the boolean true or false.

Rules:
- The competitor name is given to you in the article's "watch_for"
  field. If "watch_for" doesn't appear anywhere in the title or
  text (case-insensitive), set mentions_competitor to false.
- Otherwise set mentions_competitor to true.

Routing:
- If mentions_competitor is true, send to relevant.
- Otherwise, send to discard.

Output. Return a single JSON object that includes every field
of the input plus the new "mentions_competitor" field, plus a
"send_to" field whose value is "relevant" or "discard". Do not
include explanations, markdown code fences, or any text outside
the JSON object.
```

Then in `office.md`:

```
Agents:
Felix is a competitor_filter.

Connections:
Sasha's out is Felix.
Felix's relevant is Eve, Sam, Tom, Greta.
Felix's discard is discard.
```

After re-running, only articles mentioning the competitor flow
through the rest of the pipeline. The full guide for writing
new roles is at
[`docs/BUILD_APPS.md`](../../../docs/BUILD_APPS.md) and the
SLM-friendly prompt patterns at
[`dev/PROMPTING_FOR_SLMS.md`](../../../dev/PROMPTING_FOR_SLMS.md).

**Example: a brand-new office.**

Once you can read `office.md` and write a role, you can compose
a different office entirely — an inbox-triage office, a
calendar-prep office, a competitor-watch office. The same
patterns apply: pick sources, name agents, wire connections.
[`docs/BUILD_APPS.md`](../../../docs/BUILD_APPS.md) walks
through this from scratch.

**Where to get help:**

- A weird error → start at `office.md` and see if the syntax
  matches the gallery examples.
- A role behaves oddly →
  [`dev/PROMPTING_FOR_SLMS.md`](../../../dev/PROMPTING_FOR_SLMS.md)
  explains the patterns that make prompts work on local SLMs.
- A bigger change → open an issue at
  [github.com/kmchandy/DisSysLab](https://github.com/kmchandy/DisSysLab).

## What you should expect

- **Quality**: classifications are reliable, summaries are
  faithful paraphrases, entities ground in the article text.
- **Speed**: ~30 seconds per article on a typical Mac with Ollama.
  Plenty for a morning digest; not enough for real-time alerts.
- **Cost**: $0/month recurring on Ollama. Pennies per run on
  OpenRouter. Tens of cents per run on Claude.
- **Privacy on Ollama**: nothing leaves your machine. On hosted
  backends, your prompts go to the provider.

## When this office isn't the right fit

- **Real-time alerts.** Situation Room is a morning-digest office,
  not a real-time-alerts office. If you need millisecond response
  (e.g., trading, security), use a different tool.
- **English-only news.** The role library is calibrated for
  English. Non-English articles work but quality degrades.
- **Tiny laptops.** Qwen3:30b needs ~12-14 GB of RAM at Q4
  quantization. Mac with 16 GB RAM works; older laptops with
  8 GB RAM don't.

## See also

- [`office.md`](office.md) — the wiring.
- [`roles/synchronizer.py`](roles/synchronizer.py) — the only
  office-specific Python role; the five library-shipped roles
  (entity_extractor, severity_classifier, topic_tagger,
  geolocator, writer) come from `dissyslab/roles/`.
- [`docs/BUILD_APPS.md`](../../../docs/BUILD_APPS.md) — how to
  build your own office.
- [`docs/LANGUAGE_MODELS.md`](../../../docs/LANGUAGE_MODELS.md) —
  how to switch or mix backends.
