# Office Compiler — Two-Week Demo Plan

## What the demo shows

A user writes plain English files — one office spec and one role file per role.
Runs one command. A distributed multi-agent system starts processing live
news articles. No code written by the user.

---

## The files the user writes

**roles/editor.md** — job description for the editor role
**roles/writer.md** — job description for the writer role
**office.md** — this specific organization

**One command:**
```bash
python3 office_compiler.py gallery/org_news_editorial/
```

**Output:** `app.py` + `test_app.py` — complete runnable DisSysLab app.

---

## Week 1: Build the Compiler

### Day 1-2: Role Parser

Write a prompt that reads one role file and extracts structured JSON.
The parser only needs two things:

```json
{
  "role_name": "editor",
  "sends_to": ["copywriter", "archivist"]
}
```

`role_name` comes from the `# Role:` heading or the opening sentence.
`sends_to` is inferred from anywhere in the description where a message
is explicitly sent to a named destination. Only include a destination
if it is explicitly stated.

The role logic (job description, routing rules, persistent state) passes
through unchanged to `ai_agent` at runtime. The compiler appends the
JSON contract (valid `send_to` values) at code generation time.

**Test on:** editor role and writer role.
**Success criterion:** extraction correct on both roles, no manual fixes needed.

### Day 3-4: Office Parser

Write a prompt that reads `office.md` and extracts structured JSON:

```json
{
  "office_name": "news_editorial",
  "sources": [
    {"name": "al_jazeera", "args": {"max_articles": 5}},
    {"name": "bbc_world",  "args": {"max_articles": 5}},
    {"name": "npr_news",   "args": {"max_articles": 5}}
  ],
  "sinks": [
    {"name": "jsonl_recorder", "args": {"path": "editorial_output.jsonl"}},
    {"name": "console_printer", "args": {}}
  ],
  "agents": [
    {"name": "Susan", "role": "editor"},
    {"name": "Anna",  "role": "writer"}
  ],
  "connections": [
    {"from": "al_jazeera", "port": "destination", "to": ["Susan"]},
    {"from": "bbc_world",  "port": "destination", "to": ["Susan"]},
    {"from": "npr_news",   "port": "destination", "to": ["Susan"]},
    {"from": "Susan", "port": "copywriter", "to": ["Anna"]},
    {"from": "Susan", "port": "archivist",  "to": ["jsonl_recorder", "console_printer"]},
    {"from": "Anna",  "port": "client",     "to": ["Susan"]}
  ]
}
```

Validate:
- Every agent's role exists in the role library
- Every port name in connections matches a name in `sends_to` for that role
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
  al_jazeera   →  Susan                              (office.md line 9)
  bbc_world    →  Susan                              (office.md line 10)
  npr_news     →  Susan                              (office.md line 11)
  Susan        [copywriter]  →  Anna                 (office.md line 12)
  Susan        [archivist]   →  jsonl_recorder       (office.md line 13)
  Susan        [archivist]   →  console_printer      (office.md line 13)
  Anna         [client]      →  Susan                (office.md line 14)

Does this look right?
```

Iterate until user confirms. Then proceed to code generation.

---

## Week 2: Code Generator, Tests, README

### Day 1-2: Code Generator

From confirmed JSON generate complete `app.py`:

- One role function per role using `ai_agent(prompt)`
- Prompt = role file contents verbatim + JSON contract appended by compiler
- JSON contract specifies valid `send_to` values for that role
- One Role node per agent instance, named after the agent (Susan, Anna)
- Port indices follow order of `sends_to`: index 0 = first destination, index 1 = second, etc.
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
- Verify fanin works (three sources all reach Susan)
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

You are a [job title] who receives one message and responds
by sending zero or more messages, each addressed to a destination role.

The messages you receive and send are either plain text or a document
partitioned into sections, each with a section header and a section body.
Treat a document as JSON with each section header as a key and the
section body as the corresponding value. Section headers are unique.

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
[agent]'s [destination_role] is [agent_or_sink].
[agent]'s [destination_role] are [agent] and [agent].
```

### Connection Pattern (one pattern covers everything)

- `X's Y is Z.` — single destination
- `X's Y are Z and Z'.` — fanout to multiple destinations

Sources use port name "destination".
All other port names come from destination role names in the role description.
Compiler normalizes plural to singular (copywriters → copywriter).

---

## Directory Structure

```
DisSysLab/
├── office_compiler.py              ← the compiler (root level)
├── gallery/
│   └── org_news_editorial/         ← the demo app
│       ├── __init__.py
│       ├── office.md               ← user writes this
│       ├── roles/
│       │   ├── editor.md           ← copied from central library
│       │   └── writer.md           ← copied from central library
│       ├── app.py                  ← generated by compiler
│       ├── test_app.py             ← generated by compiler
│       └── README.md               ← written in Week 2 Day 5
```

Roles are self-contained files copied from a central library as needed.
The office directory is fully self-contained — no runtime dependency
on the central library.

---

## Success Criteria for the Demo

1. User writes `office.md` and role files — no Python, no YAML, no framework concepts
2. `python3 office_compiler.py gallery/org_news_editorial/` runs without errors
3. Compiler shows routing table with line number citations
4. User types "looks good"
5. `app.py` is generated and runs
6. Live news articles flow through the network
7. Feedback loop terminates correctly after 3 rewrites
8. Results appear in `output.jsonl` and console
