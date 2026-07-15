# Task: periodic_brief

This file is what Claudette reads to understand *what the office
is for*, abstracted from the implementation. It is the kind of
spec a human would have handed Claudette to build this office
from scratch.

---

## The task

Build a sense-and-respond system that, on each invocation,
produces a single self-contained HTML page summarising the
user's "morning information." The page combines:

- recent **news headlines** from a small set of major outlets
- the day's **weather** for a configured city
- the day's **stock quotes** for a small set of tickers

The user opens the resulting page in a browser, drags it into a
notes app, or emails it to themselves.

## Success criterion

The HTML page renders correctly, contains current data from
each configured source, and is produced in under fifteen
seconds without requiring the user to provide API keys.

## Cadence and persistence

The office supports two cadences, selected by source
configuration:

- **On-demand.** Each source is configured with a bound
  (`max_articles=N`, `max_readings=N`). The office runs once,
  produces one HTML artifact, and exits. The user re-runs
  `dsl run periodic_brief` whenever they want a fresh briefing.
- **Continuous.** Sources are configured *without* an item bound,
  or with an explicit polling interval. The office runs
  persistently, refreshing the HTML each time a source emits.
  The browser's `<meta refresh>` tag picks up updates if the
  page is left open.

The default configuration (with `max_articles=5`,
`max_readings=1`) is on-demand. To run continuously, remove the
bounds from the source calls or set polling intervals at the
source level.

**Persistence:** none required between runs in either mode.
Each invocation (on-demand) or refresh (continuous) produces a
fresh artifact; no state carries over.

## Available sources

- RSS feeds for major news outlets (BBC, NPR, Al Jazeera, …)
- Weather API (Open-Meteo, no key required)
- Stock quote API (Yahoo / equivalent, no key required)

## Output

A single HTML file at a configurable path (default: `brief.html`).
The HTML contains a `meta refresh` tag so it self-updates if
left open while the office continues polling.

## Non-goals

- This is *not* a deep analytical briefing. Headlines are
  presented as-is, not summarised or scored.
- This is *not* personalised. The HTML reflects the configured
  sources, not the user's interests.
- This is *not* an LLM-powered system. Zero LLM calls in the
  default configuration.

## Why this task matters

It is the simplest demonstration of multi-source aggregation in
a sense-and-respond framework. As a teaching artifact, it shows
that a useful S&R system can be built with zero agents and zero
LLM dependency — the orchestration framework alone provides
enough structure. As a precedent for Claudette, it teaches that
*sometimes the right design has no LLM calls at all*.
