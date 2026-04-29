# How to write a custom role

**Goal.** Define a new kind of agent — a translator, a summarizer,
a tagger, a fact-checker, a sentiment scorer — by writing a short
job description in plain English. Once a role exists, you can
assign it to as many agents as you want.

A **role** is a job description for an agent. It lives in a single
file at `roles/<role>.md`. The file is read by the LLM that runs
inside the agent: it is the agent's job description and nothing
else.

## Run a working example

Start by looking at the simplest role in the gallery:

```bash
dsl init my_first_office my_office
cd my_office
cat roles/analyst.md
```

You'll see four lines:

```
# Role: analyst

You are a Hacker News analyst. For each story you receive, write
one crisp sentence describing what it's about and why someone
learning software might care.

Send to briefing.
```

That's a complete, valid role. Run the office and Alex (the
agent assigned this role) goes to work:

```bash
dsl run .
```

## Anatomy of a role file

Every role file has the same three pieces:

```
# Role: <role-name>          ← header (must match the filename)

<Identity sentence.>          ← who the agent is
<Job description.>            ← what the agent does to each message

Send to <mailbox-name>.       ← which mailbox the result goes to
```

**The header** declares the role name. The filename
`roles/analyst.md` and the header `# Role: analyst` must match.
The `office.md` then assigns this role to one or more agents:
`Alex is an analyst.`

**The identity sentence** sets the LLM's voice. *"You are a Hacker
News analyst"* puts the model in a different frame than *"You are
a copy editor"* or *"You are a Spanish-to-English translator"*.

**The job description** is the heart of the role. It says what the
agent does to each incoming message. Be specific: "rewrite each
article as one paragraph beginning with a significance rating" is
better than "summarize the article".

**The send instruction** names the mailbox. The mailbox is just a
label — it could be `briefing`, `output`, `keep`, `summary`,
anything. What matters is that the same name appears in
`office.md` under `Connections:`:

```
Alex's briefing is console_printer.
```

The mailbox `briefing` is wired from Alex to a sink. Change the
mailbox name in the role file and you have to change it in the
org chart too — they have to match.

## A role with multiple mailboxes

A role can route messages to different destinations based on
conditions. Here is the filter role from `org_news_filter`:

```
# Role: filter

You are a content filter who receives news articles and sends
articles to a keeper or a discard.

Your job is to decide if each article is about the americas:
canada, usa, brazil, ..

If the article is about the americas, send to keeper.
Otherwise send to discard.
```

The role names two mailboxes: `keeper` and `discard`. The job
description spells out the condition for each. The org chart
wires each mailbox somewhere:

```
Felix's keeper is console_printer.
Felix's discard is jsonl_recorder.
```

The same agent now has two outputs. The LLM picks one per
incoming message based on the criteria you wrote.

## Writing a brand-new role from scratch

Suppose you want a **summarizer** that takes any article and
writes a one-line summary. Two files do it.

`roles/summarizer.md`:

```
# Role: summarizer

You are a concise summarizer. For each message you receive, write
a single sentence (no more than 20 words) that captures the
central point. Put the summary in a "summary" field. Preserve
the source, title, url, and timestamp fields unchanged.

Always send to output.
```

`office.md`:

```
# Office: summary_office

Sources: bbc_world(max_articles=5)
Sinks: console_printer

Agents:
Sam is a summarizer.

Connections:
bbc_world's destination is Sam.
Sam's output is console_printer.
```

That's a complete office. Run it with `dsl run .`.

## The pattern, in a sentence

A role is a plain-English job description in `roles/<role>.md`. It
declares an identity, the job, and the mailboxes the agent sends
to. The org chart in `office.md` assigns roles to agents and
connects each mailbox to a downstream agent or sink.

## Variations

**Many agents, one role.** A role is defined once and assigned to
as many agents as you want:

```
Agents:
Alex is a summarizer.
Morgan is a summarizer.
Riley is a summarizer.
```

Three agents now run independently, each with the same job
description but in their own thread. Useful when one agent isn't
keeping up with the message rate.

**One agent, many roles?** No — an agent has exactly one role.
If you want an agent to do two jobs, write a role whose job
description covers both, or split the work across two agents
chained together.

**Add structured output.** Roles whose job description asks for
specific JSON-style fields ("Add a 'significance' field with values
CRITICAL, HIGH, MEDIUM, or LOW") tend to behave more reliably than
free-form prose. Downstream agents can then key off those fields
in their own job descriptions.

**Borrow from the gallery.** Every gallery office has its role
files in `roles/`. Reading them is the fastest way to pick up the
house style:

- [`analyst` in `my_first_office`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/my_first_office/roles/analyst.md)
  — a one-mailbox role.
- [`filter` in `org_news_filter`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/org_news_filter/roles/filter.md)
  — two mailboxes, conditional routing.
- [`analyst` in `org_intelligence_briefing`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/org_intelligence_briefing/roles/analyst.md)
  and [`editor`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/org_intelligence_briefing/roles/editor.md)
  — two roles in one office, one feeding the other.

## Tips for writing good job descriptions

- **Be specific about the output.** "Write one sentence in 20
  words or fewer" beats "summarize briefly".
- **Name the mailboxes the agent sends to.** Use the same names
  in the role file and in `office.md`'s `Connections:`.
- **Spell out every routing condition.** "If X, send to A.
  Otherwise send to B." If a message could go nowhere, the
  pipeline stalls.
- **Preserve fields you'll need later.** When a role adds new
  fields (e.g. `significance`, `topic`), say "preserve the
  source, url, and title fields" — otherwise the model may drop
  them.
- **Keep the role short.** A few paragraphs is plenty. Long role
  files behave less reliably than focused ones.

## See also

- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — every shipped sink an agent can route a mailbox to.
- [How to filter for a topic](filter-for-a-topic.md) — a focused
  example of a two-mailbox role.
- [How to chain offices](chain-offices.md) — once you have a
  collection of roles, group them into offices and wire offices
  together.
- [How to send messages to the outside world](send-messages-outside.md)
  — once a role produces good output, route it to a file, the
  terminal, your inbox, or a chat channel.
