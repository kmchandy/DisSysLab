# Module 05: Job Postings Monitor

*Monitor real job boards. Get alerted when relevant postings appear.*

---

## What You'll Build

A job postings monitor that reads from two live job RSS feeds simultaneously,
filters out spam and irrelevant postings, uses Claude AI to assess how well
each job matches your target role, and routes results to two destinations:

```
python_jobs ─┐
              ├→ spam_filter → relevance → split → match   → archive + display
ml_jobs     ─┘                                  → no_match → (dropped)
```

This is the first Gallery module — a complete, real application built with
the same four building blocks from Modules 01-04. No new node types.
What's new is the source: real RSS feeds instead of demo data.

**This module requires:**
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- The `feedparser` Python package (`pip install feedparser`)

A demo version (`app.py`) runs without any of this.

---

## Files in This Module

| File                      | What it is                                               |
|---------------------------|----------------------------------------------------------|
| `README.md`               | This file                                                |
| `demo_job_source.py`      | Demo job postings (no network needed)                    |
| `app.py`                  | Demo version — run this first, no API keys needed        |
| `claude_generated_app.py` | Exactly what Claude produced from the Part 4 prompt      |
| `app_live.py`             | Real RSS feeds + real Claude AI — the actual monitor     |
| `app_extended.py`         | Extended version that also extracts salary information   |
| `test_module_05.py`       | Tests you can run to verify everything works             |

---

## Part 1: Run the Demo (2 minutes)

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

  ✅ MATCH: Senior Python Engineer at Stripe — Remote, $180k-$220k
  ✅ MATCH: Staff Python Engineer at Anthropic — San Francisco, $200k-$250k
  ✅ MATCH: ML Engineer (Python/PyTorch) at DeepMind — London or Remote
  ✅ MATCH: NLP Engineer at Hugging Face — Remote worldwide, $140k-$180k

════════════════════════════════════════════════════════════
✅ Done! Matches saved to job_matches.jsonl
```

This uses demo job data — the same network structure as `app_live.py` but
with no network calls and no API costs. Move to Part 2 to understand the
design.

---

## Part 2: Understand What You Just Built (10 minutes)

### The design questions

**What to monitor?** Two job feeds: python_jobs and ml_jobs (fanin).

**What processing?**
1. Filter spam — job boards attract a lot of it.
2. Check relevance — does this posting match my target role?

**Where do results go?**
- Matching jobs → saved to file and printed to terminal (fanout)
- Non-matching jobs → dropped silently

**The topology:**
```
  python_jobs ─┐
                ├→ [spam_filter] → [relevance] → [splitter]
  ml_jobs     ─┘                               → out_0 → [archive]
                                               → out_0 → [display]
                                               → out_1 → (dropped via None)
