# Intelligence Briefing

This example shows a two-agent office where agents hand off work to each other.

Alex screens incoming articles for significance. Only the significant ones
reach Morgan, who rewrites each one as a crisp intelligence briefing note.
Everything else is discarded.

```
al_jazeera ─┐
bbc_world  ─┼→  Alex  ─→  Morgan  ─→  intelligence_display
npr_news   ─┘       └→  briefing.jsonl  (discarded articles)
                            └→  briefing.jsonl  (briefing notes)
```

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

---

## The org chart: Office staff and how they communicate
Next we describe the agents in the office -- the  sources, processing agents and sinks. 
Then we define their connections: who sends what information to whom.

```
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

---

## Run it

```bash
dsl run gallery/org_intelligence_briefing/
```

The compiler shows you the routing and asks "Does this look right?"
Say yes and your office starts.

---

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

**Add a third agent.** You could add a translator between Alex and Morgan,
or a classifier after Morgan that routes briefings by topic to different sinks.

**Change the sources.** Replace the news feeds with anything — job boards,
arXiv papers, social media, your email inbox.

---

## What you built

Alex and Morgan each run in their own thread. Articles flow from sources
through Alex's filter to Morgan's pen, all concurrently. This is a
distributed system — two specialized agents coordinating through messages,
running continuously on your laptop.

The next example adds live social media streaming:
[Situation Room](../org_situation_room/README.md).
