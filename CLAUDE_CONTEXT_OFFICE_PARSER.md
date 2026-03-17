# DisSysLab — Office Parser

## What an Office Is

An office is a specific organization built from roles. It specifies:
- Which sources provide data
- Which sinks consume data
- Which agents exist and what roles they play
- How agents connect to each other

The office spec is written in plain English following a loose template.
It has no knowledge of what roles do internally — only who connects to whom.

---

## Office Spec Template

```
# Office: office_name

Sources: source_name(max_articles=N), source_name(max_articles=N)
Sinks: sink_name, sink_name(arg=value)

Agents:
[agent_name] is a [role_name].
[agent_name] is a [role_name].

Connections:
[source]'s destination is [agent].
[agent]'s [channel] is [agent_or_sink].
[agent]'s [channel] are [agent] and [agent].
```

**Connection rules:**

1. One pattern covers all connections: `X's Y is Z.` or `X's Y are Z and Z'.`
   - X is a source, agent, or sink
   - Y is a channel name (or "destination" for sources)
   - Z is an agent or sink

2. Sources use the channel name "destination".

3. Fanout — one channel to multiple destinations — uses the plural form
   and lists all destinations:
   `Susan's archivist are jsonl_recorder and console_printer.`

4. Fanin — multiple agents feeding one agent — is multiple connection lines
   with the same destination:
   ```
   al_jazeera's destination is Susan.
   bbc_world's destination is Susan.
   ```

5. Feedback loops are just connections back to an earlier agent:
   `Anna's client is Susan.`

6. Channel names in connections must match channel names declared in the
   role description. The compiler normalizes plural to singular
   (copywriters → copywriter).

---

## Available Sources

```
al_jazeera(max_articles=N)
bbc_world(max_articles=N)
bbc_tech(max_articles=N)
npr_news(max_articles=N)
hacker_news(max_articles=N)
techcrunch(max_articles=N)
mit_tech_review(max_articles=N)
venturebeat_ai(max_articles=N)
nasa_news(max_articles=N)
python_jobs(max_articles=N)
```

## Available Sinks

```
jsonl_recorder(path="filename.jsonl")   # saves to file
console_printer                          # prints to screen
```

---

## Office Parser Prompt

Use this prompt to extract structured JSON from an office spec.

```
You are a compiler that reads an office spec and extracts
structured information.

An office spec follows this template:
- Office name: "# Office: office_name"
- Sources line: "Sources: source_name(arg=val), ..."
- Sinks line: "Sinks: sink_name, sink_name(arg=val)"
- Agents section: "[agent_name] is a [role_name]." one per line
- Connections section: "[source]'s destination is [agent]."
  or "[agent]'s [channel] is [agent_or_sink]."
  or "[agent]'s [channel] are [agent] and [agent]."

For each connection extract:
- from: the sender name
- port: the channel name (singular form)
- to: list of destination names

Return JSON only, no explanation, no nested JSON:
{
  "office_name": "name from # Office: heading",
  "sources": [
    {"name": "source_name", "args": {"arg": value}}
  ],
  "sinks": [
    {"name": "sink_name", "args": {"arg": value}}
  ],
  "agents": [
    {"name": "agent_name", "role": "role_name"}
  ],
  "connections": [
    {"from": "name", "port": "channel", "to": ["name"]}
  ]
}
```

---

## Example Input

```
# Office: news_editorial

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: jsonl_recorder(path="editorial_output.jsonl"), console_printer

Agents:
Susan is an editor.
Anna is a writer.

Connections:
al_jazeera's destination is Susan.
bbc_world's destination is Susan.
npr_news's destination is Susan.
Susan's copywriter is Anna.
Susan's archivist are jsonl_recorder and console_printer.
Anna's client is Susan.
```

## Example Output

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

---

## Confirmation Conversation

After parsing both roles.md and office.md, show the user:

**1. Agent list with roles and channels:**
```
Agents:
  Susan  —  editor  (sends to: copywriter, archivist)
  Anna   —  writer  (sends to: client)
```

**2. Routing table with line number citations:**
```
Routing:
  al_jazeera   →  Susan                              (office.md line 9)
  bbc_world    →  Susan                              (office.md line 10)
  npr_news     →  Susan                              (office.md line 11)
  Susan        [copywriter]  →  Anna                 (office.md line 12)
  Susan        [archivist]   →  jsonl_recorder       (office.md line 13)
  Susan        [archivist]   →  console_printer      (office.md line 13)
  Anna         [client]      →  Susan                (office.md line 14)
```

**3. Ask for confirmation:**
```
Does this look right?
```

Iterate until the user confirms. Only then proceed to code generation.

**If a channel name in connections does not match any channel declared
in the role, flag it:**
```
  Warning: Susan's role (editor) declares channels [copywriter, archivist]
  but office.md line 12 references channel "rewriter" which is not declared.
  Did you mean "copywriter"?
```
