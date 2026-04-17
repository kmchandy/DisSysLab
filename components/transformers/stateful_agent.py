# components/transformers/stateful_agent.py

"""
StatefulAgent: Accumulates article dicts and emits a batch on a clock tick.

This is a fixed, non-tailorable component used in every gallery pipeline.
It sits between the transform pipeline and the report writer:

    transformers → StatefulAgent → ReportWriter → text sink

The StatefulAgent:
  - Receives article dicts from the pipeline (standard five-key format)
  - Accumulates them in memory, de-duplicating by URL
  - On each clock tick, emits one batch dict to the report writer
  - Continues accumulating after each tick (sliding window by default)
  - Stops when it receives a STOP sentinel (handled by the DSL framework)

Clock ticks are sent by a ClockSource — a separate Source node wired
into the StatefulAgent alongside the article stream.

Usage:
    from dissyslab.components.transformers.stateful_agent import StatefulAgent
    from dissyslab.components.sources.clock_source import ClockSource
    from dissyslab.blocks import Source, Transform, Sink

    # Article pipeline
    feed      = Source(fn=normalizer.run,   name="feed")
    analyze   = Transform(fn=ai_fn,          name="analyze")

    # Batch reporting
    clock     = Source(fn=ClockSource(interval_seconds=86400).run, name="clock")
    batcher   = Transform(fn=StatefulAgent(max_articles=200).run,  name="batcher")
    report    = Transform(fn=report_writer_fn,                      name="report")
    output    = Sink(fn=print,                                       name="output")

    g = network([
        (feed,    analyze),
        (analyze, batcher),   # articles flow in
        (clock,   batcher),   # ticks flow in  (fanin)
        (batcher, report),
        (report,  output),
    ])

Clock tick messages:
    {"type": "tick", "timestamp": "<ISO string>"}

Batch output dict emitted on each tick:
    {
        "type":      "batch",
        "count":     int,                  # total articles across all sources
        "tick_time": "<ISO string>",
        "by_source": {
            "hacker_news":     [ {...}, {...}, ... ],
            "mit_tech_review": [ {...}, ... ],
            ...
        }
    }

    Articles within each source are in order of arrival.
    Duplicates (same URL) are discarded across all sources.
    If no articles have arrived since the last tick, no batch is emitted.
"""

import threading
from datetime import datetime, timezone
from typing import Optional


class StatefulAgent:
    """
    Accumulates article dicts and emits a batch dict on each clock tick.

    Thread-safe: articles and ticks arrive on separate threads (DSL fanin).

    Args:
        max_articles: Maximum articles to keep in memory at once.
                      Oldest articles are dropped when limit is reached.
                      Default: 200.
        clear_on_tick: If True, clear accumulated articles after each tick.
                       If False, keep accumulating (sliding window).
                       Default: True (emit articles since last tick only).
    """

    def __init__(
        self,
        max_articles: int = 200,
        clear_on_tick: bool = True,
    ):
        self.max_articles = max_articles
        self.clear_on_tick = clear_on_tick

        self._by_source = {}           # {source_name: [article, ...]}
        self._seen_urls = set()       # for de-duplication across all sources
        self._lock = threading.Lock()

    def run(self, msg: dict) -> Optional[dict]:
        """
        Process one incoming message.

        Articles are accumulated. Clock ticks trigger batch emission.
        Returns a batch dict on tick, None on article (no downstream output).

        This method is called by the DSL framework for every message
        arriving at this transform node, whether from the article stream
        or the clock source.
        """
        msg_type = msg.get("type", "article")

        if msg_type == "tick":
            return self._emit_batch(msg.get("timestamp", ""))

        else:
            # It's an article — accumulate it
            self._accumulate(msg)
            return None   # no output until tick

    # ── private ───────────────────────────────────────────────────────────

    def _accumulate(self, article: dict):
        """Add article to accumulator, organised by source, de-duplicating by URL."""
        url = article.get("url", "")
        source = article.get("source", "unknown")

        with self._lock:
            if url and url in self._seen_urls:
                return  # duplicate — discard

            if url:
                self._seen_urls.add(url)

            # Add to the correct source bucket
            if source not in self._by_source:
                self._by_source[source] = []
            self._by_source[source].append(article)

            # Enforce max_articles across all sources (drop oldest globally)
            total = sum(len(v) for v in self._by_source.values())
            if total > self.max_articles:
                # Find and remove the oldest article across all sources
                for src in list(self._by_source.keys()):
                    if self._by_source[src]:
                        dropped = self._by_source[src].pop(0)
                        dropped_url = dropped.get("url", "")
                        if dropped_url:
                            self._seen_urls.discard(dropped_url)
                        if not self._by_source[src]:
                            del self._by_source[src]
                        break

    def _emit_batch(self, tick_time: str) -> Optional[dict]:
        """Emit batch dict organised by source, and optionally clear accumulator."""
        with self._lock:
            if not self._by_source:
                return None  # nothing accumulated — skip this tick

            total = sum(len(v) for v in self._by_source.values())

            batch = {
                "type":      "batch",
                "count":     total,
                "tick_time": tick_time or datetime.now(timezone.utc).isoformat(),
                "by_source": {src: list(articles)
                              for src, articles in self._by_source.items()},
            }

            if self.clear_on_tick:
                self._by_source = {}
                self._seen_urls = set()

            return batch
