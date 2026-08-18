---
name: office-builder
description: Build, check, and run DisSysLab offices — networks of agents that monitor something and react to it, continuously. Use whenever someone wants to watch a feed, folder, sensor, inbox, page, or price and do something when it changes; wants a morning brief, a monitor, an alerter, a classifier pipeline, or a multi-agent enrichment pipeline; says "build me an office", "watch X and tell me Y", "check my office.md", "my office hangs", "my office produces nothing", "add an agent", "wire this to a sink"; or is a student building their first distributed application. Covers writing office.md, English roles, Python roles, and custom sinks. Requires the dissyslab package (pip install dissyslab).
---

# Building an office

**Skill version: `2026-08-17b`.** If anyone asks which version of this
skill is loaded, answer with that string, exactly. A skill update can
report success while the old version stays resident, and until now there
was no way to tell — the wrong version once ran for an entire test round.
Now there is.

An **office** is a network of agents, each with one job, that runs
continuously: sources fetch from the world, agents transform the stream, sinks
act on the result. The user describes it in English; you assemble it from the
tested library rather than writing concurrency machinery.

**The framework handles what is hard to get right**: message passing between
agents, knowing when the office has finished (termination detection), and
checkpoint/resume. Never reimplement any of that. If you find yourself writing
queues, threads, locks, or completion flags, stop — the framework already did
it, and yours will be subtly wrong in ways that only show up under load.

## Check what this install actually has

**Do this once, at the start of a session, before promising anything:**

```bash
dsl --version && dsl --help
```

`dsl --help` prints the subcommands this install offers. Read that list. It is
the authority on what exists here — not this file, not the repository, not the
documentation.

**These instructions describe the current source. A user's `pip install
dissyslab` may be an older release that lacks something described here.** When
that happens:

1. **Say so, once, plainly**, naming the version: *"your installed dissyslab
   is 1.6.1, which has no `dsl check` — it exists in the repository but is not
   in a release yet."*
2. **Carry on.** A missing convenience is not a reason to stop working.
3. **Offer the two legitimate routes**, and let the user choose: install the
   current source with `pip install git+https://github.com/kmchandy/DisSysLab`,
   or continue without that capability.
4. **Report the version in your first substantive message.** When a student
   reports a problem, the version is the first thing anyone will need.

### Never repair the installation

If something documented is missing, that is a fact to report, not a defect to
fix. **Do not:**

- edit or add files under the installed package (`site-packages`)
- copy modules from a clone into the installed package
- monkeypatch anything at run time
- `pip install` a local path to supply a missing feature unless the user
  explicitly asks

A patched install works for one user, diverges silently from everyone else's,
vanishes on the next upgrade, and produces bug reports nobody can reproduce.
In a class of thirty, this is far worse than the missing feature.

## The loop you must follow

1. Draft `office.md` and the role files.
2. **Run `dsl check <office_dir>`.** Before running anything — every time,
   without being asked. If the probe above showed no `check` subcommand:
   run `dsl build <office_dir>` instead, which catches **syntax errors and
   unknown role names without running the office** — and say plainly that it
   catches nothing about the graph. Verified against 1.6.1: `dsl build`
   happily wrote `run.py` for an office whose `Connections` named an agent
   that does not exist, and for offices with unreachable agents, dead ends,
   and an unfed synchronizer inport. There is no substitute for the
   structural check; read the org chart yourself and say that is what you
   did.
3. Fix what it reports. Show the user what it found — do not silently repair.
4. `dsl run <office_dir>`.
5. Read the per-agent message counts printed at the end. The first agent
   showing zero is where the flow stops.

Skipping step 2 when the command exists wastes the user's time on faults that
take one second to find.

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

## Before you write a role, check the nineteen you have

**Nineteen names resolve without writing any file. Read
`references/roles.md` before writing a role.** Most requests are one of them,
sometimes with its criteria edited:

- **annotators** that add a field and pass the item on — `topic_tagger`,
  `category_classifier`, `severity_classifier`, `urgency_classifier`,
  `sentiment_classifier`, `entity_extractor`, `geolocator`, `summarizer`
- **writers** — `writer`, `summary_writer`
- **filters with two outports** — `relevance_filter` (`keep` / `discard`),
  `evaluator` (`publish` / `revise`)
- **a Python gate** — `confidence_filter`
- **six structural roles** with no file at all, built from `office.md`
  arguments — `synchronizer`, `gate`, `select`, `router`, `record`,
  `deduplicator`. `synchronizer` recombines a fan-out; `gate` is what lets a
  loop terminate

