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
Eve is summarizer.
Sasha is a deduplicator(by="url").
Sync is a synchronizer(inboxes=["entities", "severity", "topic"]).
news_monitor is an office at ../news_monitor.
Jay is unassigned.
```

**Exactly three forms, and nothing else parses:**

| Form | Means |
|---|---|
| `<Name> is a[n] <role>.` | a library role, `roles/<role>.md`, or `roles/<role>.py` |
| `<Name> is an office at <path>.` | a nested office |
| `<Name> is unassigned.` | the job is not decided yet |

- **The article is optional.** `Eve is summarizer.` and `Eve is a
  summarizer.` are the same line. It used to be the only thing separating a
  role from a sub-office, which is not a distinction anyone means to draw
  with one character; `office at` is what marks a sub-office now, two words
  that say what they mean.
- A line matching none of the three is a **parse error naming all three**,
  rather than a silent reinterpretation. Three outcomes for one dropped
  article, chosen by which library the name happened to belong to, is what
  this replaced.
- Arguments in parentheses, same as sources.
- Plural agreement is accepted: `Susan and Anna are editors.`
- `<Name>` is the agent's local identity; `<role>` is the job.

### An office you have not finished

`Jay is unassigned.` is how you write down an agent whose job the user has
not said yet. An office holding one is a **draft**, and that changes what
the report means rather than what it says: the incompleteness findings are
listed as *"still to do"*, and `dsl check` exits 0.

```
check_wiring: office.md -- draft, 2 things still to do

  still to do   nothing reaches Jay yet.
  still to do   'Jay' has no job yet.
```

`dsl run` and `dsl build` refuse a draft, naming the agents whose job is
undecided.

**Use this rather than inventing a job.** When someone says *"give me an
office with Dan and Jay"* they have told you two names and nothing else.
Write the two names down and wait. An unfinished office is not a broken
one, and reporting it as broken teaches a beginner that building is a
sequence of errors.

**Say back what you wrote, then invite the next sentence.** Two lines:

> The office has an agent called Dan with an unassigned role, and an agent
> called Jay with an unassigned role. Tell me more about the office.

Not a list of everything missing. The gaps are real and `dsl check` prints
them on request, but reciting them here turns a first sentence into a
report card, and a beginner reads a five-item list of what is absent as
five things they got wrong. One sentence of what exists, one invitation to
continue.

Also not a menu. A model asked something underspecified will offer options
unless it is told not to — *"would you like Dan to be a filter, a router, a
summarizer…"* is the default behaviour, and it is wrong here. The user
knows what she is building; she has not said it yet.

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
cannot see faults that depend on what happens at run time — an office whose
diagram is correct can still deadlock, because whether a message is ever
readable can depend on execution history rather than on the graph.

### W11 — free text reaching something that acts

One finding is not about structure but about consequence, and it is a
**note**, so the check still passes:

```
W11  note:text from web_scraper can reach gmail_sink -- which sends email.
```

An agent whose job is English is run by a language model, and a model that
can be instructed can be instructed by its input. When that input was
fetched from the open web, a stranger chose the words. No wording of the
role file closes that; what bounds it is the other end, because an office
affects the world only through its sinks.

So when this fires, **say what it means and let the user decide** — do not
quietly rewire, and do not treat it as an error:

> *This office can send whatever a scraped page says out by email. If that
> is what you want, nothing to do. If not, I can have the last agent send
> only a score and a link rather than text it wrote.*

An office whose sinks all print or write a local file never fires it.

## The other subcommands worth knowing

```
dsl draw <office_dir>          the network as a Mermaid diagram
dsl roles                      every built-in role and the field it adds
dsl skills                     which DisSysLab skills are installed
dsl fetch-prices --office DIR  download your own price history
```

**`dsl draw` when the wiring stops being readable as text**, which happens
at the first branch or fan-in — or when the user asks to see it. It is on
request, never automatic: a diagram redrawn after every edit has to stay
stable under change, or adding one agent moves the ones the reader had
already understood. It draws an office that does not compile, too, since
that is when a picture is worth most. `--out FILE` writes to a file;
`--raw` omits the ```mermaid fence.

**`dsl skills` before telling anyone what is installed.** A skill that never
loaded is one you cannot see, and you will answer anyway.

**`dsl fetch-prices` for any office with a `csv_stock_history` source.** It
takes the basket from the office's own source line, skips files already
downloaded, and finishes by loading each ticker back through the office to
confirm it can read what was just written. Nothing in this project ships
market data — the vendor's terms do not permit redistributing it — so this
is a deliberate act by each user, and `yfinance` lives in the `[market]`
extra for the same reason.
