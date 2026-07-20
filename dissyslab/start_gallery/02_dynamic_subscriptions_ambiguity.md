# start_gallery example — a structural ambiguity, resolved (expert session, not a Pat cold test)

**What this actually is, read before anything else below.** This is a
real, close-to-verbatim transcript of the conversation that built
`gallery/apps/situation_room_requests` — but the "Pat" role in it was
played by Mani (the system's own designer, not a non-technical user),
and the "Claude" role was played by an instance holding this entire
session's accumulated context, plus direct reads of `role.py`,
`network.py`, `os_agent.py`, and `webhook_source.py` done specifically
to get this right. Neither side is a fair stand-in for a real
`dsl new`/`dsl edit` session: a real Pat won't phrase a correction as
precisely as "the features are computed by parallel agents... stored
in memory... computed only once" — that's an architect's directive,
not a non-programmer's reaction — and a real Claude session won't have
this depth of context unless it's actually captured in
`start_instructions.md` and `start_gallery` themselves.

So: treat the *structural pattern* below (compute once regardless of
subscriber count; push, not pull; no backfill; no new coordinator
needed) as real and worth teaching. Don't treat the register of either
side's lines as evidence of what a real Pat conversation sounds like.
A genuinely representative version of this file still needs to come
from an actual cold test — a fresh Claude grounded only on
`start_instructions.md` + `start_gallery`, talking to something playing
an actually non-technical Pat, the same discipline OfficeSpeak already
uses for its own cold tests. That hasn't been done yet.

`01_single_agent.md` shows the destination: a correct, unambiguous
office, with nothing to disambiguate. This one shows what resolving a
real structural ambiguity looked like at least once — with the caveat
above about whose voice is actually in it.

## The architect's initial description (structural, and genuinely incomplete)

There wasn't one crisp opening sentence — the real ask was spread
across several messages, with discussion in between. In order,
close to verbatim:

> "Think of a situation room in a movie about the government. Torrents
> of data arrive from a variety of sources. The Treasury Department
> wants the data analyzed to identify currency manipulators; the
> Defense Department wants to know about possible attacks; the State
> Department wants to know about riots..."

> "Think of a situation room with two kinds of inputs: (1) data from
> news, social media etc. (2) requests from stakeholders for different
> types of analysis; when the stakeholder wants it says stop my
> request. Each request is a sequence of enriching — entity
> extraction, severity classification..."

> "Assume that the torrent of data is fixed. Stakeholders can ask for
> analysis of the torrent but cannot ask for more data feeds into the
> torrent."

Structurally, this already names a source (the torrent), a dynamic set
of requests, and per-request enrichment. What it doesn't say is the
thing that turns out to matter most: when two stakeholders both want
severity on the same article, is that computed once or twice?

## First reading, and why it's wrong

The literal-minded reading treats "each request watches for one kind
of thing" as "each request gets its own pipeline" — a router in front
of the four extractors (entity, severity, topic, geo), fanning each
incoming article out to one enrichment pipeline per active request.
That's a real office, and it even builds. It's also wrong: every
active subscriber re-triggers the same LLM calls on the same article,
so the cost of running this office scales with the number of
subscribers, not with the number of articles. Nothing in Pat's
sentence rules this out. Nothing in it rules out the correct reading
either. This is the ambiguity — not a missing field, a missing
decision about where computation happens relative to subscription.

## The architect's correction

"The features of the item are computed by parallel agents exactly as
in the current situation room, and the features are stored in memory.
Then each request is fulfilled by looking up the memory. Even if many
requests ask for severity_classification, it is computed only once."

This is the actual structural fix: compute once, downstream of
subscription count entirely; serve every request from what's already
computed. It moves the router from *before* the four extractors to
*after* them.

## Remaining ambiguities, resolved by asking

Even with the compute-once decision settled, two questions were still
open, and got closed by asking rather than guessing:

- **Push or pull?** Does the registry notify active subscribers
  itself as new records arrive, or do subscribers have to ask for
  what's new? Answer: "Push. Not pull."
- **Backfill or not?** Does a request that starts now see history
  from before it started? Answer: "New request only sees from now
  onwards."

Both answers are one line. Neither was inferable from the original
description, and guessing wrong on either would have changed the
registry's actual logic (a query-by-item-id lookup path exists only if
backfill is needed — it isn't, so it doesn't).

