# DisSysLab: Persistent Distributed Multi-Agent Systems

*Describe your organization. Deploy it. Watch it run.*

---

## The Core Idea

A distributed multi-agent system is an organization of workers:

- Each **agent** has a job description — what it receives, what it decides, what it returns
- Each **connection** is a routing rule — when agent A produces output with status X, send it to agent B
- The **system runs persistently** — not a script that runs once, but a living organization that keeps processing as long as data arrives

DisSysLab lets you build these systems in two steps:

1. **Define agents** — write a job description (a prompt) for each worker
2. **Define routing** — list the connections as `(sender, status, receiver)` triples

That's it. No threading code. No queue management. No synchronization logic.

---

## Step 1: Define Agents with Job Descriptions

Every agent in DisSysLab has a **job description** — a prompt that tells it exactly what to do with each message it receives.

Here is a news editor agent:

```python
from dsl.blocks.role import Role
from components.transformers.ai_agent import ai_agent

EDITOR_PROMPT = """
You are a news editor. Read the article and score its sentiment
from 0.0 (extremely negative) to 1.0 (extremely positive).

Rules:
- Score below 0.25 or above 0.75 → assign status: interesting
- Score between 0.25 and 0.75   → assign status: boring

Return JSON only, no explanation:
{"text": "<original text>", "score": <float>, "status": "interesting" or "boring"}
"""

editor = Role(
    fn=ai_agent(EDITOR_PROMPT),
    statuses=["interesting", "boring"],
    name="editor"
)
```

The job description specifies:
- What the agent receives (an article)
- What it decides (interesting or boring)
- What it returns (the article with a score and status)

The `statuses` list tells DisSysLab what routing decisions this agent can make. Each status maps to one output channel.

---

## Step 2: Define Routing with Status-Based Connections

Connections are specified as `(sender, status, receiver)` triples:

```python
("editor", "interesting", "archive")   # interesting articles → archive
("editor", "boring",      "rewriter")  # boring articles → rewriter
```

This reads exactly like an org chart:
- *When the editor marks an article as interesting, send it to the archive*
- *When the editor marks an article as boring, send it to the rewriter*

Use `"all"` when an agent has only one output and no routing decision:

```python
("rewriter", "all", "editor")   # all rewritten articles → back to editor
```

---

## A Complete Example: The Editorial Pipeline

Three news sources feed into an editor. Interesting articles go to an archive. Boring articles go to a copy writer who rewrites them and sends them back to the editor.

### The Agents

```python
from dsl.blocks import Source, Sink
from dsl.blocks.role import Role
from dsl import network
from components.transformers.ai_agent import ai_agent
from components.sources.rss_normalizer import al_jazeera, bbc_world, npr_news
from components.sinks.sink_jsonl_recorder import JSONLRecorder

EDITOR_PROMPT = """
You are a news editor. Score the article sentiment from 0.0 to 1.0.

Rules:
- Score below 0.25 or above 0.75 → status: interesting
- Score between 0.25 and 0.75   → status: boring

Return JSON only, no explanation:
{"text": "<original text>", "score": <float>, "status": "interesting" or "boring"}
"""

COPY_WRITER_PROMPT = """
You are a copy writer. Rewrite the article to make it more strongly
opinionated — either more positive or more negative, whichever
requires less change. Keep the core facts intact.

Return JSON only, no explanation:
{"text": "<rewritten text>", "score": <float>}
"""

# Define the agents
editor = Role(
    fn=ai_agent(EDITOR_PROMPT),
    statuses=["interesting", "boring"],
    name="editor"
)

copy_writer = Role(
    fn=ai_agent(COPY_WRITER_PROMPT),
    statuses=["all"],
    name="copy_writer"
)
```

### The Sources and Sinks

```python
aj  = al_jazeera(max_articles=5)
bbc = bbc_world(max_articles=5)
npr = npr_news(max_articles=5)

src_aj  = Source(fn=aj.run,  name="al_jazeera")
src_bbc = Source(fn=bbc.run, name="bbc_world")
src_npr = Source(fn=npr.run, name="npr_news")

recorder = JSONLRecorder(path="output.jsonl", mode="w", flush_every=1)
sink = Sink(fn=recorder, name="archive")
```

### The Org Chart

```
al_jazeera ─┐
bbc_world  ─┼──→ editor ──[interesting]──→ archive
npr_news   ─┘         │
                      └──[boring]──→ copy_writer
                                         │
                                         └──[all]──→ editor
```

### The Routing

```python
g = network([
    # Sources feed into editor
    (src_aj,  "all", "editor"),
    (src_bbc, "all", "editor"),
    (src_npr, "all", "editor"),

    # Editor routes by status
    ("editor",      "interesting", "archive"),
    ("editor",      "boring",      "copy_writer"),

    # Copy writer sends all output back to editor
    ("copy_writer", "all",         "editor"),
])
```

### Run It

```python
if __name__ == "__main__":
    g.run_network(timeout=None)
    recorder.finalize()
```

---

## The Two Rules

Every DisSysLab org system follows exactly two rules:

**Rule 1: Agents are defined by job descriptions.**

```python
agent = Role(
    fn=ai_agent("Your job description here..."),
    statuses=["status_a", "status_b"],
    name="agent_name"
)
```

The prompt tells the agent what to do. The statuses tell DisSysLab what routing decisions the agent can make.

**Rule 2: Routing is defined by status-based connections.**

```python
("sender", "status", "receiver")
```

When `sender` produces output with the given `status`, DisSysLab delivers it to `receiver`. The system handles all threading, queuing, and message passing automatically.

---

## Sources and Sinks

Sources produce data. Sinks consume it. Neither makes routing decisions, so they use `"all"`:

```python
# Source feeding into a Role:
(my_source, "all", "editor")     # object syntax also works:
(my_source, editor)              # these two lines are equivalent

# Role feeding into a Sink:
("editor", "interesting", "archive")
```

---

## Mixing Syntax

Object syntax and string syntax can be mixed freely:

```python
g = network([
    (src_aj,  editor),                        # object syntax
    (src_bbc, editor),                        # object syntax
    ("editor", "interesting", "archive"),     # string syntax
    ("editor", "boring",      "copy_writer"), # string syntax
    ("copy_writer", "all",    "editor"),      # string syntax
])
```

Use object syntax when it reads more naturally (especially for sources and sinks). Use string syntax when the routing logic is the focus.

---

## Designing Your Own Org

Start with the org chart on a whiteboard:

1. **What are the roles?** Name each worker and describe their job in one sentence.
2. **What decisions does each role make?** These become the statuses.
3. **Where does each decision send output?** These become the routing rules.
4. **Where does data come from and go to?** These become sources and sinks.

Then translate directly to code:
- Each role → one `Role(fn=ai_agent(...), statuses=[...], name=...)`
- Each routing rule → one `("sender", "status", "receiver")` triple
- Each source → one `Source(fn=..., name=...)`
- Each sink → one `Sink(fn=..., name=...)`

The org chart IS the code.

---

## Requirements

```bash
export ANTHROPIC_API_KEY='your-key-here'
pip install anthropic
```

---

## What's Next

- **`app.py`** — the same pipeline implemented in pure Python (no API key needed)
- **`gallery/`** — more example organizations ready to run
- **`examples/`** — step-by-step modules explaining how DisSysLab works under the hood
