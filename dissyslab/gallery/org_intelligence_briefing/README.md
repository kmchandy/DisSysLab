# Intelligence Briefing

A two-agent office where work flows from one agent to the next.
Alex screens articles for significance; only the significant ones
reach Morgan, who rewrites each as a crisp briefing note.

## What it does

```
al_jazeera ─┐
bbc_world  ─┼→  Alex  ─→  Morgan  ─→  intelligence_display
npr_news   ─┘       └→  briefing.jsonl  (discarded articles)
                            └→  briefing.jsonl  (briefing notes)
```

- Three RSS feeds stream articles into Alex
- Alex (an analyst) decides which ones describe a significant world
  event; the rest go to a file and are dropped
- Morgan (an editor) rewrites each keeper as a one-paragraph briefing
  with a significance rating
- Briefings stream to a live display and to `briefing.jsonl`

## Files in this office

```
intelligence_briefing/
    office.md              ← the org chart: sources, agents, sinks
    roles/
        analyst.md         ← what Alex does, in plain English
        editor.md          ← what Morgan does, in plain English
```

A `briefing.jsonl` file appears in the folder once you run the
office; it holds Alex's discards and Morgan's briefings.

## Try it

```bash
dsl init org_intelligence_briefing my_briefing
cd my_briefing
dsl run .
```

The compiler shows you the routing and asks "Does this look right?"
Say yes and your office starts.

## Make it yours

**Change what Alex looks for.** Open `roles/analyst.md` and redefine
significance to match your interests:

```
Your job is to decide if each article discusses developments in
artificial intelligence or machine learning.
```

**Change Morgan's output format.** Open `roles/editor.md` and ask for
a different style — bullet points, a tweet-length summary, a formal memo:

```
Your job is to rewrite each article as three bullet points:
one sentence each for what happened, why it matters, and what to watch next.
```

**Add a third agent.** Insert a translator between Alex and Morgan,
or a classifier after Morgan that routes briefings by topic to
different sinks.

**Change the sources.** Replace the news feeds with anything — job
boards, arXiv papers, social media, your email inbox.

---

## The roles

An office can have many agents sharing the same role — two analysts,
three editors. Here we have one of each.

**Alex's job — analyst:**

```
# Role: analyst

You are a news analyst who receives news articles and sends
articles to an editor or a discard.

Your job is to decide if each article describes a significant
world event — a major political development, conflict, natural
disaster, or scientific breakthrough.

If the article is significant, send to editor.
Otherwise send to discard.
```

**Morgan's job — editor:**

```
# Role: editor

You are a senior editor who receives news articles and sends
articles to an archivist.

Your job is to rewrite each article as a crisp one-paragraph
intelligence briefing note. Begin with a significance rating
on its own line: CRITICAL, HIGH, MEDIUM, or LOW. Then write
one paragraph summarizing the key facts. Preserve the source,
url, and title fields from the input message. Put your
significance rating in a field called "significance" and your
summary in the "text" field.

Always send to archivist.
```

## The org chart

The whole office, in one file:

```
# Office: intelligence_briefing

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: intelligence_display, jsonl_recorder(path="briefing.jsonl")

Agents:
Alex is an analyst.
Morgan is an editor.

Connections:
al_jazeera's destination is Alex.
bbc_world's destination is Alex.
npr_news's destination is Alex.
Alex's editor is Morgan.
Alex's discard is jsonl_recorder.
Morgan's archivist are intelligence_display and jsonl_recorder.
```

## What you built

Alex and Morgan each run in their own thread. Articles flow from
sources through Alex's filter to Morgan's pen, all concurrently.
This is a distributed system — two specialized agents coordinating
through messages, running continuously on your laptop.

The next example adds live social media streaming:
[Situation Room](../org_situation_room/README.md).
