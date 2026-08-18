# Sources and sinks

## Get the live list first

This file goes stale; the registry does not. Before telling a user something
does or does not exist, ask the installed package:

```bash
python3 -c "
from dissyslab.office import utils
for n in ('SOURCE_REGISTRY','SINK_REGISTRY'):
    r = getattr(utils, n, {})
    print(f'--- {n} ({len(r)}) ---'); print('\n'.join(sorted(r)))
"
```

The full prose catalogue, with each component's arguments and message shapes, is
`docs/SOURCES_AND_SINKS.md` in the repo. Read it before writing a custom
source — the answer is usually already there.

## Snapshot (dissyslab 1.7.2 — 46 sources, 26 sinks)

### Sources

**News and feeds** — `bbc_world`, `bbc_tech`, `npr_news`, `al_jazeera`,
`techcrunch`, `mit_tech_review`, `venturebeat_ai`, `nasa_news`,
`hacker_news`, `rss` (any feed URL), `bluesky`

**Research** — `arxiv_cs_ai`, `arxiv_cs_cl`, `arxiv_cs_cv`, `arxiv_cs_lg`,
`arxiv_cs_ro`

**Jobs** — `python_jobs`, `remoteok`, `we_work_remotely`

**Markets and weather** — `stocks`, `stocks_2` … `stocks_5` (one per ticker,
needs `pip install "dissyslab[market]"`),
`kalshi`, `weather`, `weatherapi`

**Media and sensors** — `image_folder`, `audio_folder`, `audio_clip`,
`audio_mic`

**Files and the web** — `file_source`, `csv_points_source`, `web`,
`web_scraper`, `search`

**Personal** — `gmail`, `calendar`

**Plumbing** — `webhook` (listens for POSTs), `console_input`, `starter`
(emits one message to kick off a loop), `mcp_source` (any MCP server)

### Sinks

**Display** — `console_printer`, `intelligence_display`, `debate_display`

**Files** — `jsonl_recorder` and its named variants (`_briefing`, `_archive`,
`_raw`, `_discard`), `markdown_digest`, `periodic_brief_sink`,
`periodic_brief_html_sink`, `job_html_sink`

**Messaging** — `slack_sink` (+ `_alerts`, `_archive`, `_briefing`),
`gmail_sink` (+ `_match`, `_research`, `_tailor`, `_cover_letter`),
`webhook_sink`

**Other** — `mcp_sink` (any MCP server), `discard` (throw it away, explicitly)

**History** — `csv_stock_history` (reads local CSV files; see the market
note below)

### Removed in 1.7.2

`stock_history` and `synthetic_stock_history`. The first read Stooq's
historical endpoint, which stopped serving data; the second was a stand-in
while that was broken. Use `csv_stock_history` and download your own data.
If a user's `office.md` names either one, `dsl check` reports it as W5 with
a suggestion — that is the fix, not a reason to reinstate them.

## Sink arguments

Names alone are not enough — a sink you cannot configure is a sink you
will configure wrongly. These are the constructor signatures, so you do
not have to guess. Everything after the first argument is optional.

| Sink | Arguments |
|---|---|
| `console_printer` | `verbose=False` |
| `discard` | *(none)* |
| `jsonl_recorder` *(and `_briefing`, `_archive`, `_raw`, `_discard`)* | `path="anomaly_stream.jsonl"`, `mode="w"`, `flush_every=1`, `ensure_ascii=False`, `sort_keys=False` |
| `markdown_digest` | `path="morning_digest.md"`, `mode="w"`, `title=None` |
| `periodic_brief_sink` | `path="brief.md"`, `title=None` |
| `periodic_brief_html_sink` | `path="brief.html"`, `title=None`, `accent_color="#3b82f6"`, `auto_refresh=True`, `print_to_console=True`, `auto_open=True` |
| `job_html_sink` | `path="matched_jobs.html"`, `max_items=50`, `title="Job Matches"` |
| `report_html` | `path="report.html"`, `title="Backtest Report"` |
| `intelligence_display` | `max_items=None` |
| `debate_display` | `show_reasoning=True`, `max_reasoning_lines=4` |
| `slack_sink` *(and `_alerts`, `_archive`, `_briefing`)* | `webhook_url_env="SLACK_WEBHOOK_URL"`, `username=None`, `icon_emoji=None`, `timeout=5.0` |
| `gmail_sink` *(and `_match`, `_research`, `_tailor`, `_cover_letter`)* | `to` **(required)**, `subject="DisSysLab Alert"`, `user_env="GMAIL_USER"`, `password_env="GMAIL_APP_PASSWORD"` |
| `webhook_sink` | `url=None` *or* `webhook_url_env=None`, `headers=None`, `timeout=10.0`, `retry_count=3` |
| `mcp_sink` | `server`, `tool`, `args=None`, `auth_env_var=None` |