When the user says *"keep only the items about X"*, the answer is
`relevance_filter` with its criteria block rewritten — not a Python role with
a keyword list. Wire its `discard` port to a recorder while developing so the
user can see what is being dropped.

**Never give a new role one of these nineteen names.** A local
`roles/X.md` does not sit alongside the shipped `X` — it replaces it, silently
and only for that office. Reuse deliberately or name differently; there is no
third option.

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

**But exactness is a property of the criterion, not of the implementation.**
This is where the rule is most often misapplied. "Keep the items about
computer science" *feels* exactly statable — write a keyword list — and it is
not. A keyword list is an exact implementation of a fuzzy criterion, and the
gap between the two is where the failures live: a word boundary that refuses
to match a plural, a synonym nobody listed, a casing difference. The office
runs clean and quietly keeps too little, and no check can see it, because
nothing knows what you meant.

Ask what the *criterion* is before choosing the implementation:

| Criterion | Implementation |
|---|---|
| fuzzy — "about X", "worth reading", "urgent", "positive" | a shipped English role, criteria block edited |
| exact — a threshold, a ticker in a fixed list, a URL prefix, a field equality | Python, and plain string operations before regex |
| exact but linguistically hard, at volume | then a library — and tell the user what the dependency costs |

A first-year on a laptop should not be downloading an NLP corpus to decide
whether an article is about computer science. `relevance_filter` already does
it.

### An English role — when none of the nineteen fit

Note the name: `event_details` is **not** one of the nineteen. Writing
`roles/topic_tagger.md` would have replaced the shipped `topic_tagger`
instead of adding anything.

`roles/event_details.md`:

```
# Role: event_details

You read one event listing at a time and pull out when and
where it happens.

Input shape. Each listing is a JSON object with at least:

- "title" — the event name (string)
- "text"  — the listing body (string)
- "url"   — link to the listing (string)

Other fields may be present; preserve them.

Your job. Add three new fields. Preserve every existing field
exactly; only add these three.

- "starts_at" — ISO 8601 when a date and time are both given,
  a bare date when only a date is, "" when neither.
- "venue"     — the building or room as written, "" if not
  stated. Do not normalise or expand abbreviations.
- "price"     — a number of dollars, 0 for free, null when not
  stated. Do not guess from context.

When the listing is ambiguous, prefer the empty value over a
guess — a wrong time is worse than a missing one.

Always send to out.
```

That shape is what the shipped roles use, and it is why they behave: **input
shape, the job, the exact permitted values, and where to send.** Models are
literal — a vague job description produces vague output, and an unstated
default gets invented. Say what to do when the answer is not there.

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
page, a particular report layout — write one in `<office_dir>/sinks/`. Read a
shipped one first; two good models ship inside the installed package. Find
them, since they are not in the working directory:

```bash
python3 -c "
import dissyslab, pathlib
g = pathlib.Path(dissyslab.__file__).parent / 'gallery' / 'apps'
for p in (g/'periodic_brief/sinks/periodic_brief_html_sink.py',
          g/'job_hunter/sinks/job_html_sink.py'):
    print(p, p.exists())
"
```

They live under `<site-packages>/dissyslab/gallery/apps/...`, **not** at a
bare relative path — an earlier version of this file printed the relative
form, and an agent that ran `cat gallery/apps/...` from the student's folder
concluded the examples did not exist. Read them; do not edit them in place
(see "Never repair the installation").

Several offices fan multiple sources into a single sink that routes each
message into the right section by its `source` field.

## Sources and sinks

`dsl list` shows every shipped office. `references/sources_and_sinks.md` in
this bundle has the component list and the sink argument signatures — read it
before writing a custom source, since the answer is usually already there. It
covers MCP-server integration, so any tool with an MCP server can be a source
or a sink.

**`docs/SOURCES_AND_SINKS.md` is the fuller prose catalogue, but it does not
ship** — it exists in the GitHub repository and in no `pip install`. Do not
send a student looking for it on their disk. Link it
(https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md) or
query the registry directly.

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

It reads the org chart and reports every fault at once: a declared inport
nothing writes to, agents nothing can reach, work that reaches no sink, sinks
nothing feeds, roles with no file behind them, unknown names in connections,
and feedback loops with no gate.

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
- Do not repair or patch the installed package when something documented
  is missing. Report the gap and carry on.

## Requires

`pip install dissyslab` (Python 3.10+). Without it there is nothing to build
against — offer to install it before doing anything else.