## An extension, stated the same way

Later in the same conversation, the architect added a capability
rather than resolving an ambiguity — worth including because it's the
same register, just additive: "The situation_room is a pub/sub system.
Allow subscribers to publish messages. These messages are treated
exactly in the same way as torrent messages." That single sentence is
enough to derive the mechanism: a published item has to re-enter the
same shared pipeline the RSS torrent uses, not get special treatment —
so it needs a wire back from the registry to the pipeline's entry
point, normalized into the same shape the pipeline already expects.

## The resolved office

```office.md
# Office: situation_room_requests

# Same fixed torrent and same four parallel extractors as apps/situation_room.
# New: a Registry that holds computed features in memory and serves a
# dynamic set of stakeholder requests (start/stop) out of that memory,
# instead of recomputing anything per request.
#
# situation_room_requests is a pub/sub system. Subscribers may also
# publish: a message a subscriber publishes re-enters the same shared
# pipeline (dedupe -> four extractors -> synchronizer) as a torrent
# item, is computed once, and is then visible to every currently
# active subscription watching the relevant field -- exactly like any
# other torrent item, not routed back privately to its publisher.

Sources: bbc_world(max_articles=3, poll_interval=300), npr_news(max_articles=3, poll_interval=300),
         al_jazeera(max_articles=3, poll_interval=300), webhook(port=9100)

Sinks: jsonl_recorder_archive(path="feature_archive.jsonl"),
       intelligence_display(max_items=8),
       gmail_sink(to="stakeholder2@example.com", subject="Situation Room Briefing")

Agents:
Sasha    is a deduplicator(by="url").
Eve      is an entity_extractor.
Sam      is a severity_classifier.
Tom      is a topic_tagger.
Greta    is a geolocator.
Sync     is a synchronizer(inports=["entities", "severity", "topic", "location"]).
Registry is a subscription_registry.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.
webhook's destination is Registry.

Sasha's out is Eve, Sam, Tom, Greta.

Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.

Sync's out is Registry.

Registry's archive is jsonl_recorder_archive.
Registry's to_console is intelligence_display.
Registry's to_email is gmail_sink.
Registry's to_torrent is Sasha.
```

```roles/subscription_registry.py
"""Registry role for situation_room_requests.

Custom Python, not an LLM role — this logic is exact and auditable
(a table lookup and a dict projection), so it stays ordinary code.

One inbox, fed by two upstream senders (Sync's merged feature
records, webhook's start/stop/publish requests) — told apart by
shape, not by separate inports. Not a coordinator: nothing here
needs gate, merge_synch, or select. Push only, nothing polls this
agent; no backfill, a new request only sees records computed after
it starts.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


def _make_registry_fn():
    subscriptions: Dict[str, Dict[str, str]] = {}
    publish_counter = {"n": 0}

    def registry_fn(msg: Any) -> Optional[List[Tuple[Any, str]]]:
        if not isinstance(msg, dict):
            return None

        action = msg.get("action")
        if action in ("start", "stop"):
            request_id = msg.get("request_id")
            if not request_id:
                return None
            if action == "start":
                subscriptions[request_id] = {
                    "stakeholder": msg.get("stakeholder", request_id),
                    "watch_for": msg.get("watch_for", "severity"),
                    "channel": msg.get("channel", "console"),
                }
            else:
                subscriptions.pop(request_id, None)
            return None

        if action == "publish":
            # Treated exactly like a torrent item: normalize and
            # re-enter the shared pipeline at its entry point.
            publish_counter["n"] += 1
            url = msg.get("url") or (
                f"urn:publish:{msg.get('request_id', 'anon')}:"
                f"{publish_counter['n']}"
            )
            item = {
                "source": msg.get("source", f"subscriber:{msg.get('stakeholder', 'unknown')}"),
                "title": msg.get("title", ""),
                "text": msg.get("text", ""),
                "url": url,
                "timestamp": msg.get("timestamp") or time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            }
            return [(item, "to_torrent")]

        # An ordinary computed feature record from Sync. Archive it
        # unconditionally, then serve currently active subscriptions
        # from it -- no recomputation, regardless of how many.
        results: List[Tuple[Any, str]] = [(msg, "archive")]
        for request_id, sub in subscriptions.items():
            field = sub["watch_for"]
            if field not in msg:
                continue
            value = msg[field]
            projected = {
                "request_id": request_id,
                "stakeholder": sub["stakeholder"],
                "title": msg.get("title"),
                "url": msg.get("url"),
                field: value,
                "text": f"[{sub['stakeholder']}] {field}={value} — {msg.get('title', '')}",
            }
            outport = "to_console" if sub["channel"] == "console" else "to_email"
            results.append((projected, outport))
        return results

    return registry_fn


def _factory() -> Role:
    return Role(
        fn=_make_registry_fn(),
        statuses=["archive", "to_console", "to_email", "to_torrent"],
    )


role = AgentRoleEntry(
    name="subscription_registry",
    in_ports=("in_",),
    out_ports=("archive", "to_console", "to_email", "to_torrent"),
    factory=_factory,
    description=(
        "Stores each computed feature record once and pushes a "
        "per-subscriber projection to whichever channel each active "
        "request asked for. Also accepts subscriber-published items "
        "and re-injects them into the shared pipeline (pub/sub)."
    ),
)
```

