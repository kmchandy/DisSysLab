---
name: office-builder
description: Build, check, and run DisSysLab offices — networks of agents that monitor something and react to it, continuously. Use whenever someone wants to watch a feed, folder, sensor, inbox, page, or price and do something when it changes; wants a morning brief, a monitor, an alerter, a classifier pipeline, or a multi-agent enrichment pipeline; says "build me an office", "watch X and tell me Y", "check my office.md", "my office hangs", "my office produces nothing", "add an agent", "wire this to a sink"; or is a student building their first distributed application. Covers writing office.md, English roles, Python roles, and custom sinks. Requires the dissyslab package (pip install dissyslab).
---

# Building an office

An **office** is a network of agents, each with one job, that runs
continuously: sources fetch from the world, agents transform the stream, sinks
act on the result. The user describes it in English; you assemble it from the
tested library rather than writing concurrency machinery.

**The framework handles what is hard to get right**: message passing between
agents, knowing when the office has finished (termination detection), and
checkpoint/resume. Never reimplement any of that. If you find yourself writing
queues, threads, locks, or completion flags, stop — the framework already did
it, and yours will be subtly wrong in ways that only show up under load.

## The loop you must follow

1. Draft `office.md` and the role files.
2. **Run `dsl check <office_dir>`.** Always. Before running anything.
3. Fix what it reports. Show the user what it found — do not silently repair.
4. `dsl run <office_dir>`.
5. Read the per-agent message counts printed at the end. The first agent
   showing zero is where the flow stops.

Skipping step 2 wastes the user's time on faults that take one second to find.

## An office.md

Four sections. This is the whole program:

```
# Office: situation_room

Sources: bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: intelligence_display, jsonl_recorder_briefing(path="briefings.jsonl")

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Sync is a synchronizer.
Riley is a writer.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
Sasha's out is Eve, Sam.
Eve's out is Sync's entities.
Sam's out is Sync's severity.
Sync's out is Riley.
Riley's out is intelligence_display, jsonl_recorder_briefing.
```

Notes that save debugging time:

- A source's outport may be written `destination` or `out`. Both are legal.
- A sink has exactly one inbox, always `in_`.
- `X's out is Y, Z.` is fan-out — one message to both.
- `Eve's out is Sync's entities.` sends into a *named* inport. A
  synchronizer's inports are defined by whatever gets wired to it.
- The network **may contain cycles**. Loops are legal and often intended. A
  loop needs a `gate` if it is to terminate.
- Keep `max_articles=N` / `max_readings=N` limits in place. They stop a
  student running up an LLM bill by accident. Remove only when asked.

## English role or Python role

Each agent's job lives in `roles/<role_name>.md` (English, run by a language
model) or `roles/<role_name>.py` (Python, deterministic and free).

**The line to draw** — and the framework's own roles follow it: a role belongs
in Python when its contract is on *content* or *arithmetic*; the generic
behaviour around it belongs to the library. `wildlife_watcher` puts the image
classifier in a local Python role because it is specific to ImageNet classes,
and uses the library's `confidence_filter` for the gating that follows.

Use **English** when the job needs judgment: classify severity, extract
entities, tag a topic, write a briefing, decide whether an email is urgent.

Use **Python** when the job is exact, numeric, or wraps a model: deduplicate,
compute a moving average or RMS, threshold a reading, run a classifier,
reshape a record. Python roles cost nothing per message; English roles call a
model every time.

Prefer Python whenever the job can be stated exactly. It is cheaper, faster,
deterministic, and testable.

### An English role

`roles/topic_tagger.md`:

```
# Role: topic_tagger

You read one news article at a time and assign it to one of:
politics, business, technology, science, health, sports,
entertainment, other.

Preserve the original article. Add one new field, "topic",
whose value is one of the eight labels above.

Always send to out.
```

Rules that make English roles behave: say what arrives, what to preserve, what
to add, and **always where to send it**. Models are literal — a vague job
description produces vague output. Name the exact allowed values.

### A Python role

The contract, taken from a working role:

