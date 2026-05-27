# arxiv_radar

**Tags:** single-agent, single-office, scientific

A minimal office that monitors three arXiv subject feeds (cs.AI,
cs.LG, cs.CL) for new papers, classifies each by type, rates its
likely impact, and prints the result to the terminal.

The intent of this gallery app is to show that the same office
pattern as `situation_room` works for an entirely different domain
— academic research — with only the role files changed. The bones
are deliberately minimal: three sources, two enrichment agents in
a sequential pipeline, one sink. There is no topic filter, no
deduplicator, no daily digest. Pat can add any of those by
dropping the appropriate role files into this office's `roles/`
folder and editing `office.md`.

## Run

```bash
dsl run arxiv_radar
```

You will see one card per recent paper:

```
[arxiv_cs_lg] ...title...
   paper_type: EMPIRICAL
   impact:     MEDIUM
   reason:     ...
```

Cost is small (~3 papers per category × 2 LLM calls per paper × 3
categories = 18 LLM calls per run). At Claude Sonnet pricing,
that's a few cents per run.

## How it is wired

```
arxiv_cs_ai ─┐
arxiv_cs_lg ─┼→ Carla (paper_classifier) → Iris (impact_rater) → intelligence_display
arxiv_cs_cl ─┘
```

The three sources fan in to Carla. Each paper passes through Carla
and then Iris, picking up a `paper_type` field and then an `impact`
+ `reason` field. The display sink prints whatever it receives.

## Customising

- **Change which categories to watch.** Edit the `Sources:` line
  in `office.md`. The framework ships `arxiv_cs_ai`, `arxiv_cs_lg`,
  `arxiv_cs_cl`, `arxiv_cs_cv`, `arxiv_cs_ro`.
- **Tune the classifier or impact criteria.** Edit
  `roles/paper_classifier.md` or `roles/impact_rater.md` directly.
  The English you write is the LLM prompt the framework hands to
  the model.
- **Add a topic filter.** Drop a `roles/topic_filter.md` (use
  `dsl show relevance_filter` as a starting point), add `Mara is a
  topic_filter.` to the Agents section, and rewire the connections
  to pass each paper through Mara before Carla.
- **Add a daily digest.** Wire a `synchronizer` + a custom
  `report_writer` role + an `intelligence_display` sink. See
  `situation_room` for the multi-agent shape.

## Compare to the Python equivalent

A more elaborate Python implementation of the same idea lives at
[`examples/python_offices/arxiv_tracker/`](../../examples/python_offices/arxiv_tracker/).
That version adds a topic filter, a daily batcher, and a written
research digest. This gallery office is intentionally simpler: it
shows the framework primitives without distractions.