## Explanation for Pat

News comes in from three feeds and gets the same four-part analysis
every article always gets — who's in it, how severe it is, what topic
it's about, where it happened — computed exactly once per article no
matter who's watching. Separately, a stakeholder can say "start
watching for severity" and give it a name; from that point on, every
new article's severity rating gets pushed to them, on-screen or by
email depending on what they asked for. Saying "stop" ends it, with no
effect on anyone else watching. A stakeholder can also feed in their
own item instead of waiting for the news — it gets the same four-part
analysis and reaches the same watchers as if it had come from a feed.
Nothing is recomputed for a second, third, or tenth stakeholder asking
about the same thing.

## What surfaced later, once it was actually built and run

The ambiguity-resolution above happened at the *description* stage,
before anything ran. Two more issues surfaced only by running it,
worth naming because they're a different kind of gap: a declared
outport (`to_torrent`) went briefly unwired in `office.md` with no
error at build time — `dsl build` doesn't require every declared
outport to be connected, so this is a check a conversation has to make
by reading the connections, not one the compiler makes for you. And
the RSS sources had no `poll_interval`, so they fetched once and went
silent — correct per their own documented default, but it meant the
"dynamic ongoing subscription" premise had nothing live left to
subscribe to by the time anyone tried it. Both are reminders that
"resolved through conversation" and "correct when run" are different
claims — the second one only gets checked by actually building and
running the thing.

## What this teaches, and what it doesn't

What's trustworthy here: a structural ambiguity can be a missing
*decision*, not a missing field — "where does computation happen
relative to subscription" — and closing it means proposing a concrete
structure and reacting to feedback, not asking for more precision in
the abstract. Quick either/or questions (push or pull, backfill or
not) are cheap and worth asking explicitly rather than defaulting
silently. And "for each subscription, do X" is not, on its own,
evidence that a new coordinator is needed — this office uses none;
it's one ordinary Python role with private state, and that should be
the default assumption until something concrete rules it out.

What's not trustworthy: any inference about how *quickly*, how
*precisely*, or in what *register* a real Pat would supply these
answers. The architect resolved both remaining ambiguities in one
two-line message, correctly, on the first try. That's the architect's
own system knowledge showing, not a property of the disambiguation
process itself — a real Pat may need the question asked three
different ways, or may not have an opinion on backfill at all until
she sees what happens without it. Nothing here validates timing or
difficulty for the real case, only that the *kind* of gap (a
structural decision hiding behind seemingly-complete English) is
real and worth watching for.

## Source

Distilled from the conversation that built
`gallery/apps/situation_room_requests`, 2026-07-18–19 — an expert
design session between Mani and a Claude instance with this session's
full accumulated context, not a Pat/cold-Claude exchange. See the
caveat at the top of this file before reusing anything below as a
claim about real Pat conversations.