```

Wait — two outputs from `out_0`? That's **fanout from a Split port**. The
match port fans out to both archive and display. The no-match port goes to
a sink that simply drops everything. This is a new topology combination:
Split routing followed by fanout on one branch.

### The relevance check

The key new idea in this module is the **relevance prompt**. Instead of
using a pre-built prompt from the library, the app defines its own:

```python
JOB_RELEVANCE_PROMPT = """You are helping a job seeker find relevant postings.

The target role: senior Python engineer, remote or hybrid, $150k+, at a
tech company working on interesting problems.

Given a job posting title/summary, determine if it is a strong match,
partial match, or not a match for this target role.

Return JSON format:
{
    "match": "STRONG" | "PARTIAL" | "NONE",
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation"
}"""
```

This is the Prompt → JSON → Python pattern in action. You write a prompt
that describes your specific criteria, Claude returns structured JSON, and
your Python function acts on it. To monitor jobs for your own interests,
you change the prompt — the rest of the app stays the same.

### Reading the code

Open `app.py`. The structure is identical to Module 04 — the only new
elements are:

1. `demo_job_source.py` provides job-flavored demo data
2. A custom `JOB_RELEVANCE_PROMPT` replaces a library prompt
3. The routing uses `"STRONG"` and `"PARTIAL"` instead of sentiment labels

Everything else — fanin, spam filter, Split, JSONLRecorder — is exactly
what you've seen before.

---

## Part 3: Run the Real Monitor (setup required)

`app_live.py` connects to real job RSS feeds and uses the real Claude API.

### Setup

**1. Install feedparser:**
```bash
pip install feedparser
```

**2. Set your API key:**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**3. Customize your target role** (optional but recommended):

Open `app_live.py` and find `JOB_RELEVANCE_PROMPT`. Change the target role
description to match what you're actually looking for:

```python
JOB_RELEVANCE_PROMPT = """You are helping a job seeker find relevant postings.

The target role: [describe your ideal job here — role, location, salary,
tech stack, company type, anything that matters to you].

...
```

**4. Run:**
```bash
python3 -m examples.module_05.app_live
```

The monitor reads from two live job RSS feeds, analyzes each posting with
Claude, and saves matches to `job_matches.jsonl`.

### Real RSS feeds used

| Feed                  | URL                                          |
|-----------------------|----------------------------------------------|
| Python jobs (Indeed)  | `https://www.indeed.com/rss?q=python+engineer` |
| Remote ML jobs        | `https://remoteok.io/remote-machine-learning-jobs.rss` |

These are public RSS feeds that require no authentication. `app_live.py`
sets `max_articles=5` per feed to keep API costs low during testing.
Increase this — or remove the limit — once you're satisfied with the results.

### What to expect

Real job RSS feeds contain a lot of noise: expired postings, irrelevant
results, occasionally malformed entries. The spam filter and relevance check
handle most of this. You may want to tune `JOB_RELEVANCE_PROMPT` after
seeing the first few results.

---

## Part 4: Make It Yours (homework)

The power of this monitor is that the entire behavior is controlled by one
prompt. To monitor for a completely different type of job, you only change
`JOB_RELEVANCE_PROMPT`.

### Try these variations

**Change the target role:**
```python
# Instead of Python engineer, monitor for data science roles:
The target role: data scientist with Python and SQL skills,
open to remote or NYC, $130k+, at a company with interesting datasets.
```

**Add a salary extractor** (see `app_extended.py`):
```python
# After relevance check, extract salary range if mentioned:
from components.transformers.prompts import ENTITY_EXTRACTOR
```

**Monitor different feeds:**
```python
# Try any public job RSS feed:
rss = RSSSource("https://stackoverflow.com/jobs/feed?q=python&r=true")
rss = RSSSource("https://weworkremotely.com/categories/remote-programming-jobs.rss")
rss = RSSSource("https://remoteok.io/remote-dev-jobs.rss")
```

### Ask Claude to build a variation

> Build me a DisSysLab job monitor that reads from these two RSS feeds:
> [paste URLs]. Filter spam, check if postings match my target: [describe
> your target role]. Save matches to a file. Use real components.

---

## Key Concepts

**Custom prompts.** Any string can be a prompt — you're not limited to the
built-in library. Define `MY_PROMPT = """..."""` and pass it to `ai_agent()`.
The prompt is the behavior. Change the prompt, change the behavior.

**Real sources require error handling.** RSS feeds can be slow, return
malformed entries, or include HTML in text fields. `RSSSource` strips HTML
automatically. Network timeouts are handled by increasing `timeout` in
`run_network()`.

**Fanout from a Split port.** A Split output port can fan out to multiple
sinks — `(splitter.out_0, archive)` and `(splitter.out_0, display)` together
give the match branch two destinations.

**The same four building blocks.** Source, Transform, Sink, Split. This is
a real, useful application. No new concepts were needed to build it.

---

## What's Next

**Module 06+** continues the Gallery with more domain-specific monitors —
each a complete working application built with the same four building blocks.