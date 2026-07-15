# Failure modes — periodic_brief

This file documents the known limits of periodic_brief. It is
what Claudette reads to understand *when this design starts to
break down*, so she does not propose it as a precedent for tasks
that would hit those limits.

---

## Known failure modes

### F1 — Source unavailable on a given run

If one of the RSS feeds is down or the weather/stock API is
rate-limited, the corresponding section of the HTML is empty
(or contains a stale fallback) for that run.

The office does *not* retry, *not* alert, *not* fail loudly.
The user discovers the missing section by looking at the HTML.

Why this is acceptable for this task: the artifact is a daily
informational dashboard. A missing section is a mild annoyance,
not a correctness failure. For a higher-stakes task (e.g.,
trading signal generation), this would not be acceptable.

### F2 — Stock tickers limited to the registered aliases

The office uses `stocks`, `stocks_2`, `stocks_3` (registered
aliases). To watch more than five tickers, the user must either
add new aliases to the source registry or invent a custom
multi-ticker source. The office.md cannot just write
`stocks_6`, `stocks_7`, … indefinitely without registry
support.

Why this is acceptable for this task: users tracking >5 tickers
are not the target audience for a teaching example. A serious
finance tool would build a proper multi-ticker source.

### F3 — No deduplication across sources

BBC and NPR sometimes cover the same story. The HTML shows
both headlines side-by-side without noting the duplication.

Why this is acceptable for this task: in a flat
headlines-list, the cost of deduplication exceeds the value.
For an analytical briefing where each story should be discussed
once, deduplication would matter (and would justify adding the
`deduplicator` agent — see `situation_room` for that pattern).

### F4 — HTML is the only output format

The sink emits HTML. If the user wants JSON, Markdown, or
plain-text, they have to either modify the sink or run a
separate office.

Why this is acceptable for this task: the user wants HTML;
generalising to multiple formats would add config without
serving the stated need.

### F5 — No state between runs

Each invocation starts fresh. The office does not know what was
in yesterday's briefing, so it cannot say "no new headlines
since yesterday" or "this stock moved 3% since the last run."

Why this is acceptable for this task: the user wants a current
snapshot, not a diff. A diff-aware briefing would justify a
checkpointed sink that reads its own prior output.

---

## When these failures matter — i.e., when Claudette should NOT use this design

If the new task requires any of:

- **High availability of every source** — F1 makes this unsuitable.
  Pattern needed instead: per-source health monitoring with
  alerts.
- **Many sources of the same type** — F2 makes this unsuitable.
  Pattern needed instead: a registry-aware multi-instance source,
  or a custom source that takes a list.
- **Deduplication or cross-source synthesis** — F3 makes this
  unsuitable. Pattern needed instead: dedup + enrichment agents
  (see `situation_room`).
- **Multiple output formats from one office** — F4 makes this
  unsuitable. Pattern needed instead: multiple sinks fanning out
  from a single enrichment moderator.
- **Differential information across runs** — F5 makes this
  unsuitable. Pattern needed instead: a checkpointed sink or a
  persistent intermediate store.

---

## Failures that have *not* happened (worth confirming, not assuming)

These are plausible failure modes that, to the best of current
knowledge, have not surfaced in practice — but Claudette should
not treat them as ruled out:

- Race conditions when sources emit faster than the sink can
  render
- HTML corruption when special characters appear in headlines
- Memory growth when the office is left running for very long
  periods (the office is designed as one-shot; long-running
  behaviour is untested)
