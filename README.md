# DSL — Build Your Own Office of AI Agents

**Claude answers when you ask. What if Claude worked for you all the time — even when you're not there?**

DSL lets you build an office of AI agents that runs continuously, 24 hours a day.
You describe each agent's job in plain English. You specify who talks to whom.
One command starts your office. Your agents work while you sleep.

This is how you build an office that creates your Situation Room — scanning live
news and social media, filtering for what matters, filing briefings in real time.
You didn't write any code. You wrote two plain English files.

---

![Situation Room](gallery/org_situation_room/screenshot.png)

---

## What You Wrote

Two plain English files. Nothing else.

**The job descriptions — what each agent does:**

```
# Role: analyst

You are a news analyst who receives posts and articles and sends
items to an editor or a discard.

Your job is to decide if each item is relevant to significant
political developments or economic events — specifically involving
topics such as Trump, Congress, Senate, elections, the Federal Reserve,
tariffs, inflation, markets, Ukraine, Iran, trade policy, or the
broader economy.

Exclude celebrity gossip, sports, entertainment, and personal
opinions with no broader political or economic significance.

If the item is relevant, send to editor.
Otherwise send to discard.
```

```
# Role: editor

You are a senior editor who receives posts and articles and sends
items to a situation_room.

Your job is to rate each item for its significance — CRITICAL, HIGH,
MEDIUM, or LOW — and rewrite it as a crisp one-paragraph briefing note.
Note whether the item came from social media or news. Preserve the
source, url, timestamp, and author fields. Put your significance rating
in a field called "significance" and your summary in the "text" field.

Always send results to situation_room.
```

**The org chart — who connects to whom:**

```
Sources: bluesky(max_posts=None, lifetime=None),
         al_jazeera(max_articles=10, poll_interval=600),
         bbc_world(max_articles=10, poll_interval=600)
Sinks: intelligence_display(max_items=8),
       jsonl_recorder(path="situation_room.jsonl")

Agents:
Alex is an analyst.
Morgan is an editor.

Connections:
bluesky's destination is Alex.
al_jazeera's destination is Alex.
bbc_world's destination is Alex.
Alex's editor is Morgan.
Alex's discard is jsonl_recorder.
Morgan's situation_room are intelligence_display and jsonl_recorder.
```

That's it. The compiler reads these files, shows you the routing,
asks "Does this look right?", and generates your office.

```
al_jazeera ─┐
bbc_world   ─┤→  Alex  →  Morgan  ─┬→  Situation Room display
bluesky     ─┘                      └→  situation_room.jsonl
```

---

## Quick Start

**Step 1 — Clone and install:**

```bash
git clone https://github.com/your-org/DSL.git
cd DSL
pip install -r requirements.txt
export ANTHROPIC_API_KEY='your-key'
```

**Step 2 — Compile your office:**

```bash
python3 office_compiler.py gallery/org_situation_room/
```

The compiler shows you what it understood and asks for confirmation.
If anything looks wrong, edit your files and rerun — no Python required.

**Step 3 — Start your office:**

```bash
python3 -m gallery.org_situation_room.app
```

Your Situation Room starts immediately. Alex scans incoming posts and
articles. Morgan writes briefings. The display updates in real time —
BlueSky posts arrive seconds apart, RSS articles arrive as they're
published. Your office runs until you stop it.

---

## Build Your Own Office

Change the topics. Change the agents. Change the sources.
The office is yours.

**To build your own:**

1. Create a new directory: `gallery/org_your_idea/`
2. Write a role file for each type of agent in `roles/`
3. Write an org chart in `office.md`
4. Run: `python3 office_compiler.py gallery/org_your_idea/`

**Some ideas:**

- A research assistant that monitors arXiv for papers in your field,
  filters for relevance, and summarizes findings into a daily digest
- A competitive intelligence office that scans tech news, flags
  mentions of your competitors, and rates their significance
- A job scout that monitors job boards, filters for your skills,
  and ranks postings by fit
- A policy tracker that monitors government sources and flags
  regulatory changes relevant to your industry
- A personal finance monitor that tracks market news and flags
  developments relevant to your portfolio

---

## Going Further

Once your first office is running, the possibilities expand naturally.

**Multiple agents in the same role.** You can have two analysts —
Alex focused on politics, Jordan focused on economics — both feeding
the same editor. Just add agents to your office spec.

**Networks of offices.** A legal office feeds a CEO office. An
intelligence office feeds a strategy office. In DSL, an office can
itself be an agent in a larger office. The infrastructure is already
there.

**Agent personas.** Your editor is measured and balanced. What if
she were pessimistic? What if your analyst only flagged stories
involving specific countries? Agent behavior is entirely determined
by the job description — change the description, change the behavior.
No code changes required.

---

## Available Sources

```
bluesky          — live social media stream, no auth needed
al_jazeera       — Al Jazeera world news
bbc_world        — BBC world news
bbc_tech         — BBC technology news
npr_news         — NPR news
hacker_news      — Hacker News
techcrunch       — TechCrunch
mit_tech_review  — MIT Technology Review
venturebeat_ai   — VentureBeat AI
nasa_news        — NASA news
python_jobs      — Python job listings
```

## Available Sinks

```
intelligence_display(max_items=N)  — live color-coded dashboard
console_printer                    — plain text to console
jsonl_recorder(path="file.jsonl")  — save to JSON Lines file
```

---

## Gallery

| Office | What it does |
|--------|-------------|
| [Situation Room](gallery/org_situation_room/) | Live politics & economics monitor — BlueSky + RSS |
| [Intelligence Briefing](gallery/org_intelligence_briefing/) | World news briefing, significant events only |
| [News Filter](gallery/org_news_filter/) | Filters articles by geography |
| [News Chain](gallery/org_news_chain/) | Two-agent editorial chain |

---

## How It Works

DSL compiles your plain English files into a Python distributed system.
Each agent runs in its own thread. Messages flow through queues.
The framework handles all concurrency, synchronization, and shutdown.

```
Your plain English files
        ↓
office_compiler.py  (uses Claude to parse your descriptions)
        ↓
app.py  (generated — complete runnable Python)
        ↓
Concurrent agents processing live data, running forever
```

Unlike tools that re-run a pipeline on a schedule, DSL agents are
always running — waiting for the next message, processing it
immediately, passing it on. BlueSky posts arrive seconds apart.
RSS articles arrive the moment they're published. Your office
responds in real time.

---

## For the Curious: How DSL Is Implemented

Interested in how this works under the hood? DSL is also a complete
Python framework for building distributed systems — sources, transforms,
splits, sinks, fanin, fanout, message queues, concurrent threads.

The module sequence takes you from generating your first app with Claude
to building the framework primitives from scratch:

| Module | Topic |
|--------|-------|
| M1 | Describe and Build — generate your first app with Claude |
| M2 | Multiple Sources and Destinations — fanin and fanout |
| M3 | Smart Routing — filter and split messages |
| M4 | Build Your Own — write agents from scratch |

Start here: [`examples/module_01_describe_and_build/README.md`](examples/module_01_describe_and_build/README.md)

---

## Requirements

- Python 3.10+
- Anthropic API key ([get one here](https://console.anthropic.com))
- `pip install -r requirements.txt`

---

*DSL is an open research project exploring Claude's ability to specify,
compile, and run persistent distributed systems from natural language.*