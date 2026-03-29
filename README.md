# DSL — Build Your Own Office of AI Agents

# DSL — Build Your Own Office of AI Agents

**AI tools answer when you ask. What if a network of AI agents worked for you all the time?**

## 🎓 New to DisSysLab? Start here
[Take the 5-minute micro-course](https://kmchandy.github.io/DisSysLab/microcourse.html)

---

DSL lets you build an office of AI agents that runs continuously and never stops
until you tell it to.
Your agents monitor sources, analyze data, control devices, and store results for you, all
the time.

---

![Situation Room](gallery/org_situation_room/screenshot.png)

*A Situation Room scanning live news and social media in real time.
You didn't write any code. You wrote two plain English documents.*

---

## Get Started in 2 Minutes

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DSL
pip install -r requirements.txt
export ANTHROPIC_API_KEY='your-key'

python3 office_compiler.py gallery/org_intelligence_briefing/
```

The compiler reads your plain English files, shows you the routing,
asks "Does this look right?", and starts your office.

---

## Two Paths Forward

### Path A — Describe your office in plain English: Job Descriptions and Org Chart

You write job descriptions and an org chart. No programming required.

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

That's it. Change the topics, change the agents, change the sources.
The office is yours.

**Offices can contain offices.** An office is
a building block which you can put into a network with other offices
— a news office feeding a strategy office, a research
office feeding an editorial office. Each office is a black box: the
organization only knows what goes in and what comes out. You can build
organizations of arbitrary complexity, one office at a time, reusing
offices across different networks.

**→ [Go to the gallery](gallery/README.md) to run an existing office and build your own.**

---

### Path B — Learn how distributed systems work

**Interested in how DSL works under the hood?** 
DSL is also a  Python framework for building distributed systems —
concurrent agents, message queues, routing, and termination detection.
See [`examples/`](examples/README.md) for a module sequence that takes you 
from your first network to building distributed systems from scratch.

---

## Requirements

- Python 3.10+
- Anthropic API key ([get one here](https://console.anthropic.com))
- `pip install -r requirements.txt`

---

*DSL is an open research project exploring natural language interfaces
to persistent distributed systems.*