```python
from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


class _InsideClassifier(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self.count: int = 0

    # Optional. Implementing these two is what lets an office
    # checkpoint and resume this agent after a crash.
    def save_state(self):
        return {"count": self.count}

    def load_state(self, state):
        self.count = int((state or {}).get("count", 0))

    def run(self):
        while True:
            msg = self.recv("in_")
            if msg["x"] ** 2 + msg["y"] ** 2 < 1.0:
                self.count += 1
                self.send({"kind": "inside", "running_count": self.count}, "out_")


role = AgentRoleEntry(
    name="inside_classifier",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_InsideClassifier,
)
```

Points that are easy to get wrong:

- The module must end with a module-level `role = AgentRoleEntry(...)`.
- **The port spellings differ between the two places.** `Agent.__init__` takes
  `outports=["out_"]` (trailing underscore) while `AgentRoleEntry` takes
  `out_ports=("out",)` (no underscore). Copy this exactly rather than
  reasoning about it.
- `run()` is an infinite loop over `self.recv(port)`. Never return from it
  voluntarily — returning kills the agent's thread before the office can
  finish polling it, and termination detection then blocks forever.
- Emitting nothing for a message is fine: just don't call `send`.
- Add `save_state`/`load_state` whenever the agent holds state worth keeping
  across a crash. Without them the agent restarts empty.

### A custom sink

When no shipped sink produces the artifact the user wants — a styled HTML
page, a particular report layout — write one in `<office_dir>/sinks/`. Model
it on `gallery/apps/periodic_brief/sinks/periodic_brief_html_sink.py` or
`gallery/apps/job_hunter/sinks/job_html_sink.py`; read one before writing one.
Several offices fan multiple sources into a single sink that routes each
message into the right section by its `source` field.

## Sources and sinks

`dsl list` shows every shipped office. The full catalogue of sources and sinks
is `docs/SOURCES_AND_SINKS.md` — read it before writing a custom source. It
includes MCP-server integration, so any tool with an MCP server can be a
source or a sink.

Common ones: RSS/news feeds, weather, stock tickers, an image or audio folder,
a webhook listener, Gmail; and for sinks, console, JSONL recorder, HTML
writers, a discard.

## Starting from a shipped office

**Always `dsl init`, never `dsl run` on a shipped office.**

```
dsl init periodic_brief my_brief
cd my_brief
dsl run .
```

`dsl run periodic_brief` does work, but it writes its output *inside the
installed package* rather than the user's folder, and they will not find it.
`dsl init` makes an editable copy in the working directory.

## What `dsl check` catches, and what it cannot

It reads the org chart and reports every fault at once: agents nothing can
reach, work that reaches no sink, sinks nothing feeds, roles with no file
behind them, unknown names in connections, and feedback loops with no gate.

It is **structural**. It cannot see faults that depend on what happens at run
time. An office whose diagram is perfectly correct can still get stuck,
because getting stuck can depend on which messages actually arrive and in what
order. If `dsl check` is clean and the office still hangs, the fault is in the
run, not the wiring — look at which agent is blocked and on which inport.

Worth telling a student explicitly: the difference between what you can know
from the diagram and what you can only know from an execution is one of the
real ideas in this subject.

## When something goes wrong

| Symptom | First move |
|---|---|
| Hangs, nothing happens | `dsl check`. If clean, find which agent is blocked on which inport and what would have to arrive. |
| Runs, produces nothing | Per-agent message counts at the end of the run. First zero is where flow stops. A sink nothing feeds is the usual cause. |
| A sink's file is empty | Almost always no connection writes to that sink. `dsl check` names it as W8. |
| English role does something odd | The job description is underspecified. State the allowed values and where to send. |
| Import or backend error | `dsl doctor`. |

## Do not

- Do not write threads, queues, locks, or your own termination logic.
- Do not run an office before `dsl check` is clean.
- Do not silently fix what the check reports — show the user; the fault is
  often the lesson.
- Do not remove `max_articles` / `max_readings` limits unless asked.
- Do not put a model wrapper or a heavy dependency in an English role.

## Requires

`pip install dissyslab` (Python 3.10+). Without it there is nothing to build
against — offer to install it before doing anything else.
