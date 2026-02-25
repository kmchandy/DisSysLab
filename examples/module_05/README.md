# Module 05: Job Postings Monitor

*Monitor job boards. Get alerted when relevant postings appear.*

---

## What You'll Build

A job postings monitor that reads from two job feeds simultaneously,
filters out spam, uses AI to assess how well each posting matches your
target role, and routes results to two destinations:

```
python_jobs ─┐
              ├→ spam_filter → relevance → split → match   → archive + display
ml_jobs     ─┘                                  → no_match → (dropped)
```

This is the first Gallery module — a complete, real application built with
the same four building blocks from Modules 01-04. No new node types.
What's new is the application: a monitor you'd actually want to run.

---

## Files in This Module

| File                      | What it is                                              |
|---------------------------|---------------------------------------------------------|
| `README.md`               | This file                                               |
| `app.py`                  | The demo version — run this first                       |
| `claude_generated_app.py` | Exactly what Claude produced from the Part 4 prompt     |
| `app_live.py`             | Real RSS feeds + real Claude AI (Part 3)                |
| `app_extended.py`         | Extended version with salary extraction added           |
| `test_module_05.py`       | Tests you can run to verify everything works            |

---

## Part 1: Run the App (2 minutes)

From the DisSysLab root directory:

```bash
python3 -m examples.module_05.app
```

You should see job postings filtered and routed:

```
💼 Job Postings Monitor
════════════════════════════════════════════════════════════

  python_jobs ─┐
                ├→ spam_filter → relevance → split
  ml_jobs     ─┘                          → match   → archive + display
                                          → no_match → dropped

  ✅ STRONG: Senior Python Engineer at Stripe — Remote, $180k-$220k
       Matches target role: senior Python or ML engineer.

  🔶 PARTIAL: Data Scientist (Python/SQL) at Airbnb — Remote, $165k
       Partial match: relevant technology but role level unclear.

  ✅ STRONG: ML Engineer (Python/PyTorch) at DeepMind — London or Remote
       Matches target role: senior Python or ML engineer.

════════════════════════════════════════════════════════════
✅ Done! Matches saved to job_matches.jsonl
```

This uses demo job data — the same network structure as `app_live.py` but
with no network calls and no API costs. Move to Part 2 to understand the
design.

---

## Part 2: The Design Process (10 minutes)

Before writing `app.py`, the network was designed by answering four questions.
Use this same process for your own app in Part 4.

### Question 1: What do I want to monitor?

*Two job feeds: python_jobs and ml_jobs.*

Two sources feeding one pipeline → **fanin**.

### Question 2: What processing do I need?

*Filter spam first. Then check whether each posting matches my target role.*

Two Transform nodes in sequence: `spam_filter → relevance`.

### Question 3: Where do I want results to go?

*Matching jobs saved to a file and printed to the terminal. Non-matches dropped.*

Two destinations for matches (archive + display) → **fanout from a Split port**.
Non-matches go to a sink that silently discards them.

### Question 4: Draw the topology

```
  python_jobs ─┐
                ├→ [spam_filter] → [relevance] → [splitter]
  ml_jobs     ─┘                               → out_0 → [archive]
                                               → out_0 → [display]
                                               → out_1 → (discard)
```

Two outputs from `out_0`? That's **fanout from a Split port** — the match
branch fans out to both archive and display. The no-match branch goes to
a sink that drops everything. This combines Split routing with fanout on
one branch.

Once the drawing exists, the code writes itself.

---

## Part 3: Read the Code (10 minutes)

Open `app.py`. Every section maps directly to the design above.

### Imports

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_job_source import DemoJobSource
from components.transformers.prompts import SPAM_DETECTOR, JOB_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder
```

### Components — one per box in the drawing

```python
python_src = DemoJobSource(feed_name="python_jobs")
ml_src     = DemoJobSource(feed_name="ml_jobs")

spam_detector     = demo_ai_agent(SPAM_DETECTOR)
relevance_checker = demo_ai_agent(JOB_DETECTOR)