Two that bite:

- **`title` defaults to a date-stamped "Morning digest"** on
  `markdown_digest` and the brief sinks. Correct for a morning brief,
  wrong on anything else. Set it.
- **A bare `path` is relative to the office folder**, not to where the
  user typed the command — `build/run.py` chdirs there first. That is
  usually what you want, and it means running a *shipped* gallery office
  in place writes into `site-packages`. `dsl init` first.

To confirm any of the above against the actual install, ask it:

```bash
python3 -c "
import inspect, importlib
from dissyslab.office.utils import SINK_REGISTRY
e = SINK_REGISTRY['markdown_digest']
m = e['import'].replace('from ','').split(' import ')[0]
print(inspect.signature(getattr(importlib.import_module(m), e['class']).__init__))
"
```

## Notes that save time

**Why numbered variants exist.** `stocks`, `stocks_2`, `stocks_3` … are
separate registry entries because each source instance is one declaration.
Watching three tickers means three sources, not one with three arguments:

```
Sources: stocks(ticker="AAPL", max_readings=1),
         stocks_2(ticker="NVDA", max_readings=1),
         stocks_3(ticker="MSFT", max_readings=1)
```

The same applies to `jsonl_recorder`, `slack_sink`, and `gmail_sink` variants —
use a distinct name per destination.

**`discard` is a real sink.** Routing a filter's rejects to `discard` is how
you say "deliberately dropped" rather than leaving an outport unwired. An
unwired outport is a fault; `discard` is a decision.

**But `discard` also destroys your only evidence.** A filter that drops the
wrong thing produces an office that checks clean, runs clean, and answers
wrong — and there is nothing left to look at, because the dropped messages
went to `discard`. `dsl check` cannot catch this; nothing can. A regex of
`\bneural operator\b` silently dropped every paper titled "Neural Operators",
and the only way to see it was to look at what was rejected.

**So while you are developing, send rejects somewhere readable:**

```
Sinks: jsonl_recorder_keep(path="kept.jsonl"),
       jsonl_recorder_discard(path="rejected.jsonl")

Felix's keep is jsonl_recorder_keep.
Felix's discard is jsonl_recorder_discard.
```

Now the mistake is a file you can open. `examples/org_news_filter` is built
this way; copy the shape. Switch to `discard` when you are confident the
criterion is right — or never, since a rejects file costs almost nothing.

This is the general rule, and it is worth stating as one: **you cannot
automate a check for "the answer is wrong", so build offices whose wrong
answers are visible.** Anywhere a message is dropped, filtered, deduplicated,
or defaulted, ask what a student would look at to find out it happened.

**`rss` takes any feed.** Before asking for a new named source, check whether
`rss(url=...)` covers it.

**`mcp_source` / `mcp_sink`.** Any tool with an MCP server — a filesystem,
GitHub, a search provider — can be an office's input or output. This is
usually the answer when a user wants to connect something the registry has
never heard of.

**Credentials.** `gmail`, `calendar`, `slack_sink` and `weatherapi` need
credentials; `bbc_world`, `npr_news`, `weather` and the file sources do not.
`periodic_brief` runs with no key and no optional install at all, which makes
it the right first thing to show someone. If a source fails to authenticate,
run `dsl doctor`.

**Market data is an optional install, and users fetch their own.** `stocks`
needs `pip install "dissyslab[market]"` (yfinance). `csv_stock_history` needs
no extra install to *read* — but the script that produces the files it reads
does.
Say so *before* writing an office that uses them, and never install it
without asking. Nothing in the package ships prices: Yahoo's terms do not
permit redistributing them, so backtests read local CSVs the user downloads
once with
`gallery/apps/mac_speed_suite/download_stock_history_from_yf.py`. If a
`stocks` source produces nothing but `stocks_error`, read the run summary —
it prints the source's own reason, and "yfinance is not installed" is the
usual one.

**Empty output is now an error.** A source that produces nothing raises
`OfficeRunError` rather than exiting 0, because an all-zero result that looks
like success is worse than a crash. When producing nothing is legitimate — a
feed with nothing new — mark the source `allow_empty=True`.

**And so is output that is entirely error reports.** A source that catches a
bad fetch and emits `{"type": "<name>_error", ...}` stays alive through a
transient failure, which is right — but it *sent* messages, so the check above
used to be satisfied, and sinks ignore types they don't recognise, so nothing
printed. Three HTTP 404s from `stocks` once produced a clean, silent, empty
morning brief that reported success. A source whose output is *all* errors is
now as loud as a dead one; a source with *some* errors is reported in the run
summary without failing the run. Read the summary's `errors` column — it only
appears when it is non-zero.
