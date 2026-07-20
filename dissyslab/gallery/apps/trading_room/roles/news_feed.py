# dissyslab/gallery/apps/trading_room/roles/news_feed.py
"""
News — news_feed.

Validation fixture for the generic ``select`` coordinator
(``dissyslab.office.library.select_role``), mirroring OfficeSpeak's
``start_gallery/trading_room.md``. Fires once on the office's single
``starter`` kick, then emits a small, fixed sequence of news items —
some that warrant a trade, one that doesn't — and stops. Deterministic
by construction: a single sender to a single connection preserves
send order, so ``SelectNews`` sees these in exactly this order
regardless of thread scheduling.
"""

from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


_ITEMS = [
    {"headline": "Fed cuts rates", "warrants_trade": True},
    {"headline": "Weather report", "warrants_trade": False},
    {"headline": "Merger announced", "warrants_trade": True},
    {"headline": "Company X profit surges", "warrants_trade": True},
]


class _NewsFeed(Agent):
    def __init__(self, name: str | None = None):
        super().__init__(name=name, inports=["in_"], outports=["out_"])

    def run(self) -> None:
        self.recv("in_")  # the starter's single kick
        for item in _ITEMS:
            self.send(dict(item), "out_")


role = AgentRoleEntry(
    name="news_feed",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_NewsFeed,
    description="Fire a fixed sequence of news items once kicked by starter.",
)
