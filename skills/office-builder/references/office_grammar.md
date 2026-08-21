# office.md — the grammar

Up to seven sections, in any order. Section headers are case-insensitive.

| Section | Required | What goes there |
|---|---|---|
| `# Office: <name>` | yes | The office's identifier |
| `Sources:` | usually | One declaration per world-facing input |
| `Sinks:` | usually | One declaration per world-facing output |
| `Agents:` | no | One line per worker |
| `Connections:` | yes | One line per connection statement |
| `Inputs:` | no | External inboxes — only for an office meant to sit inside another |
| `Outputs:` | no | External outboxes — same |

An office with no `Agents:` section is legal. `periodic_brief` is six sources
fanning straight into one sink.

## Sources and Sinks

Comma-separated, arguments in parentheses, may wrap across lines:

```
Sources: bbc_world(max_articles=5), npr_news(max_articles=5),
         weather(city="Pasadena", max_readings=1)
Sinks:   intelligence_display,
         jsonl_recorder_briefing(path="briefings.jsonl")
```

Names must come from the registries — see `sources_and_sinks.md`. Arguments
are forwarded to the component's constructor.

**Keep `max_articles=N` and `max_readings=N` in place.** They are what stops a
shipped office from running forever and billing a student's API key. Remove
only when the user asks for continuous operation.

## Agents

```
Agents:
Felix is a filter.
Alex is an analyst.
Sasha is a deduplicator(by="url").
Sync is a synchronizer(inboxes=["entities", "severity", "topic"]).
news_monitor is an office at ../news_monitor.
```

- `<Name> is a[n] <role>.` — `a` and `an` are interchangeable.
- `<Name> is an office at <path>.` — a sub-office. Offices nest; the
  surrounding network sees only its ports.
- Arguments in parentheses, same as sources.
- Plural agreement is accepted: `Susan and Anna are editors.`
- `<Name>` is the agent's local identity; `<role>` is the job, and resolves to
  `roles/<role>.md`, `roles/<role>.py`, or a library role.

### Per-agent model backend

```
Eve is an entity_extractor.
Eve's AI is ollama.          # local, free — fine for extraction
Riley is a writer.
Riley's AI is claude.        # high quality for the final synthesis
```

Backends: `anthropic` (alias `claude`), `openai` (alias `gpt`), `gemini`,
`openrouter`, `ollama`, each with `_creative` and `_precise` variants. Those
lines are the whole difference between a uniformly expensive office and a
tiered one. Only English roles use a backend; Python roles ignore it.

## Connections

The form is `<Name>'s <port> is <recipient(s)>.` — `is` and `are` both parse.

```
Connections:
hacker_news's destination is Felix.
Felix's keep is Alex.
Felix's discard is discard.
Alex's briefing is console_printer.
```

**Fan-out** — one statement, several recipients, commas and/or `and`:

```
Felix's keep is Alex, Morgan and discard.
```

**Into a named inbox** — `<Recipient>'s <port>`:

```
Eve's out is Sync's entities.
Sam's out is Sync's severity.
```

**Between sub-offices** — the recipient names a port on the sub-office:

```
hacker_news's destination is news_monitor's article_in.
news_monitor's article_out is news_editor's article_in.
```

### Port-name rules worth memorising

- A source's outbox may be written `destination` **or** `out`. Both legal;
  the compiler maps either to the same runtime port.
- A sink has exactly one inbox and it is always `in_`. You never name it.
- An agent's outboxes are whatever its role declares. A role can have several
  — `Felix's keep` and `Felix's discard`, or `Riley's continue` and
  `Riley's finish`.
- A synchronizer's inboxes are either declared —
  `synchronizer(inboxes=["a","b"])` — or inferred from what gets wired to it.
  **If you declare them, wire every one.** A declared inbox nothing writes to
  is an agent that blocks forever.

## Cycles

The network **may contain cycles**, and this is a feature, not an oversight —
it is why end-of-stream sentinels are not enough and real termination
detection is needed. A loop should contain a `gate`, which is what decides
when to stop. `debate` loops three panellists through a moderator and back
until they agree, gated by `Sasha`.

## Blank lines and comments

Blank lines inside a section are ignored — use them to group related
connections, as the gallery offices do. `#` outside the header line is not a
comment; put explanation in the office's `README.md` instead.

## Checking it

```
dsl check <office_dir>
```

Reports every structural fault at once. Run it before every `dsl run`. It
cannot see faults that depend on what happens at run time.
