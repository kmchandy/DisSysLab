# News Filter

This example shows the simplest possible office -- an office with one agent.

Felix reads every incoming article and makes one decision — is this
article about the Americas? If yes, it goes to the console. If no,
it goes to a file and is discarded from the live display. The 
org chart -- the flow of information -- is shown below.

```
al_jazeera ─┐
             ├→  Felix  ─→  console  (articles about the Americas)
bbc_world  ─┘          └→  filtered_output.jsonl  (everything else)
```

---

## What Felix does: The Role

An office may have many agents with the same role. 
For example, an office may have many editors and many copywriters.
We define a role by its job descriptions.
Here is a job description for news filter.


```
# Role: filter

You are a content filter who receives news articles and sends
articles to a keeper or a discard.

Your job is to decide if each article is about the americas: canada, usa, brazil, ..
If the article is about the americas, send to keeper.
Otherwise send to discard.
```

---

## The org chart: Office staff and how they communicate
Next we describe the agents in the office -- the  sources, processing agents and sinks. 
Then we define their connections: who sends what information to whom.

```
Sources: al_jazeera(max_articles=2), bbc_world(max_articles=2)
Sinks: console_printer, jsonl_recorder(path="filtered_output.jsonl")

Agents:
Felix is a filter.

Connections:
al_jazeera's destination is Felix.
bbc_world's destination is Felix.
Felix's keeper is console_printer.
Felix's discard is jsonl_recorder.
```

---

## Run it

```bash
dsl run gallery/org_news_filter/
```

The compiler shows you the routing and asks "Does this look right?"
Say yes and your office starts.

---

## Make it yours

**Change the filter topic.** Open `roles/filter.md` and change the
geography to anything you care about:

```
Your job is to decide if each article is about climate change or
renewable energy.
```

**Change the sources.** In `office.md`, replace `al_jazeera` and
`bbc_world` with any sources from the framework:

```
Sources: hacker_news(max_articles=5), techcrunch(max_articles=5)
```

**Add more agents.** Once an article passes Felix's filter, you could
send it to a second agent that summarizes it, rates its significance,
or translates it. That's the next example —
[Intelligence Briefing](../org_intelligence_briefing/).


## You have built a distributed system
Congratulations — Felix is running in his own thread, processing
articles the moment they arrive. This is a distributed system running
on your laptop. Later we will show you how to deploy it to the cloud.