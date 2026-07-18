"""Registry role for situation_room_requests.

Custom Python role, not an LLM role — its logic is exact and
auditable (a table lookup and a dict projection), so it stays
ordinary code rather than a prompt.

One inbox, fed by two upstream senders (Sync's merged feature
records, webhook's start/stop requests) — told apart by shape, not by
separate inports. Not a coordinator: nothing here needs gate,
merge_synch, or select.

Private state: ``subscriptions = {request_id: {stakeholder,
watch_for, channel}}``, held in a closure so it persists for the
lifetime of the agent (one Role instance runs one message-processing
loop for the whole office run — see dissyslab/blocks/role.py).

Behavior per incoming message:

* ``{"action": "start", "request_id", "stakeholder", "watch_for",
  "channel"}`` -> add an entry. No outgoing message.
* ``{"action": "stop", "request_id"}`` -> remove the entry, if
  present. No outgoing message.
* ``{"action": "publish", "request_id"?, "stakeholder"?, "title"?,
  "text"?, "url"?, "source"?, "timestamp"?}`` -> this office is a
  pub/sub system: a subscriber may publish a message, and it is
  treated exactly like a torrent item, not routed back privately to
  its publisher. Registry normalizes it to the standard article
  shape ({source, title, text, url, timestamp}) that Sasha and the
  four extractors expect, and forwards it on "to_torrent" -> Sasha,
  the same entry point the RSS torrent uses. It re-enters the shared
  pipeline (dedupe -> four extractors -> synchronizer -> Registry
  again, this time as an ordinary feature record) and, once computed,
  is visible to every currently active subscription watching the
  relevant field, the same as any other item. A synthetic, unique
  "url" is generated when the publisher doesn't supply one, because
  Sasha's deduplicator silently drops any message missing its "by"
  key -- without this, an un-urled publish would vanish with no
  message emitted, or a repeated blank "url" would look like a
  duplicate of itself.
* an ordinary feature record (has "severity"/"entities"/"topic"/
  "location", produced by Sync) -> always emit the full record on
  "archive". Then, for each currently active subscription, project
  just that subscription's ``watch_for`` field, package it into a
  short message tagged with ``request_id`` and ``stakeholder``, and
  emit it on "to_console" or "to_email" per that subscription's
  ``channel``.

Deliberate simplifications for this sketch (confirmed by Mani,
2026-07-18): push only, nothing polls Registry; no backfill, a new
request only sees records computed after it starts, so there is no
query-by-item-id lookup path even though every record is, in the
general sense, stored once in memory.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry


# Fields Sync's four extractors add to a record, in case a stakeholder
# asks to watch one of these by name.
_KNOWN_FEATURE_FIELDS = {"entities", "severity", "topic", "location"}


def _make_registry_fn():
    subscriptions: Dict[str, Dict[str, str]] = {}
    publish_counter = {"n": 0}  # closure-mutable; a plain int can't be

    def registry_fn(msg: Any) -> Optional[List[Tuple[Any, str]]]:
        if not isinstance(msg, dict):
            return None

        action = msg.get("action")
        if action in ("start", "stop"):
            request_id = msg.get("request_id")
            if not request_id:
                # Malformed control message; drop rather than guess.
                return None
            if action == "start":
                subscriptions[request_id] = {
                    "stakeholder": msg.get("stakeholder", request_id),
                    "watch_for": msg.get("watch_for", "severity"),
                    "channel": msg.get("channel", "console"),
                }
            else:  # "stop"
                subscriptions.pop(request_id, None)
            return None

        if action == "publish":
            # A subscriber's own item. Treat it exactly like a torrent
            # item: normalize to the standard article shape and send
            # it into the same entry point (Sasha) the RSS feeds use.
            # It is NOT routed back privately to the publisher here —
            # once it's computed downstream it will reach whichever
            # subscriptions (including, incidentally, the publisher's
            # own) are watching the relevant field, same as any other
            # item.
            publish_counter["n"] += 1
            url = msg.get("url") or (
                f"urn:publish:{msg.get('request_id', 'anon')}:"
                f"{publish_counter['n']}"
            )
            item = {
                "source": msg.get("source", f"subscriber:{msg.get('stakeholder', msg.get('request_id', 'unknown'))}"),
                "title": msg.get("title", ""),
                "text": msg.get("text", ""),
                "url": url,
                "timestamp": msg.get("timestamp") or time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            }
            return [(item, "to_torrent")]

        # Otherwise: an ordinary computed feature record from Sync.
        # Archive every record unconditionally, regardless of who (if
        # anyone) is currently subscribed.
        results: List[Tuple[Any, str]] = [(msg, "archive")]

        for request_id, sub in subscriptions.items():
            field = sub["watch_for"]
            if field not in msg:
                continue  # this record doesn't carry the watched field
            value = msg[field]
            projected = {
                "request_id": request_id,
                "stakeholder": sub["stakeholder"],
                "title": msg.get("title"),
                "url": msg.get("url"),
                field: value,
                "text": (
                    f"[{sub['stakeholder']}] {field}={value} "
                    f"— {msg.get('title', '')}"
                ),
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
        "Stores each computed feature record once (regardless of how "
        "many requests are active) and pushes a per-subscriber "
        "projection to whichever channel each active request asked "
        "for. Also accepts subscriber-published items and re-injects "
        "them into the same shared pipeline as torrent items "
        "(pub/sub). Deterministic Python, not an LLM role."
    ),
)
