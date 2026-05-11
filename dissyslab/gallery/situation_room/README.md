# Situation Room

> A continuously-running office that turns three world-news feeds
> into a morning intelligence digest. Free, local, private.

## What this office does

Every morning (or as often as you run it), Situation Room pulls
articles from BBC World, NPR, and Al Jazeera. It deduplicates them,
classifies severity, extracts named entities, tags topic and
location, and writes a short briefing for each article. A reviewer
agent decides which briefings are worth publishing. The published
briefings are rendered in your terminal as a clean intelligence
digest — what you'd want to read over coffee at 8 a.m.

```
bbc_world, npr_news, al_jazeera  →  Sasha (dedup by URL)
                                        ↓
                ┌──── Eve (entities) ────┐
                │                        │
                ├──── Sam (severity) ────┤
   Sasha ──────┤                        ├─→ Sync (merge) → Riley (write) → Jordan (review)
                ├──── Tom (topic)    ────┤                                       ↓
                │                        │                       ┌─ publish → intelligence_display
                └──── Greta (location) ──┘                       └─ revise  → discard
```

Nine plain-English agents wired into a pipeline. No subscriptions.
Your data never leaves your laptop.

## Set it up in 10 minutes

Three steps. Each takes about three minutes.

**1. Install Ollama and pull a model.**

[Download Ollama](https://ollama.com/download) for your operating
system, then in a terminal:

```bash
ollama pull qwen3:30b
```

This downloads a 19 GB open-weight model (Qwen3-30B-A3B) to your
laptop. One-time download. You'll need ~32 GB of RAM and a recent
Mac or PC.

**2. Install DisSysLab.**

```bash
pip install dissyslab
export DSL_BACKEND=ollama
```

**3. Run the office.**

```bash
dsl run dissyslab/gallery/situation_room/
```

The first run will take ~15–25 minutes — the model thinks
carefully about each article. Subsequent runs reuse the model in
memory and are faster. Output streams to your terminal as
briefings are written.

That's it. No API key, no recurring cost, no service to depend on.

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
Sinks: markdown_digest(path="~/morning_digest.md"), discard
```

And update the connection at the bottom:

```
Jordan's publish is markdown_digest.
```

Now each run writes one markdown file you can open over coffee.

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
  faithful paraphrases, no hallucinated entities (validated on a
  21-article corpus — see `dev/experiments/`).
- **Speed**: ~30 seconds per article on a typical Mac, because
  Qwen3 thinks carefully before producing each output. Pat is
  preparing for an 8 a.m. meeting, not a stock trade — slow is
  fine.
- **Cost**: $0/month recurring. One-time hardware cost is whatever
  Mac (M-series, 32 GB+ RAM recommended) you already own or buy.
- **Privacy**: nothing leaves your machine. Your AI usage doesn't
  appear in anyone else's analytics.

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
  office-specific Python role; the four library-shipped roles
  (entity_extractor, severity_classifier, topic_tagger,
  geolocator, writer, evaluator) come from
  `dissyslab/roles/`.
- [`docs/BUILD_APPS.md`](../../../docs/BUILD_APPS.md) — how to
  build your own office.
- [`docs/LANGUAGE_MODELS.md`](../../../docs/LANGUAGE_MODELS.md) —
  how to switch or mix backends.
