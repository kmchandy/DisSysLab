# Periodic Brief

> A single HTML page each morning combining news, weather, and
> stock tickers. No keys, no LLM calls — runs in about ten
> seconds on any laptop with DisSysLab installed.

`periodic_brief` is the simplest demonstration of what DisSysLab
does: it orchestrates multiple sources into one structured
artifact. News headlines from BBC and NPR, today's weather for a
city of your choice, and today's quotes for a few stock tickers —
all rendered into a single self-contained `brief.html` file you
open in your browser, drag into Notion, or email to yourself.

Out of the box: zero LLM calls, zero credentials, zero waiting.
When you want richer features (per-article analysis, calendar,
Gmail), there's a `periodic_brief_pro` next door that adds those
in exchange for an API key or two.

## Run it

```bash
dsl run periodic_brief
open brief.html
```

About ten seconds later, your browser opens a styled HTML brief
with three sections: Markets (stock tickers), Weather (current
conditions for the configured city), and News (recent headlines
from BBC and NPR). The page has a `meta refresh` tag, so if you
leave it open it reloads every minute as the office continues
polling.

## What's in the office

Open [`office.md`](office.md). It's about ten lines:

```
Sources: bbc_world(max_articles=5), npr_news(max_articles=5),
         weather(city="Pasadena", max_readings=1),
         stocks(ticker="AAPL", max_readings=1),
         stocks_2(ticker="NVDA", max_readings=1),
         stocks_3(ticker="MSFT", max_readings=1)
Sinks: periodic_brief_html_sink(path="brief.html")

Connections:
bbc_world's destination is periodic_brief_html_sink.
npr_news's destination is periodic_brief_html_sink.
weather's destination is periodic_brief_html_sink.
stocks's destination is periodic_brief_html_sink.
stocks_2's destination is periodic_brief_html_sink.
stocks_3's destination is periodic_brief_html_sink.
```

Six sources, one sink. Every source emits messages with a
recognisable `type` or `source` field; the HTML sink routes each
into the right section of the page. There are *no agents* in this
default config — that's why it's instant, no LLM dependency.

## Make it yours

**Change the city.** Edit the `weather(...)` argument:

```
weather(city="San Francisco", max_readings=1)
```

Use the city's English name with proper spacing — Open-Meteo's
geocoder is strict.

**Change the stock tickers.** Replace `AAPL` / `NVDA` / `MSFT`:

```
stocks(ticker="TSLA", max_readings=1),
stocks_2(ticker="META", max_readings=1),
stocks_3(ticker="GOOGL", max_readings=1)
```

For more than five tickers, ask in an issue — we ship
`stocks` through `stocks_5` as aliases out of the box.

**Change the news feeds.** Replace `bbc_world` / `npr_news` with
any combination from the built-in source library: `al_jazeera`,
`techcrunch`, `mit_tech_review`, `venturebeat_ai`, `hacker_news`,
`python_jobs`, `bbc_tech`, `nasa_news`.

**Change where the brief goes.** Drop the HTML sink, use markdown
or terminal output:

```
Sinks: periodic_brief_sink(path="brief.md")   # markdown version
# or
Sinks: console_printer                         # terminal stream
```

## What you should expect

- **Quality:** news headlines pass through verbatim; weather is a
  factual one-liner from Open-Meteo; stock quotes come straight
  from Stooq. Nothing here is AI-generated.
- **Speed:** about 10 seconds end-to-end. Pat opens her laptop, runs
  `dsl run periodic_brief`, the page is ready before her coffee.
- **Cost:** $0. No API keys.

## Schedule it

For a daily brief at 6am, add this to your crontab (`crontab -e`):

```
0 6 * * *  cd /Users/you/Documents/DisSysLab && dsl run periodic_brief > /tmp/dsl.log 2>&1
```

At 6am every day, the brief regenerates. Open `brief.html` to
read it. Optionally chain a `osascript` or `xdg-open` call after
to open it for you.

## Want more?

[`periodic_brief_pro`](../periodic_brief_pro/) is the upgraded
version. It adds a sense → think → respond news pipeline (each
article gets entity / topic / urgency tagged, then a writer
composes a brief per article), plus your Google Calendar, plus
unread Gmail. The trade-off is setup time and inference cost —
see that office's README for the keys you need and the runtime
expectations.

## See also

- [`office.md`](office.md) — the wiring (ten lines).
- [`periodic_brief_pro`](../periodic_brief_pro/) — the LLM-enabled
  upgrade.
- [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
  — the design pattern that periodic_brief_pro instantiates for
  its news pipeline.
