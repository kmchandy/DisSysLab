# DisSysLab

[![PyPI](https://img.shields.io/pypi/v/dissyslab)](https://pypi.org/project/dissyslab/)
[![Python](https://img.shields.io/pypi/pyversions/dissyslab)](https://pypi.org/project/dissyslab/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Tests](https://github.com/kmchandy/DisSysLab/actions/workflows/test.yml/badge.svg)](https://github.com/kmchandy/DisSysLab/actions/workflows/test.yml)

**Build distributed systems of cooperating AI agents, and learn the
algorithms that keep them correct.**

DisSysLab runs **offices**: networks of agents that communicate only by
messages. Some agents are language models following instructions written
in English; others are a few lines of Python. Sources bring messages in
(news feeds, sensors, files), sinks write results out (the screen, files,
email), and one file, `office.md`, says who is connected to whom. The
library provides the hard parts of concurrency -- message passing,
termination detection, and reports of offices that stall -- so that an
office is short enough to read in a minute and check before it runs.

## What an office looks like

This one sorts the messages students send to a course's staff. An agent
reads each message, a language model decides how urgent it is, and a
router files it.

`office.md`:

```
# inbox_sorter: messages to the course staff, sorted by how soon they need an answer.

sources:
    inbox: file_source(path="messages.jsonl")

sinks:
    console_printer
    urgent: jsonl_recorder(path="urgent.jsonl")
    later: jsonl_recorder(path="later.jsonl")

agents:
    Tri: triage
    Rex: router(on="urgency")

connections:
    inbox -> Tri -> Rex
    Rex.urgent -> urgent, console_printer
    Rex.routine -> later
```

`roles/triage.md`, the instruction the model receives:

```
---
emits: how soon a message to the course staff needs an answer
in: subject, text
out: urgency (urgent | routine)
---
You read one message that a student sent to the staff of a course. It is
a JSON object; "subject" and "text" are the message.

Decide how soon it needs an answer. It is urgent if the student cannot
make progress on work that is due within a day without our help: a lost
assignment near a deadline, an install that fails before a due date.
Everything else is routine: questions about schedules, readings, grading
policy, or work due later.

Return only a JSON object with one field, "urgency", whose value is
"urgent" or "routine".
```

The `out:` line is a **guardrail**: a reply with any value other than
`urgent` or `routine` is reported and goes no further, and a field the
model adds without being asked is dropped. Before anything runs,
`dsl check` reports every problem by line -- a misspelt name, a port that
does not exist, a router outbox no message can reach:

```
dsl check .     every problem, without running anything
dsl draw .      the network, arrow by arrow (--mermaid for a picture)
dsl run .       run it; the summary says what failed or stalled
```

## Start here

**Students: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** takes
you from installing DisSysLab to building the office above, one checked
step at a time, with the output you should see at each step. Then:

- `dsl grammar` (and `dsl grammar roles`, `sources`, `examples`) is the
  reference, shipped with the code so that it matches your install.
- [dissyslab/gallery/](dissyslab/gallery/) holds ten offices, each
  teaching one idea, from a two-agent filter to a backtester with eleven
  trading strategies. `dsl list` shows them; `dsl init <office> <folder>`
  copies one to work on.

```bash
pip install dissyslab
dsl init returns_desk my_desk      # an office that needs no key
cd my_desk
dsl check .
dsl run .
```

## Building with an AI assistant

The [skills/](skills/) folder holds skills that teach an assistant
(Claude, Codex, Gemini CLI) to build offices with you: `office-builder`
for any office, `sensor-office-builder` for audio, images and sensor
readings, and `backtest-strategy-builder` for trading strategies. They
point the assistant at `dsl grammar` and `dsl check` rather than carrying
their own copy of the language, so they cannot teach a version you do not
have.

## Then study the algorithms underneath

A student builds something they care about, and then finds out what was
holding it up.

- **Termination detection.** How does an office know that no agent will
  ever send another message, when no agent can see the whole system? It
  does this every time it stops by itself.
- **Stall detection.** When an agent holds work it can never finish, the
  office follows the connections backwards from what it is waiting for --
  each one empty, each agent on the way idle -- until the path closes on
  itself or ends at a finished source, and prints that path as the proof.
- **Global snapshots.** The runtime implements the Chandy-Lamport
  snapshot algorithm; offices in this version do not use it yet.

The formal treatment behind the course is *Parallel Program Design: A
Foundation*, K. Mani Chandy and Jayadev Misra (Addison-Wesley, 1988).
Algorithm notes are in [docs/algorithms/](docs/algorithms/).

## What it does not do

- **One machine.** An office runs in one process, each agent in a
  thread: concurrency, not parallel speed.
- **Checks are not proofs.** `dsl check` finds structural mistakes and
  the guardrails catch replies that break a role's declared shape. They
  cannot tell you that an answer is wrong; build offices whose wrong
  answers are visible.
- **No web interface.** Offices write to the screen and to files.
- **Platforms.** Linux and macOS are supported and in CI. Windows runs
  and is in CI, with setup notes in [docs/WINDOWS.md](docs/WINDOWS.md).
- **Version 1 offices** (written as sentences, `Alex is a writer.`) do not
  run in this version. Version 1 is on the `v1` branch and the `v1.10.2`
  tag.

## Why I am building this

Sense-and-respond systems have belonged to large institutions for
decades. Militaries formalised them as the OODA loop; Stephan Haeckel
introduced "sense and respond" as a business methodology in 1992; in
2009 Roy Schulte and I published *Event Processing: Designing IT
Systems for Agile Companies* (Morgan Kaufmann). I worked on two
startups building such systems, and helped build earthquake-warning
and radiation-detection systems — see *Community Sense and Response
Systems: Your Phone as Quake Detector*, CACM, July 2014.

They belonged to institutions because only institutions had the
expertise and the compute. That is what has changed. A person can now
describe an office in plain English and lean on tested machinery for
the parts that are hard to get right.

I am using this to teach distributed algorithms to undergraduates,
first-year students included. The measure I hold it to is one
sentence: **a first-year builds an application they care about, and
then studies the algorithms underneath it.**

## Repository map

| Path | Contents |
|---|---|
| [skills/](skills/) | Skills an assistant loads to build offices |
| [course/](course/) | The course: setup, what you build, the catalogue, and `micro/` — short self-paced sittings |
| [docs/](docs/) | Reference: components, backends, algorithms, internals |
| [dissyslab/](dissyslab/) | The library and the gallery |
| [tests/](tests/) | The suite; CI runs it on Python 3.10–3.14 |
| [archive/](archive/) | Dated documents, kept but not maintained |

## Install from source

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
dsl doctor && pytest tests/ -q
```

Note the `[dev]`: a plain `pip install -e .` runs offices but omits
the test tools. Market-data offices need
`pip install "dissyslab[market]"`. For offices with language-model
agents, choose a backend and export its credentials — see
[docs/API_KEY_SETUP.md](docs/API_KEY_SETUP.md) and
[docs/LANGUAGE_MODELS.md](docs/LANGUAGE_MODELS.md).

## License

MIT; see [LICENSE](LICENSE).
