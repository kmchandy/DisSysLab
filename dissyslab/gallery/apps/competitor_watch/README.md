# Competitor Watch

> An office that monitors three tech-news feeds for mentions of
> companies and topics you care about, annotates each article
> with entities + sentiment + topic, and writes a daily markdown
> digest.

A sense → think → respond office. Articles from BBC Tech,
TechCrunch, and VentureBeat AI pass through three parallel
thinkers — `entity_extractor`, `sentiment_classifier`,
`topic_tagger` — then a `summary_writer` composes a brief paragraph
per article. Output goes into `competitors.md`, which you can open
in any markdown viewer or check in to git for tracking.

## Set it up

This office uses only public RSS feeds — no third-party
credentials needed. You only need an LLM backend:

```bash
# OpenRouter (recommended) — a few cents per run
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...

# OR: Anthropic Claude — pennies per role per article
export DSL_BACKEND=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# OR: local Ollama (free, but slow — 15–30 min per run)
# This is the default if no key is set
```

## Run it

```bash
dsl run competitor_watch
```

After ~2 minutes on OpenRouter (or 15–30 minutes on Ollama), open
`competitors.md` to see the day's annotated briefings.

## What you should expect

- **Quality:** entity extraction is good for prominent companies;
  weaker for novel startups (the underlying small models haven't
  seen their names). Sentiment is reliable on opinion-shaped
  articles; less useful on pure factual reporting.
- **Speed:** ~2 min on OpenRouter (Qwen-2.5-7B), 15–30 min on local Ollama.
- **Cost:** under 1 cent per run on OpenRouter for ~30 articles.

## Make it yours

The office's default thinkers (entity, sentiment, topic) give you
a generic competitor-watch. To track *specific* companies or
products you care about, write a local relevance filter and put it
in `roles/relevance_filter.md` in this office. See
[`dissyslab/roles/relevance_filter.md`](../../../roles/relevance_filter.md)
for the base prompt to copy.

Edit [`office.md`](office.md):

- **SLOT 1 (sources):** swap or add feeds — Hacker News
  (`hacker_news`), MIT Tech Review (`mit_tech_review`), specific
  RSS via `web_scraper(url=...)`.
- **SLOT 2 (thinkers):** drop one if you don't need it, or add
  `urgency_classifier`.
- **SLOT 3 (writer):** customize the brief style — *"competitor
  digest in Slack-message format"* vs *"executive memo"*.
- **SLOT 4 (sinks):** drop `markdown_digest`, use `slack_sink_briefing`
  or `gmail_sink` instead.

See [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for the pattern.
