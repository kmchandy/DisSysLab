
# DisSysLab — Building Organizations

## What This Is

DisSysLab lets you build multi-agent distributed systems by describing
an organization in plain English. You write two files:

- **`roles.md`** — reusable job descriptions for each type of agent
- **`office.md`** — this specific organization: who the agents are and how they connect

Then run one command:

```bash
python3 office_compiler.py roles.md office.md
```

A complete runnable distributed system is generated. No coding required.

---

## The Three Concepts

**Role** — a reusable job description. Defines what an agent does and
what output channels it sends to. Written once, reused in many offices.
Port names come from "send to X" phrases in the description.

**Agent** — a named instance of a role. Susan is an editor. Anna is a writer.
Two agents can have the same role and run concurrently.

**Office** — the network. Specifies which agents exist and how their
channels connect to other agents and sinks.

---

## Quick Example

**roles.md:**
```
# Role: editor

You are an editor who receives news articles and sends
articles to a copywriter and to an archivist.

The article has a section called "rewrites" whose value
is a number. If absent, treat as 0.

Your job is to analyze the sentiment of each article
and score it from 0.0 (most negative) to 1.0 (most positive).

If the score is less than 0.25 or greater than 0.75,
send the article to the archivist.
If the score is between 0.25 and 0.75 and rewrites < 3,
send the article to the copywriter and modify rewrites by adding 1.
If the score is between 0.25 and 0.75 and rewrites >= 3,
send the article to the archivist.


# Role: writer

You are a writer who receives news articles and sends
articles to a client.

Your job is to rewrite the article to be more strongly
opinionated. Preserve all fields from the input message.
```

**office.md:**
```
# Office: news_editorial

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5)
Sinks: jsonl_recorder(path="output.jsonl"), console_printer

Agents:
Susan is an editor.
Anna is a writer.

Connections:
al_jazeera's destination is Susan.
bbc_world's destination is Susan.
Susan's copywriter is Anna.
Susan's archivist are jsonl_recorder and console_printer.
Anna's client is Susan.
```

**Run:**
```bash
python3 office_compiler.py roles.md office.md
```

---

## What the Compiler Does

1. Reads `roles.md` — extracts role names, channels, persistent state,
   routing rules for each role
2. Reads `office.md` — extracts agents, sources, sinks, connections
3. Shows you the routing table with line number citations and asks
   "Does this look right?"
4. Iterates until you confirm
5. Generates `app.py` and `test_app.py`
6. Runs structural tests and reports pass/fail

---

## Supported Network Patterns

**Fanin** — multiple sources feeding one agent:
```
al_jazeera's destination is Susan.
bbc_world's destination is Susan.
npr_news's destination is Susan.
```

**Fanout** — one channel to multiple destinations:
```
Susan's archivist are jsonl_recorder and console_printer.
```

**Feedback loop** — agent sends back to an earlier agent:
```
Anna's client is Susan.
```

**Multiple agents with same role** — two editors running concurrently:
```
Agents:
Susan is an editor.
Beth is an editor.
```

---

## Detailed Documentation

- **Role descriptions:** `CLAUDE_CONTEXT_ROLE_PARSER.md`
- **Office specs:** `CLAUDE_CONTEXT_OFFICE_PARSER.md`
- **Code generation:** `CLAUDE_CONTEXT_CODE_GENERATOR.md`

---

## Directory Structure

```
DisSysLab/
├── office_compiler.py              ← the compiler
├── CLAUDE_CONTEXT_OFFICE.md        ← this file
├── CLAUDE_CONTEXT_ROLE_PARSER.md   ← role template + parser prompt
├── CLAUDE_CONTEXT_OFFICE_PARSER.md ← office spec template + parser prompt
├── CLAUDE_CONTEXT_CODE_GENERATOR.md← code generation rules
└── gallery/
    └── org_news_editorial/
        ├── __init__.py
        ├── roles.md                ← you write this
        ├── office.md               ← you write this
        ├── app.py                  ← generated
        ├── test_app.py             ← generated
        └── README.md
```