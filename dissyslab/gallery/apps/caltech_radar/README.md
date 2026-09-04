# caltech_radar

**Tags:** rss, single-agent, filter, campus

Three things happening near you, watched at once: talks and events on
the Caltech Institute Calendar, new papers on arXiv cs.AI, and the
weather in Pasadena. One agent reads the events and the papers and
decides which are about computer science or AI. Those go onto a web
page. The rest go to a file, so you can check what the agent threw
away. The weather goes straight to the page without being asked
anything — there is nothing to decide about it.

## How it is wired

```
caltech_calendar ─┐
                  ├→  Screen  ─→  radar.html        (computer science or AI)
arxiv_cs_ai ──────┘          └──→ not_for_me.jsonl  (everything else)

weather ───────────────────────→  radar.html
```

Two sources fan in to Screen's single inbox: the events and the papers
arrive interleaved, in whatever order the two feeds happen to deliver
them, and Screen sees one stream. Screen has two outboxes, `keep` and
`discard`, and every message leaves by exactly one of them. The weather
never reaches Screen at all — its connection goes to the page directly.
That is three of the shapes from
[micro-course 1](https://github.com/kmchandy/DisSysLab/blob/main/course/micro/01_one_connection.html)
in one office: a merge, a two-outbox agent, and a plain connection.

`radar.html` opens in your browser with three sections — **Schedule**
(the Caltech events that got through), **News** (the papers), and
**Weather**. The sink sorts messages into those sections by their
`source` field, which is why the calendar feed is named
`caltech_calendar`: the sink routes anything whose source contains
"calendar" to Schedule.

## Run

```bash
dsl init caltech_radar my_radar
cd my_radar
dsl run .
```

Every source in this office stops after one pass — fifteen events, ten
papers, one weather reading — so the office runs, writes the page, and
terminates. It does not sit there polling.

`Screen` is an English role, so this office needs `ANTHROPIC_API_KEY`
in a `.env` file beside `office.md`. About 25 messages, one model call
each.

`dsl check` on this office reports one **note** (W12): the HTML sink
imports `subprocess`, because it opens your browser when the run
finishes. That is not an error. It is the check telling you that a
piece of Python in this office can act outside the Sources and Sinks
the office declares, and asking whether you meant it. The file is
`sinks/periodic_brief_html_sink.py`, sitting in your own folder. Open
it.

## Files in this office

```
caltech_radar/
    office.md                        ← the network: sources, agent, sinks
    roles/
        cs_ai_filter.md              ← what Screen does, in plain English
    sinks/
        periodic_brief_html_sink.py  ← builds radar.html
```

`radar.html` and `not_for_me.jsonl` appear after the first run. Read
the second one. The discarded pile is where you find out what your
agent actually understood you to mean.

## Make it yours

**Change what counts.** Open `roles/cs_ai_filter.md` and rewrite the
criteria. Physics instead of computer science; anything with free food;
talks before 4pm. The English in that file is the whole specification —
there is nothing else to change.

**Watch a different calendar.** The Caltech feed is an ordinary RSS
URL, given in the `Sources:` line. Any department, lab, or campus that
publishes a feed works the same way. Keep "calendar" in the `name` if
you want it filed under Schedule rather than News:

```
Sources: rss(url="https://your-feed-here/rss", name="my_calendar",
             max_articles=15)
```

**Keep the discards out of your way.** Replace `jsonl_recorder` with
`discard` in `office.md` once you trust the filter. Being able to say
"throw this away" explicitly, rather than leaving an outbox
unconnected, is why `discard` exists.

**Add a second agent.** Send `keep` to a summarizer before the page,
and the office becomes a pipeline: Screen decides, the summarizer
writes. See `arxiv_radar` for that shape.

## The role

Screen's job description, in plain English:

```
---
outboxes: keep, discard
adds: reason
---
# Role: cs_ai_filter

You receive two kinds of message: talks and events from the Caltech
Institute Calendar, and new paper listings from arXiv cs.AI. ...
```

The front matter is the part `dsl check` reads. It says Screen may send
on `keep` and on `discard` and on nothing else, and that Screen must
add a `reason` field to every message it passes on. Neither of those is
a comment: `Agent.send` raises on an outbox the role did not declare,
and the framework rejects a reply that is missing `reason`.

The `reason` is why `not_for_me.jsonl` is worth opening. Every
discarded message carries one sentence saying what made the agent
decide — which is the only record you have of what your English
actually meant to it.

## The network

The whole office, in one file:

```
# Office: caltech_radar

Sources: rss(url="https://www.caltech.edu/campus-life-events/calendar/rss", name="caltech_calendar", max_articles=15), arxiv_cs_ai(max_articles=10), weather(city="Pasadena", max_readings=1)
Sinks: periodic_brief_html_sink(path="radar.html"), jsonl_recorder(path="not_for_me.jsonl")

Agents:
Screen is a cs_ai_filter.

Connections:
rss's destination is Screen.
arxiv_cs_ai's destination is Screen.
Screen's keep is periodic_brief_html_sink.
Screen's discard is jsonl_recorder.
weather's destination is periodic_brief_html_sink.
```

The Caltech feed is named `rss` in the Connections section because
`rss` is the name of the generic feed reader in the `Sources:` line.
The `name="caltech_calendar"` argument is what each message calls
itself once it is moving, and it is what the page uses to file it.

## What you built

Six agents in six threads, sharing no memory, each blocked waiting on
its own inbox. The Caltech feed and arXiv do not know about each other;
they know only where to send. Screen does not know where its two
outboxes go. That is the whole of the coupling, and it is written down
in `office.md` — which is also the only place you have to look to know
what this system can and cannot do.
