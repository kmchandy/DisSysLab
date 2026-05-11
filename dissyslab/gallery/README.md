# Gallery

DisSysLab ships with two kinds of offices, in two folders:

- **[`apps/`](apps/)** — Pat-facing offices you can pick, install, and
  run as ready-to-use AI assistants. Each one has a README that
  explains what it does, how to set it up in a few minutes, and how
  to tweak / modify / build on it. Start here if you came for the
  product.

- **[`examples/`](examples/)** — Builder-facing tech demos. Smaller
  offices that showcase one pattern each — a sub-office, a custom
  role, a webhook listener, a multi-agent editorial chain. Useful
  when you're writing your own office and want to crib a pattern.

The same framework runs both. The split is documentation focus, not
technical capability.

---

## Apps for Pat

| App | What it does | Audience |
|---|---|---|
| [`apps/periodic_brief`](apps/periodic_brief/) | One markdown morning brief combining news + weather (and your calendar + email once you add credentials). The showpiece app for what multi-source AI orchestration can do. | Anyone who wakes up wanting to know what's going on. |
| [`apps/situation_room`](apps/situation_room/) | Morning intelligence digest from BBC + NPR + Al Jazeera. Severity, topics, locations, entities, briefings, editorial review. | Journalists, analysts, NGO staff, researchers, policy folks. |
| [`apps/situation_room_pro`](apps/situation_room_pro/) | Same office, but Riley (writer) runs on Claude while the four extractors stay on free Qwen. Demonstrates per-role backend mixing. | Anyone who'll pay a few cents/day for sharper briefings. |
| [`apps/weather_monitor`](apps/weather_monitor/) | Hourly plain-English weather briefing for a city you pick. The simplest possible office. | Anyone going outside. |
| [`apps/stocks_monitor`](apps/stocks_monitor/) | One-line read of a stock ticker's movement every few minutes. | Hobbyist investors. |
| [`apps/calendar_briefing`](apps/calendar_briefing/) | Reads your Google Calendar and writes a one-line briefing per upcoming event. | Anyone with a calendar. |

Run any of them with:

```bash
dsl run dissyslab/gallery/apps/<app_name>/
```

---

## Examples for Builders

The `examples/` folder is a library of patterns. Each office is small
on purpose — one moving part at a time, so you can read the office.md
and immediately see what's going on.

Notable patterns:

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
- **Build your own office** → [`docs/BUILD_APPS.md`](../../docs/BUILD_APPS.md).
- **Switch or mix backends** → [`docs/LANGUAGE_MODELS.md`](../../docs/LANGUAGE_MODELS.md).
- **Sources and sinks reference** → [`docs/SOURCES_AND_SINKS.md`](../../docs/SOURCES_AND_SINKS.md).
- **Why apps vs examples** → see the top of this file. Same framework;
  different documentation audience.
