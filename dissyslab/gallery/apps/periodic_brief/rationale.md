# Rationale: periodic_brief

This file explains *why* the office was designed the way it was.
It is what Claudette reads when she has identified periodic_brief
as a relevant precedent and wants to understand the reasoning
she should transfer to her new task.

The rationale is organised by design decision, with each
decision named, justified, and accompanied by the alternatives
that were considered and rejected.

---

## Decision 1 — No transformer agents

**Choice:** The office has zero agents between sources and sink.

**Why:** The task is *aggregation*, not *transformation*. The
sources already emit messages in a usable shape (headline +
url, weather observation, stock quote). The sink knows how to
arrange them into HTML sections. There is no information-
processing step in the middle that would justify an LLM call or
a custom Python transformer.

**Alternatives considered and rejected:**

- *Add a summariser agent for news headlines.* Rejected because
  headlines are already short; summarisation would add cost and
  latency without improving the artifact.
- *Add a classifier agent to bucket headlines by topic.* Rejected
  because the user wants a flat list, not a topic tree.
- *Add an alert agent for stock-price thresholds.* Rejected
  because the task is informational, not action-prompting.

**Generalisable lesson for Claudette:** *when sources already
emit data in the shape the sink wants, no transformer layer is
needed.* The diamond/pipeline template is optional, not
mandatory; the simplest correct design often has neither.

## Decision 2 — Multiple stocks aliases instead of a single agent

**Choice:** Three separate stock sources (`stocks`, `stocks_2`,
`stocks_3`), each watching one ticker, rather than one source
configured with three tickers.

**Why:** DSL's source registry uses parameterised aliases. A
single `stocks` source can take only one `ticker` argument; to
watch multiple tickers, the office uses multiple instances.
This is the registry's convention; the office follows it
rather than inventing a custom source that takes a ticker list.

**Alternatives considered and rejected:**

- *Build a custom `stocks_multi(tickers=...)` source.* Rejected
  for this office — adds custom code for marginal benefit.
  Defensible to invent if the office needed >5 tickers, where
  the alias approach becomes unwieldy.

**Generalisable lesson:** *prefer composing existing registered
sources over inventing new ones.* Inventing new components is
the right move only when the composition is genuinely awkward.

## Decision 3 — The sink does the routing

**Choice:** All six sources connect directly to one sink
(`periodic_brief_html_sink`). The sink internally routes each
incoming message to the appropriate HTML section based on the
message's `type` or `source` field.

**Why:** The integration logic (which message goes in which
HTML section) is presentation logic, not domain logic. Putting
it in the sink keeps the office.md trivial and the integration
logic close to where it is used. Six explicit connection lines
in office.md are clearer than four agents + one merger sink.

**Alternatives considered and rejected:**

- *Add a synchroniser that collects all six source outputs and
  passes a single combined dict to the sink.* Rejected because
  the sources arrive at different rates; a synchroniser would
  delay HTML rendering until the slowest source produced. The
  current design renders each source as it arrives.
- *Use a generic `intelligence_display` sink instead of a
  custom HTML sink.* Rejected because the user wants HTML, not
  terminal output, and the HTML structure (sections per
  modality) is specific enough to justify a dedicated sink.

**Generalisable lesson:** *when integration is essentially
presentation, push it into the sink.* Synchronisers earn their
place when downstream logic genuinely needs all inputs together;
they do not when each input can be rendered independently.

## Decision 4 — `max_articles` and `max_readings` bound source output

**Choice:** Each source has an explicit max parameter
(`max_articles=5`, `max_readings=1`).

**Why:** Without bounds, sources would emit messages
indefinitely (RSS feeds keep refreshing; APIs keep producing
new readings). The bounds give the office a clean termination
condition: each source emits at most N messages, then signals
completion, then the office terminates.

**Generalisable lesson:** *configurable per-source bounds make
the office finite by construction.* For on-demand artifacts
(this one), finiteness is the right default. For continuous
monitors, omit the bounds.

## Decision 5 — Self-refreshing HTML via `<meta refresh>`

**Choice:** The HTML sink emits a `meta refresh` tag so the
page reloads periodically when left open in a browser.

**Why:** The office is one-shot but the user may want a
"living" view. Cheap to add (one HTML tag), no infrastructure
needed (the browser handles the refresh), and degrades
gracefully (the tag is ignored if the user converts the HTML
elsewhere).

**Generalisable lesson:** *when a one-shot office could benefit
from looking continuous, browser features can fake continuity
without requiring server-side machinery.*

---

## Anti-patterns this office deliberately avoids

- *Adding LLM calls because LLMs are available.* If a task can
  be done with zero LLM calls, that is usually the right design
  for a teaching example.
- *Adding agents because the framework has them.* Agents are
  for transformation. If there is nothing to transform, the
  agent block is empty.
- *Making the sink generic.* A purpose-built sink for this
  specific HTML layout is clearer than a generic
  templated-output sink with twelve parameters.

---

## What Claudette should take from this example

If the new task involves *combining heterogeneous sources into
a single periodic artifact*, periodic_brief is the precedent.
The pattern transfers as:

1. List the sources the user wants integrated.
2. Pick a sink that emits the desired artifact shape.
3. Add agents only if some transformation is needed before the
   sink sees the data.
4. Default to "no agents" first; add only when forced.

The simplest design that works is usually the right starting
point. Claudette can elaborate later if the artifact is
inadequate.
