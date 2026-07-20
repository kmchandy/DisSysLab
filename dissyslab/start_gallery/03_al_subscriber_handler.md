# start_gallery example — Al's own office-shaped description (authored, not a cold test)

**What this actually is.** Al's lines below are real — written by Mani,
deliberately playing Al, as a plausible example of what someone who
already thinks in terms of workers and wiring (but isn't a distributed-
systems expert) would say. That's a legitimate way to build a teaching
example — `01`'s Pat line and OfficeSpeak's own gallery examples are
authored the same way. What it is *not* is a cold test: no separate
person played Al, and no fresh Claude (grounded only on
`start_instructions.md` + `start_gallery`) produced the draft below —
this session's Claude did, with everything already learned building
`situation_room_requests`. Task tracked for the real thing: a cold test
with a genuinely separate Al and a fresh Claude, once
`start_instructions.md` exists. Until then, trust the structural
content here (it's verified — see below) and treat the pacing/register
as illustrative, not evidence.

## Al's description

> "Build an office for me.
> It has two types of sources: (1) BBC news, Al Jazeera, and NPR, and
> (2) subscriber_messages.
> Each item from a news source is analyzed in parallel by a team of
> workers, one of whom extracts entities, another scores severity and
> so on.
> The news item, enriched by the information extracted by this worker
> team, is sent to a worker — a subscriber handler.
> The office interacts with subscribers who are not part of the office.
> A subscriber sends request-subscription and cancel-subscription
> through the subscriber_messages source; these requests are sent to
> the subscriber handler.
> A subscription request specifies... the kinds of enriched information
> the subscriber wants to receive.
> A subscription request also has [an identifier for] the subscriber.
> When the subscriber handler gets an item of enriched news it sends
> the news, with the information requested by subscribers, to each
> active subscriber."

(Trimmed from the original: source-filtering per subscription and
"the email of the subscriber" specifically — Al later said both were
incidental to the main story. Delivery mechanism is left abstract; a
system-monitor console was added as a separate, single, non-per-
subscriber destination, once it became clear that's what "console" was
actually asking for.)

Notice what this description gets right for free, just by being
office-shaped: it states the wiring directly ("is sent to a worker"),
which settles compute-once-vs-recompute before the question could even
come up, and it describes the handler pushing on receipt ("when the
subscriber handler gets an item... it sends"), which settles push vs.
pull the same way — as description, not as an answer to a question
anyone asked.

## What's still genuinely open

"And so on" (the extractor team) is a low-stakes gap — Al is
delegating enumeration, not leaving a decision unmade. Propose a
reasonable set (entities, severity, topic, location — the same four
`situation_room` already uses) and move on; no need to ask.

Two things are real structural decisions, though, and don't get to be
silently picked:

- **Backfill or not?** Al never says whether a new subscription sees
  history. Assumed: no — matches the precedent from
  `situation_room_requests`, and it's the simpler default.
- **One message or several?** "The kinds of enriched information" is
  plural — if a subscriber wants both severity and entities, is that
  one combined delivery or two? Assumed: one combined message per item
  per subscriber.

And one thing worth surfacing even though Al didn't ask: nothing here
deduplicates the same story appearing on more than one feed. Not added
— it wasn't asked for, and adding it unprompted would be the kind of
over-engineering `start_instructions_v3.md` already warns against on
the OfficeSpeak side. Flagged instead, the same way a "Things I
assumed —" list would flag it to Pat.

## The office (verified — `dsl build` succeeds)

```office.md
# Office: al_news_subscriptions

Sources: bbc_world(max_articles=3, poll_interval=300), npr_news(max_articles=3, poll_interval=300),
         al_jazeera(max_articles=3, poll_interval=300), webhook(port=9200, path="/subscriber_messages")

Sinks: console_printer, jsonl_recorder(path="subscriber_deliveries.jsonl")

Agents:
EntityExtractor   is an entity_extractor.
SeverityScorer    is a severity_classifier.
TopicTagger       is a topic_tagger.
Geolocator        is a geolocator.
Sync              is a synchronizer(inports=["entities", "severity", "topic", "location"]).
SubscriberHandler is a subscriber_handler.

Connections:
bbc_world's destination is EntityExtractor, SeverityScorer, TopicTagger, Geolocator.
npr_news's destination is EntityExtractor, SeverityScorer, TopicTagger, Geolocator.
al_jazeera's destination is EntityExtractor, SeverityScorer, TopicTagger, Geolocator.
webhook's destination is SubscriberHandler.

EntityExtractor's out is Sync's entities.
SeverityScorer's out is Sync's severity.
TopicTagger's out is Sync's topic.
Geolocator's out is Sync's location.

Sync's out is SubscriberHandler.

SubscriberHandler's monitor is console_printer.
SubscriberHandler's deliver is jsonl_recorder.
```

```roles/subscriber_handler.py
"""SubscriberHandler — custom Python, not an LLM role. One inbox, fed
by Sync's merged enriched-news records and webhook's
request-subscription / cancel-subscription messages, told apart by
shape. Not a coordinator: no gate, merge_synch, or select needed.

Two outports: "monitor" gets every enriched item, unconditionally --
a system-monitor firehose view, separate from any subscriber. Only
"deliver" is per-subscription, one combined message per item per
active subscriber, containing only the fields that subscription
asked for.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


def _make_handler_fn():
    subscriptions: Dict[str, Dict[str, Any]] = {}

    def handler_fn(msg: Any) -> Optional[List[Tuple[Any, str]]]:
        if not isinstance(msg, dict):
            return None

        action = msg.get("action")
        if action in ("request-subscription", "cancel-subscription"):
            subscriber_id = msg.get("subscriber_id")
            if not subscriber_id:
                return None
            if action == "request-subscription":
                subscriptions[subscriber_id] = {
                    "wanted_fields": msg.get("wanted_fields", ["severity"]),
                }
            else:
                subscriptions.pop(subscriber_id, None)
            return None

        # An ordinary enriched news record from Sync.
        results: List[Tuple[Any, str]] = [(msg, "monitor")]
        for subscriber_id, sub in subscriptions.items():
            wanted = {
                field: msg[field]
                for field in sub["wanted_fields"]
                if field in msg
            }
            if not wanted:
                continue
            delivery = {
                "subscriber_id": subscriber_id,
                "title": msg.get("title"),
                "url": msg.get("url"),
                **wanted,
            }
            results.append((delivery, "deliver"))
        return results

    return handler_fn


def _factory() -> Role:
    return Role(fn=_make_handler_fn(), statuses=["monitor", "deliver"])


role = AgentRoleEntry(
    name="subscriber_handler",
    in_ports=("in_",),
    out_ports=("monitor", "deliver"),
    factory=_factory,
    description=(
        "Stores each enriched item once and pushes a combined "
        "per-subscriber delivery to whichever fields each active "
        "subscription asked for. Every item also goes, unconditionally, "
        "to a system-monitor view."
    ),
)
```

## Explanation for Al

News comes in from three feeds; every article gets the same four-part
analysis — entities, severity, topic, location — computed once, no
matter who's subscribed. Everything, analyzed, streams to one console
regardless of subscriptions — a full firehose view for monitoring the
office itself. Separately, a subscriber can request-subscribe, naming
which of the four fields they want; from then on, every new article
that has those fields gets bundled into one delivery for them.
Cancel-subscription stops it, with no effect on anyone else. New
subscribers only see articles from the moment they subscribe, not
history. If the same story shows up on two feeds, it's delivered
twice right now — nothing removes duplicates across feeds. Delivery
itself is a placeholder (a JSONL file here) standing in for however
you actually want to reach a subscriber; swapping it doesn't touch
anything upstream.

## What this teaches

An office-shaped description can resolve the hardest structural
question (compute once vs. recompute per subscriber) as a side effect
of ordinary sentence structure, without anyone treating it as a
decision at all. That's different from what happened in the earlier,
expert-session example (`02`), where the same question needed an
explicit correction after a wrong first draft. Worth watching for in
real Al conversations: is the wiring actually stated ("X is sent to
Y"), or only implied? The two are not the same, and only the first one
reliably prevents the recompute-per-subscriber mistake. Separately:
"and so on" and "handled by a worker called a registry ....." (the
earlier, incomplete version of this same description) are different
kinds of gaps and deserve different responses — enumeration delegation
gets a reasonable default and no question; a genuinely unspecified
worker responsibility gets named explicitly, with a proposed default,
not silently resolved.

## Source

Al's lines authored by Mani; office and role verified with `dsl build`
in a scratch location, 2026-07-19. Not a cold test — see the caveat at
the top of this file.
