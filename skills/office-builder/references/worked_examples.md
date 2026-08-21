# Four worked examples

Every office below is real and shipped. Read the one whose *shape* matches
what the user asked for, then adapt. Copying a working shape beats composing
from the grammar.

Make an editable copy with `dsl init <office_name> <new_dir>` — never edit a
shipped office in place, and never `dsl run` one directly (its output lands
inside the installed package).

---

## 1. Fan-in to one sink — `periodic_brief`

**Shape:** several sources → one sink. No agents at all.
**Use when:** the user wants one artifact assembled from several feeds, and
nothing needs judgment.

```
# Office: periodic_brief

Sources: bbc_world(max_articles=5), npr_news(max_articles=5), weather(city="Pasadena", max_readings=1), stocks(ticker="AAPL", max_readings=1), stocks_2(ticker="NVDA", max_readings=1), stocks_3(ticker="MSFT", max_readings=1)
Sinks: periodic_brief_html_sink(path="brief.html")

Connections:
bbc_world's destination is periodic_brief_html_sink.
npr_news's destination is periodic_brief_html_sink.
weather's destination is periodic_brief_html_sink.
stocks's destination is periodic_brief_html_sink.
stocks_2's destination is periodic_brief_html_sink.
stocks_3's destination is periodic_brief_html_sink.
```

**What to take from it.** No LLM, no API key, runs in 10–20 seconds — which
makes it the right first thing to show anyone. The sink does the assembly,
routing each message into the right section by its `source` field. Three
tickers means three source declarations, not one with three arguments.

---

## 2. Fan-out, enrich, synchronise — `situation_room`

**Shape:** sources → dedupe → four parallel enrichers → synchroniser → writer
→ sinks.
**Use when:** each item needs several independent judgments that then have to
be recombined. This is the workhorse shape for anything resembling triage.

```
# Office: situation_room

Sources: bbc_world(max_articles=3), npr_news(max_articles=3), al_jazeera(max_articles=3)
Sinks: intelligence_display, jsonl_recorder_briefing(path="briefings.jsonl")

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer(inboxes=["entities", "severity", "topic", "location"]).
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

**What to take from it.** It has **no `roles/` directory** — every role is a
shipped English role. That is the point: this whole application is one file.
`Sasha's out is Eve, Sam, Tom, Greta.` is fan-out — the same article goes to
all four. The synchroniser declares its four inboxes explicitly and every one
is wired; declare four and wire three and it blocks forever. Blank lines group
the connection stanzas and are ignored by the parser.

---

## 3. Python roles that hold state — `recovery_demo`

**Shape:** source → two classifiers → combiner → sink, with agents that count.
**Use when:** the job is arithmetic rather than judgment, and when state has to
survive a crash.

```
# Office: recovery_demo

Sources: csv_points_source(path="./samples/points.txt", interval=0.005)
Sinks:   intelligence_display

Agents:
Alex is an inside_classifier.
Bob  is an outside_classifier.
Pi   is a pi_combiner.

Connections:
csv_points_source's destination is Alex, Bob.
Alex's out is Pi.
Bob's out is Pi.
Pi's out is intelligence_display.
```

`roles/inside_classifier.py`:

```python
from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


class _InsideClassifier(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inboxes=["in_"], outboxes=["out_"])
        self.count: int = 0

    def save_state(self):
        return {"count": self.count}

    def load_state(self, state):
        self.count = int((state or {}).get("count", 0))

    def run(self):
        while True:
            msg = self.recv("in_")
            x, y = float(msg["x"]), float(msg["y"])
            if x * x + y * y < 1.0:
                self.count += 1
                self.send({"kind": "inside", "running_count": self.count}, "out_")


role = AgentRoleEntry(
    name="inside_classifier",
    inboxes=("in_",),
    outboxes=("out",),
    factory=_InsideClassifier,
)
```

**What to take from it.** Estimating π by Monte Carlo is the excuse; the real
subject is `save_state` / `load_state`, which is what lets the framework take
a consistent distributed snapshot and resume after a crash. Note the port
spelling asymmetry — `outboxes=["out_"]` in `Agent.__init__`, `outboxes=("out",)`
in `AgentRoleEntry`. Copy it; do not reason about it. Emitting nothing for a
message is fine: the outside branch simply does not call `send`. And `run()`
never returns — returning would kill the thread before the office finished
polling it, and termination detection would then block forever.

---

## 4. A loop with a gate — `debate`

**Shape:** three panellists → synchroniser → moderator → back to the
panellists, until they agree.
**Use when:** the work is iterative — argue, critique, revise — rather than a
one-way pipeline.

```
# Office: debate

Sources: starter
Sinks: jsonl_recorder(path="debate_answers.jsonl"),
       jsonl_recorder_briefing(path="debate_transcript.jsonl"),
       debate_display

Agents:
Sasha is a gate.
Qwen is a qwen.
Qwen's AI is openrouter.
GPT is a gpt.
GPT's AI is openai.
Claude is a claude.
Claude's AI is anthropic.
Sync is a synchronizer(inboxes=["from_qwen", "from_gpt", "from_claude"]).
Riley is a moderator.

Connections:
starter's destination is Sasha.

Sasha's out is Qwen, GPT, Claude.

Qwen's out is Sync's from_qwen.
GPT's out is Sync's from_gpt.
Claude's out is Sync's from_claude.

Sync's out is Riley, jsonl_recorder_briefing, debate_display.

Riley's continue is Qwen, GPT, Claude, debate_display.
Riley's finish is jsonl_recorder, Sasha, debate_display.
```

**What to take from it.** `starter` emits one message to kick the loop off.
The moderator has **two named outboxes** — `continue` sends another round,
`finish` ends it — which is how a role decides between branches. `Sasha` is
the `gate`: without something in the loop deciding when to stop, the office
runs forever, and `dsl check` will say so. Each panellist runs on a different
backend, which is the whole of what `X's AI is <backend>` buys you.

---

## Choosing a shape

| The user says | Start from |
|---|---|
| "one page each morning with X, Y and Z on it" | `periodic_brief` |
| "watch these feeds and tell me what matters" | `situation_room` |
| "compute something over a stream", "don't lose state if it crashes" | `recovery_demo` |
| "have them argue until they agree", "keep revising until good enough" | `debate` |
| "classify these photos / recordings / readings" | the `sensor-office-builder` skill |

`dsl list` shows every shipped office with a one-line description; there are
about thirty, and one of them is usually closer to the user's request than
anything you would write from scratch.
