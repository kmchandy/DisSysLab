# News Editorial

This example introduces a feedback loop — agents that send work
back and forth until it meets a standard. This office has two
agents, Susan and Anna.

Susan scores each article for sentiment. If the sentiment is too
neutral (between 0.25 and 0.75), she sends it to Anna for a rewrite.
Neutral articles are considered to be boring.
Anna pushes the sentiment further — more positive or more negative —
and sends it back to Susan, and so Anna makes the article less boring.
An article may be sent back and forth between Susan and Anna.
In the interests of not having the same article cycle forever,  after
three rewrites, or when the sentiment is strong enough, Susan archives
the article.

```
al_jazeera ─┐
bbc_world  ─┼→  Susan  ←──────────────── Anna
npr_news   ─┘      │  (neutral → rewrite)   ↑
                   │  (strong → archive)    │
                   └→  console              └── (rewritten article)
                   └→  editorial_output.jsonl
```

---

## The roles

**Susan's job — editor:**

```
# Role: editor

You are an editor who receives one message and responds
by sending zero or more messages, each addressed to a destination role.

The messages you receive and send are either plain text or a document
partitioned into sections, each with a section header and a section body.
Treat a document as JSON with each section header as a key and the
section body as the corresponding value. Section headers are unique.

Your job is to analyze the sentiment of each article and score it
from 0.0 (most negative) to 1.0 (most positive).

The document has a section called "rewrites" whose value is a number.
If absent, treat as 0.

If the score is less than 0.25 or greater than 0.75, send to archivist.
If the score is between 0.25 and 0.75 and rewrites < 3, send to copywriter
and increment rewrites by 1.
If the score is between 0.25 and 0.75 and rewrites >= 3, send to archivist.
```

**Anna's job — writer:**

```
# Role: writer

You are a writer who receives one message and responds
by sending zero or more messages, each addressed to a destination role.

The messages you receive and send are either plain text or a document
partitioned into sections, each with a section header and a section body.
Treat a document as JSON with each section header as a key and the
section body as the corresponding value. Section headers are unique.

Your job is to rewrite the article to be more strongly opinionated —
push the sentiment either more positive or more negative, whichever
requires less change. Preserve all sections from the input document.

Always send to client.
```

---

## The org chart

```
Sources: al_jazeera(max_articles=1), bbc_world(max_articles=1)
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

---

## Run it

```bash
dsl run gallery/org_news_editorial/
```

The compiler shows you the routing and asks "Does this look right?"
Say yes and your editorial office starts.

---

## Make it yours

**Change the quality standard.** Open `roles/editor.md` and redefine
what triggers a rewrite. Instead of sentiment score, Susan could check
for length, reading level, or whether key facts are present:

```
If the article is longer than 200 words, send to copywriter for condensing.
If the article is 200 words or fewer, send to archivist.
```

**Change what Anna does.** Anna could translate, simplify, expand,
or fact-check instead of pushing sentiment:

```
Your job is to rewrite the article at a 6th grade reading level.
Preserve the key facts but use simple words and short sentences.
```

**Adjust the rewrite limit.** Change `rewrites < 3` in Susan's role
to allow more or fewer passes before archiving.

---

## What you built

Susan and Anna run in their own threads, exchanging messages through
queues. An article may pass between them up to three times before
being archived. This feedback loop is a common pattern in distributed
systems — iterative refinement with a termination condition.

The next example shows how to wire two offices together as a larger network:
[Two-Office News Network](../org_two_office_news/README.md).
