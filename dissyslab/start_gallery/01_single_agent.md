# start_gallery example — single agent, no coordinator

The simplest possible office: one source, one agent, one sink. No
fan-out, no merge, no coordinator of any kind. This is the shape a
`dsl new` conversation should reach for whenever Pat's ask has exactly
one thing watching, one thing deciding, and one place results go.

## Pat's description

"Make an office with a source that gets stories from Hacker News, an
agent that writes one sentence about each story, and a sink that
shows me the results."

Note the register: Pat is already naming source/agent/sink, even
though loosely. That's DSL Pat-speak, not OfficeSpeak Pat-speak — in
OfficeSpeak, Pat would say "I want something that watches Hacker News
and tells me, in one sentence, what each new story is about and why
I'd care," and never mention a source, an agent, or a sink at all.
DSL's job is to take Pat's own (possibly incomplete or ambiguous)
office-shaped sketch to a correct, unambiguous one; OfficeSpeak's job
is to invent the office-shaped structure from a goal she never
describes in those terms. This example is too small to show the
"incomplete or ambiguous, resolved through iteration" half of that —
there's barely anything here to disambiguate. See the note in
`README.md` about a planned richer example for that.

## The office

```office.md
# Office: my_first_office

Sources: hacker_news(max_articles=10, poll_interval=600)
Sinks: console_printer

Agents:
Alex is an analyst.

Connections:
hacker_news's destination is Alex.
Alex's briefing is console_printer.
```

```roles/analyst.md
# Role: analyst

You are a Hacker News analyst. For each story you receive, write
one crisp sentence describing what it's about and why someone
learning software might care.

Send to briefing.
```

## Explanation for Pat

Every ten minutes, Hacker News is checked for up to ten new stories.
Each story goes straight to Alex, who reads it and writes one
sentence about it. That sentence prints to your screen. There's
nothing else in this office — no memory of past stories, no waiting
for more than one thing at a time, no decision about where a result
should go. One story in, one sentence out, every time.

## Source

Distilled from `gallery/examples/my_first_office`. See that folder's
`README.md` for the full "make it yours" walkthrough (swap the source,
add a second source, run without recompiling) — not repeated here
since this file's job is the pattern, not the tutorial.
