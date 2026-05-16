# Gallery

DisSysLab ships with two kinds of offices, organised two ways:

- **By audience:** [`apps/`](apps/) is Pat-facing; [`examples/`](examples/)
  is Builder-facing tech demos.
- **By setup cost:** apps fall into two tiers depending on whether
  Pat needs to add API keys before they produce output. See the
  two tables below.

The same framework runs everything in here — `dsl run <office_name>`
from any directory.

> **About cost safety.** Every office in this gallery stops after a
> few polling cycles by default — long enough to see a real result,
> short enough that you won't run up a bill by mistake. Each office's
> `office.md` exposes the safety brakes as `max_articles=N` or
> `max_readings=N`. Remove them only when you mean for an office to
> run continuously.
>
> Any specific cost or runtime figures below are rough estimates,
> likely to change as providers update their pricing.

---

## Apps that run on any laptop, no keys

These apps make zero or at most one LLM call per cycle. Pat installs
DisSysLab via the curl one-liner and runs them immediately. No API
keys, no third-party signups. On a typical Mac with Ollama, you see
output in seconds.

| App | What it does | Why it's fast |
|---|---|---|
| [`periodic_brief`](apps/periodic_brief/) | Morning briefing combining BBC + NPR news, Pasadena weather, and stock tickers (AAPL, NVDA, MSFT) into one HTML page. | Zero LLM calls. Pure orchestration of public APIs into a styled brief. |
| [`weather_monitor`](apps/weather_monitor/) | Hourly plain-English weather briefing for a city you pick. | One LLM call per reading; ~30 s on Ollama, instant on OpenRouter. |
| [`stocks_monitor`](apps/stocks_monitor/) | One-line read of a stock ticker's movement every few minutes. | One LLM call per reading; same latency as weather_monitor. |

Start with `periodic_brief` — it's the cleanest demo of the
framework's value (multi-source orchestration, structured output)
without any LLM dependency to slow it down.

---

## Apps that shine on a hosted backend

These apps make many LLM calls per cycle and/or talk to APIs that
need credentials (Google Calendar, Gmail, Slack, your CRM). On
local Ollama they take 15–60 minutes per cycle. On OpenRouter with
the default Qwen-2.5-7B model (`~5 minute setup, pennies per run`)
they take 1–5 minutes — fast enough for an interactive demo.

| App | What it does | Setup needed |
|---|---|---|
| [`periodic_brief_pro`](apps/periodic_brief_pro/) | Same idea as `periodic_brief` plus a sense → think → respond news pipeline (entity / topic / urgency tagging, then a writer composing per-article briefs), plus Google Calendar, plus Gmail. The richest single-page brief. | OpenRouter or Claude key; `CALENDAR_ICS_URL`; `GMAIL_USER` and `GMAIL_APP_PASSWORD`. |
| [`situation_room`](apps/situation_room/) | Three news feeds → dedupe → four parallel thinkers (entity, severity, topic, geo) → synchronizer → writer → evaluator → terminal + JSONL archive. The framework's canonical s→t→r demo. | OpenRouter or Claude key recommended. |
| [`situation_room_pro`](apps/situation_room_pro/) | Same office, Claude as the writer for top-quality briefings, open-weight Qwen (Ollama or OpenRouter) for the four extractors. Demonstrates per-role backend override. | Anthropic key, plus your usual `DSL_BACKEND` (Ollama or OpenRouter) for the cheaper roles. |
| [`inbox_triage`](apps/inbox_triage/) | Watches Gmail; rates each unread email by urgency + sentiment, summarises it, drops a digest of keepers into Slack. | OpenRouter or Claude key; `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `SLACK_WEBHOOK_URL`. |
| [`ticket_router`](apps/ticket_router/) | Listens on a webhook for support tickets; classifies severity + urgency + category; posts the keepers to an oncall Slack channel. | OpenRouter or Claude key; `SLACK_ONCALL_WEBHOOK`. |
| [`competitor_watch`](apps/competitor_watch/) | Watches BBC Tech + TechCrunch + VentureBeat AI; annotates each article with entities + sentiment + topic; writes a daily markdown digest. | OpenRouter or Claude key. No third-party signups beyond that. |
| [`lead_qualifier`](apps/lead_qualifier/) | Listens on a webhook for form submissions; summarises each lead + tags sentiment and urgency; forwards qualified leads to your CRM via outbound webhook. | OpenRouter or Claude key; `CRM_WEBHOOK_URL`. |
| [`new_grad_jobs`](apps/new_grad_jobs/) | Watches Hacker News' Who's Hiring thread; screens postings for entry-level / new-grad fit; reformats matches as structured briefs. | OpenRouter or Claude key (hundreds of postings × 2 LLM calls). |

Each app's own README documents which env vars to export and what
to expect for runtime and cost.

---

## Examples for Builders

The [`examples/`](examples/) folder is a library of patterns. Each
office is small on purpose — one moving part at a time, so you can
read the office.md and immediately see what's going on.

| Office | Pattern |
|---|---|
| [`examples/my_first_office`](examples/my_first_office/) | Single-agent Hacker News briefer. The simplest possible office. |
| [`examples/org_news_editorial`](examples/org_news_editorial/) | Two-agent editorial chain — analyst feeds editor. |
| [`examples/org_two_office_news`](examples/org_two_office_news/) | An office of offices — `news_monitor` feeds `news_editor`. |
| [`examples/org_intelligence_briefing`](examples/org_intelligence_briefing/) | Multi-source feed with significance filtering and briefing. |
| [`examples/org_news_filter`](examples/org_news_filter/) | Filter pipeline — drop articles that don't match criteria. |
| [`examples/org_situation_room`](examples/org_situation_room/) | The older two-agent variant of `apps/situation_room`, kept as a reference for the simpler pattern. |
| [`examples/webhook_listener`](examples/webhook_listener/) | HTTP source — listens on `localhost:8000/webhook` for POSTs. |
| [`examples/web_monitor`](examples/web_monitor/) | Page-watching via the MCP web source. |
| [`examples/gmail_monitor`](examples/gmail_monitor/) | Pulls unread mail from Gmail (requires App Password). |

---

## Where to go next

- **First-time setup** → [`../README.md`](../../README.md) (top-level
  README with the one-line installer).
- **The pattern most Pat-facing offices follow** →
  [`docs/PATTERN_sense_think_respond.md`](../../docs/PATTERN_sense_think_respond.md).
- **Build your own office** → [`docs/BUILD_APPS.md`](../../docs/BUILD_APPS.md).
- **Switch or mix backends** → [`docs/LANGUAGE_MODELS.md`](../../docs/LANGUAGE_MODELS.md).
- **Sources and sinks reference** → [`docs/SOURCES_AND_SINKS.md`](../../docs/SOURCES_AND_SINKS.md).
