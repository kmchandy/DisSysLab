# Office Compiler — Two-Week Demo Plan

## What the demo shows

A user writes two plain English files — a role library and an office spec.
Runs one command. A distributed multi-agent system starts processing live
news articles. No code written by the user.

---

## The files the user writes

**roles.md** — reusable job descriptions
**office.md** — this specific organization

**One command:**
```bash
python3 office_compiler.py roles.md office.md
```

**Output:** `app.py` + `test_app.py` — complete runnable DisSysLab app.

---

## Week 1: Build the Compiler

### Day 1-2: Role Parser

Write a prompt that reads a role description following the frozen template
and extracts structured JSON:

```json
{
  "role_name": "editor",
  "receives": "news articles",
  "sends_to": ["copywriter", "archivist"],
  "persistent_state": [
    {"field": "rewrites", "type": "number", "default": 0}
  ],
  "job": "analyze sentiment and score from 0.0 to 1.0",
  "routing_rules": [
    {"condition": "score < 0.25 or score > 0.75", "send_to": ["archivist"]},
    {"condition": "0.25 <= score <= 0.75 and rewrites < 3",
     "send_to": ["copywriter"], "increment": "rewrites"},
    {"condition": "0.25 <= score <= 0.75 and rewrites >= 3",
     "send_to": ["archivist"]}
  ]
}
```

**Test on:** editor role and writer role.
**Success criterion:** extraction is correct on both roles, no manual fixes needed.

### Day 3-4: Office Parser

Write a prompt that reads an office spec and extracts structured JSON:

```json
{
  "office_name": "news_editorial",
  "sources": [
    {"name": "al_jazeera", "args": {"max_articles": 5}},
    {"name": "bbc_world",  "args": {"max_articles": 5}}
  ],
  "sinks": [
    {"name": "jsonl_recorder", "args": {"path": "output.jsonl"}},
    {"name": "console_printer", "args": {}}
  ],
  "agents": [
    {"name": "Susan", "role": "editor"},
    {"name": "Anna",  "role": "writer"}
  ],
  "connections": [
    {"from": "al_jazeera", "port": "destination", "to": ["Susan"]},
    {"from": "bbc_world",  "port": "destination", "to": ["Susan"]},
    {"from": "Susan", "port": "copywriter", "to": ["Anna"]},
    {"from": "Susan", "port": "archivist",  "to": ["jsonl_recorder", "console_printer"]},
    {"from": "Anna",  "port": "client",     "to": ["Susan"]}
  ]
}
```

Validate:
- Every agent's role exists in the role library
- Every port name in connections matches a channel declared in the role
- Every destination is a known agent or sink

**Test on:** news_editorial office spec.
**Success criterion:** extraction correct, validation catches errors.

### Day 5: Confirmation Conversation

Show the user two things and iterate until confirmed:

```
Agents:
  Susan  —  editor  (sends to: copywriter, archivist)
  Anna   —  writer  (sends to: client)

Routing:
  al_jazeera   →  Susan                     (office.md line 9)
  bbc_world    →  Susan                     (office.md line 10)
  Susan        [copywriter]  →  Anna        (office.md line 11)
  Susan        [archivist]   →  jsonl_recorder, console_printer
                                            (office.md line 12)
  Anna         [client]      →  Susan       (office.md line 13)

Does this look right?
```

Iterate until user confirms. Then proceed to code generation.

---

## Week 2: Code Generator, Tests, README

### Day 1-2: Code Generator

From confirmed JSON generate complete `app.py`:

- One Role function per role using `ai_agent(prompt)`
- System prompt constructed from role description + routing rules + state declarations
- One Role node per agent instance
- `network([...])` call using `.out_N` port syntax
- Correct fanout wiring (one port to multiple destinations)
- `if __name__ == "__main__":` guard

Also generate `test_app.py`:
- Structural tests (no API key needed)
- Import path uses full dotted module path
- Live tests skipped unless ANTHROPIC_API_KEY is set

Run structural tests automatically. Report pass/fail in plain English.

### Day 3-4: End-to-End Test

Run the news_editorial office on live news articles:
- Verify fanin works (al_jazeera + bbc_world both reach Susan)
- Verify feedback loop works (Anna sends back to Susan)
- Verify fanout works (Susan's archivist reaches both sinks)
- Verify rewrite counter increments correctly
- Verify exhausted articles reach sinks after 3 rewrites
- Fix any bugs

### Day 5: README

Write `gallery/org_news_editorial/README.md`:

1. What this demo shows
2. The role template — how to write a job description
3. The office spec template — how to describe an organization  
4. How to run the compiler
5. What you see when it runs
6. How to write your own roles and office

---

## Frozen Templates (for reference)

### Role Template

```
# Role: role_name

You are a [job title] who receives [input] and sends
[output] to a [role1] and to a [role2].

The [message] has a section called "[field]" whose value
is a [type]. If absent, treat as [default].

Your job is to [task].

If [condition], send to [role1].
If [condition], send to [role2] and increment [field] by 1.
```

### Office Spec Template

```
# Office: office_name

Sources: source_name(max_articles=N), source_name(max_articles=N)
Sinks: sink_name, sink_name(arg=value)

Agents:
[agent_name] is a [role_name].
[agent_name] is a [role_name].

Connections:
[source]'s destination is [agent].
[agent]'s [role] is [agent_or_sink].
[agent]'s [role] are [agent] and [agent].
```

### Connection Pattern (one pattern covers everything)

- `X's Y is Z.`   — single destination
- `X's Y are Z and Z'.` — fanout to multiple destinations

Sources use port name "destination".
All other port names come from "send to X" phrases in the role description.
Compiler normalizes plural to singular (copywriters → copywriter).

---

## Directory Structure

```
DisSysLab/
├── office_compiler.py          ← new: the compiler (root level)
├── gallery/
│   └── org_news_editorial/     ← new: the demo app
│       ├── __init__.py
│       ├── roles.md            ← user writes this
│       ├── office.md           ← user writes this
│       ├── app.py              ← generated by compiler
│       ├── test_app.py         ← generated by compiler
│       └── README.md           ← written in Week 2 Day 5
```

The role library lives alongside the office spec for now.
In a future version roles.md moves to a shared library location.

---

## Success Criteria for the Demo

1. User writes `roles.md` and `office.md` — no Python, no YAML, no framework concepts
2. `python3 office_compiler.py roles.md office.md` runs without errors
3. Compiler shows routing table with line number citations
4. User types "looks good"
5. `app.py` is generated and runs
6. Live news articles flow through the network
7. Feedback loop terminates correctly after 3 rewrites
8. Results appear in `output.jsonl` and console