recorder = JSONLRecorder(path="job_matches.jsonl", mode="w", flush_every=1)
```

### The key new idea: JOB_DETECTOR

`JOB_DETECTOR` is a prompt in `components/transformers/prompts.py` that
describes the target role in plain English:

```python
JOB_DETECTOR = """You are helping a job seeker find relevant postings.

The target role: senior Python engineer or ML engineer, remote or hybrid,
at a well-known tech company working on interesting problems.

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""
```

This is the Prompt → JSON → Python pattern from Module 02. You write a
prompt describing your specific criteria, and your Python function acts on
the result. To monitor for a different role, you change the prompt — the
rest of the app stays the same.

### Transform functions — one per arrow in the drawing

```python
def filter_spam(text):
    result = spam_detector(text)
    return None if result["is_spam"] else text

def check_relevance(text):
    result = relevance_checker(text)
    return {"text": text, "match": result["match"],
            "confidence": result["confidence"], "reason": result["reason"]}

def route_by_match(posting):
    if posting["match"] in ("STRONG", "PARTIAL"):
        return [posting, None]   # → out_0 (archive + display)
    else:
        return [None, posting]   # → out_1 (discard)
```

### Network — the drawing as code

```python
g = network([
    (python_source,  spam_gate),
    (ml_source,      spam_gate),      # fanin
    (spam_gate,      relevance),
    (relevance,      splitter),
    (splitter.out_0, archive),        # fanout from split port
    (splitter.out_0, display),        # fanout from split port
    (splitter.out_1, discard_sink),
])
```

### Connect real Claude AI

`app_live.py` shows the two-line change:

```python
# app.py uses:
from components.transformers.demo_ai_agent import demo_ai_agent
spam_detector     = demo_ai_agent(SPAM_DETECTOR)
relevance_checker = demo_ai_agent(JOB_DETECTOR)

# app_live.py uses:
from components.transformers.ai_agent import ai_agent
spam_detector     = ai_agent(SPAM_DETECTOR)
relevance_checker = ai_agent(JOB_DETECTOR)
```

Everything else is identical.

```bash
export ANTHROPIC_API_KEY='your-key-here'
pip install feedparser
python3 -m examples.module_05.app_live
```

---

## Part 4: Make It Yours (homework)

The entire behavior of this monitor is controlled by one prompt: `JOB_DETECTOR`
in `components/transformers/prompts.py`. To monitor for a different role,
change that prompt. The network stays the same.

### Step 1: Edit JOB_DETECTOR

Open `components/transformers/prompts.py` and find `JOB_DETECTOR`. Change
the target role description to match what you're actually looking for:

```python
JOB_DETECTOR = """You are helping a job seeker find relevant postings.

The target role: [describe your ideal job — role, location, salary,
tech stack, company type, anything that matters to you].

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""
```

### Step 2: Try different RSS feeds

Any public job RSS feed works with `app_live.py`:

```python
# Stack Overflow remote Python jobs
rss = RSSSource("https://stackoverflow.com/jobs/feed?q=python&r=true")

# We Work Remotely programming jobs
rss = RSSSource("https://weworkremotely.com/categories/remote-programming-jobs.rss")

# Remote OK dev jobs
rss = RSSSource("https://remoteok.io/remote-dev-jobs.rss")
```

### Step 3: Ask Claude to build a variation

Open your DisSysLab Claude project and try:

> Build me a DisSysLab job monitor that reads from these two RSS feeds:
> [paste URLs]. Filter spam, then check if postings match my target role:
> [describe your role]. Save matches to a file and display them.
> Use demo components.

Or paste your own ASCII topology drawing and ask Claude to build it.

### Try the extended version

`app_extended.py` adds a salary extraction step after the relevance check:

```
python_jobs ─┐
              ├→ spam_filter → relevance → salary → split → match   → archive
ml_jobs     ─┘                                           → no_match → (dropped)
```

Each archived posting includes salary fields extracted by a second AI agent.
Compare with `app.py` to see how adding a Transform node extends the pipeline.

---

## Key Concepts

**Custom prompts.** Any string can be a prompt — you're not limited to the
built-in library. `JOB_DETECTOR` is just a string constant in `prompts.py`.
Define your own alongside it and pass it to `ai_agent()`. The prompt is the
behavior. Change the prompt, change the behavior.

**Fanout from a Split port.** A Split output port can fan out to multiple
sinks — `(splitter.out_0, archive)` and `(splitter.out_0, display)` together
give the match branch two destinations. The no-match branch has one.

**The same four building blocks.** Source, Transform, Sink, Split. This is
a real, useful application. No new concepts were needed to build it.

**Real sources require setup.** RSS feeds need `feedparser` and a network
connection. `app.py` uses demo data so you can learn the pattern first.
`app_live.py` connects to the real world once you're ready.

---

## What's Next

**Module 06+** continues the Gallery with more domain-specific monitors —
each a complete working application built with the same four building blocks.