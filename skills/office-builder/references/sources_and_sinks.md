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

## Snapshot (dissyslab 1.6.1 — 42 sources, 24 sinks)

### Sources

**News and feeds** — `bbc_world`, `bbc_tech`, `npr_news`, `al_jazeera`,
`techcrunch`, `mit_tech_review`, `venturebeat_ai`, `nasa_news`,
`hacker_news`, `rss` (any feed URL), `bluesky`

**Research** — `arxiv_cs_ai`, `arxiv_cs_cl`, `arxiv_cs_cv`, `arxiv_cs_lg`,
`arxiv_cs_ro`

**Jobs** — `python_jobs`, `remoteok`, `we_work_remotely`

**Markets and weather** — `stocks`, `stocks_2` … `stocks_5` (one per ticker),
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

### Also in the repo, not yet in 1.6.1

Sources `csv_stock_history`, `stock_history`, `synthetic_stock_history`,
`session_starter` (+ `_2`, `_3`), `passthrough`, `arg_map`; sinks
`report_html`, `tutor_session_display`. Run the live query above to see what
the user's install actually has.

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

**Credentials.** `gmail`, `calendar`, `slack_sink`, `weatherapi` and the
market sources need credentials; `bbc_world`, `npr_news`, `weather`,
`stocks` and the file sources do not. `periodic_brief` runs with no key at
all, which makes it the right first thing to show someone. If a source fails
to authenticate, run `dsl doctor`.

**Empty output is now an error.** A source that produces nothing raises
`OfficeRunError` rather than exiting 0, because an all-zero result that looks
like success is worse than a crash. When producing nothing is legitimate — a
feed with nothing new — mark the source `allow_empty=true`.
