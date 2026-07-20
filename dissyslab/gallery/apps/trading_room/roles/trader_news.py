# dissyslab/gallery/apps/trading_room/roles/trader_news.py
"""
Trader — trader_news.

Reads one thing at a time from ``SelectNews``: either a news item or
the ledger's reply to a proposed trade — never both at once, because
``SelectNews`` withholds anything else until this role tells it what
to bring next. That command is exactly OfficeSpeak's Case 2 correction
in ``start_gallery/trading_room.md``: "while a trader is waiting for
the ledger's answer it should stop looking at new information
entirely."

Behaviour, each message:
- A news item that warrants a trade: propose it to the ledger, then
  command ``SelectNews`` to bring the reply next (freeze on news).
- A news item that doesn't: command ``SelectNews`` to bring the next
  news item (nothing proposed, no round trip).
- A ledger reply: if approved, write the trade; either way, command
  ``SelectNews`` back to news.

Stateless — built with :class:`dissyslab.blocks.role.Role`, which maps
the three semantic statuses (``request``/``command``/``trade``) onto
the runtime's positional ``out_0``/``out_1``/``out_2`` ports, the same
convention ``router_role`` uses.
"""

from __future__ import annotations

from typing import Any

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

_STATUSES = ["request", "command", "trade"]


def _trader_fn(msg: Any):
    results = []
    if "approved" not in msg:
        # A news item (both news items and ledger replies carry a
        # "headline" field, so "approved" -- present only on a reply
        # -- is the real discriminator, not "headline").
        if msg.get("warrants_trade"):
            print(f"[Trader] proposing trade on: {msg['headline']!r}", flush=True)
            results.append(
                ({"headline": msg["headline"], "action": "buy"}, "request")
            )
            results.append(({"next": "reply"}, "command"))
        else:
            print(f"[Trader] no trade warranted: {msg['headline']!r}", flush=True)
            results.append(({"next": "info"}, "command"))
    else:
        # A ledger reply.
        if msg.get("approved"):
            print(
                f"[Trader] approved -> writing trade: {msg['headline']!r}",
                flush=True,
            )
            results.append(
                (
                    {"headline": msg["headline"], "action": "buy", "approved": True},
                    "trade",
                )
            )
        else:
            print(f"[Trader] rejected: {msg['headline']!r}", flush=True)
        results.append(({"next": "info"}, "command"))
    return results


role = AgentRoleEntry(
    name="trader_news",
    in_ports=("in_",),
    out_ports=tuple(_STATUSES),
    factory=lambda: Role(fn=_trader_fn, statuses=list(_STATUSES)),
    description=(
        "Propose trades on warranted news, command SelectNews to freeze on "
        "the ledger's reply, write approved trades."
    ),
)
