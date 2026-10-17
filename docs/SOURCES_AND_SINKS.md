# Sources and Sinks Reference

Offices in DisSysLab have **sources**, where messages come in, and
**sinks**, where results go out. This
page lists every source and sink shipped with the framework, what
each one accepts, and how to connect it in `office.md`.
You can also build your own sources and sinks.

For new users, start with the [Getting Started
guide](GETTING_STARTED.md) and the gallery (`dsl list`); come back
here once you want to swap in a different source or send results
somewhere new.

**Conventions used below.**
- Each entry shows a usage example **as it appears in `office.md`**.
  Every example was checked by building the component from exactly
  those arguments.
- Optional arguments show their defaults.
- "Setup" notes describe credentials or installations needed for
  the source/sink to run.

---

## Sources

A source sends messages into an office. Sources are declared under
`sources:` in `office.md`; a source with no name in front is named
after its kind (`bbc_world`), and two of the same kind need two names
(`world: bbc_world`, `tech: bbc_tech`).

### `rss` — any RSS or Atom feed at all (no key)

**Start here.** If a site publishes a feed, you can read it, and you
do not need us to add it. Pass the URL:

```
sources:
    rss(url="https://example.com/feed.xml", name="my_feed", max_articles=5)
```

`name` is what the feed calls itself in each message's `source`
field and in the run summary — pick something you will recognise.
The named feeds in the next section are shortcuts for this: same
implementation, URL filled in.

Nothing about adding a feed requires editing the framework. If you
find yourself about to, you want `rss(url=...)`.

### RSS feeds (12 named, no key)

Twelve named feeds share the `rss` implementation above, with the URL
already filled in. Each is free and public; no signups, no API keys.

| Name in `office.md` | What it streams                         |
|---------------------|-----------------------------------------|
| `hacker_news`       | Hacker News newest items                |
| `al_jazeera`        | Al Jazeera world news                   |
| `bbc_world`         | BBC World News                          |
| `bbc_tech`          | BBC Technology                          |
| `npr_news`          | NPR top stories                         |
| `techcrunch`        | TechCrunch                              |
| `mit_tech_review`   | MIT Technology Review                   |
| `venturebeat_ai`    | VentureBeat AI                          |
| `nasa_news`         | NASA breaking news                      |
| `python_jobs`       | python.org jobs board                   |
| `remoteok`          | RemoteOK job listings                   |
| `we_work_remotely`  | We Work Remotely job listings           |

**Arguments (all optional):**
- `max_articles` *(int)* — how many articles per fetch. Defaults
  vary by feed (10–20). Set lower for quick tests.
- `poll_interval` *(int seconds)* — if set, the source re-fetches
  every N seconds and runs forever. If omitted, fetches once and
  stops.

**Example `office.md`:**
```
sources:
    hacker_news(max_articles=20)
    bbc_world(max_articles=10, poll_interval=600)
```

**Each message yielded:**
```python
{
    "source":    "hacker_news",   # the feed name
    "title":     "...",
    "text":      "...",            # article summary
    "url":       "...",
    "timestamp": "..."             # ISO 8601
}
```

### `console_input` — one line from stdin per step

Reads a single line with Python's `input()` when stdin is a TTY
(local `dsl run` in a terminal). Pairs naturally with
`console_printer`.

**Arguments:**
- `prompt` *(str, default `""`)* — passed to `input(prompt)`.
- `default_message` *(str, default `None`)* — when stdin is **not**
  interactive (for example the custom app runs the office with
  closed stdin), the source emits this string **once**, then stops.
  You can also set the environment variable `OFFICE_CONSOLE_INPUT`
  instead of `default_message`.

**Example `office.md`:**
```
sources:
    console_input(default_message="Summarize the weather for Pasadena.")
sinks:
    console_printer
agents:
    Alex: summarizer
connections:
    console_input -> Alex -> console_printer
```

### `weather` — current weather for any city (no key)

Polls the free [Open-Meteo](https://open-meteo.com/) API. No
signup, no key.

**Arguments:**
- `city` *(str, default `"Pasadena"`)* — plain-English city name.
- `poll_interval` *(int seconds, default `3600`)* — one hour by
  default. Open-Meteo allows ~10k requests/day.
- `max_readings` *(int, default `None`)* — stop after N readings.
  Set small for tests; leave `None` to run forever.

**Example `office.md`:**
```
sources:
    weather(city="London", poll_interval=600)
```

### `stocks` — live ticker prices (needs `dissyslab[market]`)

Polls Yahoo Finance through [yfinance](https://pypi.org/project/yfinance/)
and yields one price reading per poll.

> **You install this one, and you fetch your own data.** yfinance is not
> part of `pip install dissyslab`:
>
> ```
> pip install "dissyslab[market]"
> ```
>
> Yahoo's terms do not permit redistributing their market data, so this
> project ships none of it — no prices, no cached quotes, no sample
> market CSVs. Every user fetches their own. That is the condition on
> which the data is available, not an obstacle to route around.
>
> Until 2026-08-18 this source read Stooq, which needed no install and no
> key. Stooq's quote endpoint was removed and its history endpoint now
> answers with a JavaScript browser challenge. Yahoo's endpoints are
> unofficial too; yfinance is a maintained community wrapper around them,
> and it will occasionally need upgrading.

Tickers are written the way Yahoo writes them: `"AAPL"`, `"BP.L"`,
`"7203.T"`. A trailing `.us` (the old Stooq convention) is stripped, so
`office.md` files written against the previous version still work.

**Arguments:**
- `ticker` *(str, default `"AAPL"`)*.
- `poll_interval` *(int seconds, default `300`)* — Yahoo is not a
  subscription feed. Polling it hard earns a rate limit, and no briefing
  needs tick data.
- `max_readings` *(int, default `None`)* — `None` polls forever.

**Example `office.md`:**
```
sources:
    stocks(ticker="AAPL", poll_interval=300, max_readings=1)
```

**Each message yielded:**
```python
{
    "type":           "stocks",
    "ticker":         "AAPL",
    "market":         "NMS",
    "price":          305.59,
    "open":           306.21,
    "high":           307.66,
    "low":            302.94,
    "previous_close": 305.77,
    "change":         -0.18,     # against the previous close
    "change_pct":     -0.059,
    "currency":       "USD",
    "market_date":    "2026-08-18",
    "market_time":    "03:41:02",
    "timestamp":      "2026-08-18T03:41:02+00:00",
}
```

A failed fetch yields `{"type": "stocks_error", "error": ...}` and keeps
polling, so one bad request does not end the office. The run summary
counts those messages: if *every* message a source sends is an error, the
run fails loudly and prints the source's own reason — including the
`pip install` line if the cause is simply that yfinance is missing.

### Historical daily prices — `csv_stock_history`, and how to get the data

There is one history source, and it reads local files. Two earlier ones,
`stock_history` and `synthetic_stock_history`, were removed on 2026-08-18:
the first read Stooq's historical endpoint, which no longer serves data,
and the second existed only as a stand-in while the first was broken.
Neither was used by any office.

To backtest, download your own data once and read it from disk. Ask
your assistant — *"download ten years of prices for NVDA and AMD"* —
or run it yourself:

```bash
pip install "dissyslab[market]"
dsl fetch-prices NVDA AMD --years 10
dsl fetch-prices --office my_backtest    # or: the basket an office asks for
```

`dsl fetch-prices` works from anywhere and needs no clone. Files already
present are left alone; pass `--force` to replace them. When it takes
the basket from an office it finishes by loading each ticker back
through the office's own source, so you find out immediately if the
fetch and the read disagree rather than from an office that runs and
produces nothing.

That script reads the ticker list and the filename pattern straight out
of `office.md`, so the download always matches what the office expects.
Prices are split- and dividend-adjusted and written as plain
`Date,Open,High,Low,Close,Volume` CSV.

**Where the files go.** One directory, shared by every office:
`$DSL_MARKET_DATA` if you set it, otherwise `~/.dissyslab/market_data`.
A download made once serves every office that names the ticker, and it
serves it identically whether you cloned the repository or ran
`dsl init`. An older checkout with prices in `<repo>/sp100_data` keeps
working — that layout is still searched — but new downloads go to the
standard place.

Separating *fetch* from *read* is not only a licensing matter. A backtest
that re-downloads on every run is slow, non-reproducible, and at the
mercy of a vendor's uptime; one that reads a file on disk gives the same
answer today and next month.

### `csv_stock_history` — real daily prices from local CSV files (no network, no key)

Third option alongside `stock_history` (live Stooq fetch, currently
404ing) and `synthetic_stock_history` (fake data): reads one CSV file
per ticker from a local directory and yields it in the exact same
`stock_history` message shape, so a backtest office built against
synthetic data can point at this instead with no downstream changes.

Each file needs a header row and, case-insensitively, `Date`, `Open`,
`High`, `Low`, `Close` columns (`Volume` optional; `Adj Close`, if
present, is ignored — `Close` is used throughout, matching the other
two stock-history sources). A ticker whose file is missing or
unparseable lands in the output's `errors` dict instead of crashing
the whole batch.

**Arguments:**
- `tickers` *(list of str, required)*.
- `directory` *(str, optional — leave it out)*. Omitted, the source
  reads the shared market-data directory described above, which is the
  same before and after `dsl init`. Give it only for data you keep
  somewhere of your own.

  **Why the default exists.** A relative `directory` is counted from
  the office's folder (see `jsonl_recorder`'s `path` below), so an office
  that names one breaks the moment `dsl init` copies it somewhere else.
  The shared directory is the same wherever the office is.
- `filename_pattern` *(str, default `"{ticker}_1year.csv"`)* — must
  contain `{ticker}`.
- `start` / `end` *(str, default: no bound)* — optionally filter rows
  to a date range after loading.

**Example `office.md`:**
```
sources:
    prices: csv_stock_history(tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"], filename_pattern="{ticker}_10_year.csv")
```

### `bluesky` — live BlueSky posts (no key)

Streams posts from BlueSky's public Jetstream WebSocket. Posts
arrive the moment they're published — seconds apart during
breaking events.

**Arguments:**
- `max_posts` *(int, default `100`)* — stop after this many. Pass
  `max_posts=None` to run forever.
- `lifetime` *(int seconds, default `None`)* — stop after this
  many seconds.
- `filter_keywords` *(list of str, default `None`)* — only yield
  posts containing one of these keywords (case-insensitive).
- `language` *(str, default `"en"`)*.
- `min_text_length` / `max_text_length` *(int, default 20 / 2000)*
  — skip posts shorter or longer than these.

**Setup:** `pip install websocket-client` (one-time).

**Example `office.md`:**
```
sources:
    bluesky(max_posts=None, lifetime=None, filter_keywords=["AI", "python"])
```

### `web` — fetch a URL (MCP shortcut)

Polls a URL via the MCP `fetch` server. Useful for monitoring a
single web page that changes over time.

**Arguments:**
- `url` *(str, required)*.
- `poll_interval` *(int seconds, default `300`)*.
- `max_items` *(int, default `None`)*.

**Setup:** `pip install mcp mcp-server-fetch` (one-time).

**Example `office.md`:**
```
sources:
    web(url="https://example.com/news", poll_interval=600)
```

### `search` — Brave web search (MCP shortcut)

Runs a Brave Web Search query on a schedule. Results come back as
a list — each result is yielded as a separate message.

**Arguments:**
- `query` *(str, required)*.
- `poll_interval` *(int seconds, default `300`)*.
- `max_items` *(int, default `None`)*.

**Setup:** Install the MCP Brave Search server and set its API
key as documented in that server's instructions.

**Example `office.md`:**
```
sources:
    search(query="AI policy", poll_interval=900)
```

### `gmail` — your Gmail inbox (credentialed)

Polls Gmail using a Gmail **app password** (not OAuth) — a
16-character string you generate once in your Google account
settings. No Google Cloud project, nothing else to configure.

**Arguments:**
- `poll_interval` *(int seconds, default `60`)*.
- `max_emails` *(int, default `10`)* — per poll.
- `unread_only` *(bool, default `True`)*.
- `folder` *(str, default `"INBOX"`)*.

**Setup (one-time):**
1. `myaccount.google.com` → Security → enable 2-Step Verification.
2. `myaccount.google.com` → Security → App passwords → generate one
   for "Mail".
3. In your shell:
   ```bash
   export GMAIL_USER='you@gmail.com'
   export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'
   ```

**Example `office.md`:**
```
sources:
    gmail(poll_interval=60, unread_only=True)
```

**Each message yielded:**
```python
{
    "source":    "gmail",
    "title":     "Re: PS3 office hours",   # email subject
    "text":      "Hi Mani, I'll be...",    # body
    "url":       "https://mail.google.com/mail/u/0/#search/rfc822msgid:...",
    "timestamp": "Wed, 29 Apr 2026 14:21:32 -0700",
    # Gmail-specific extras:
    "subject":   "Re: PS3 office hours",
    "sender":    "Sara Lin <sara@example.edu>",
    "uid":       "1234",
}
```

`title` and `url` match the standard DisSysLab message shape, so
role files written for RSS feeds work unchanged on Gmail. The
`subject`, `sender`, `uid` fields are Gmail-specific extras you
can reference in roles or sinks that care about them.

**Recipe.** [How to monitor your inbox](recipes/monitor-your-inbox.md).

### `calendar` — any public ICS calendar (credentialed)

Polls a public ICS/iCal URL (Google Calendar, Apple Calendar,
Outlook — anything that exports `.ics`).

**Arguments:**
- `url` *(str, optional)* — if omitted, reads `CALENDAR_ICS_URL`
  from the environment.
- `poll_interval` *(int seconds, default `300`)*.
- `days_ahead` *(int, default `7`)* — how far ahead to look.

**Setup:** In Google Calendar → Settings → "Integrate calendar" →
copy the public URL ending in `.ics`. Either pass it directly via
`url=` or:

```bash
export CALENDAR_ICS_URL='https://calendar.google.com/calendar/ical/.../basic.ics'
```

**Example `office.md`:**
```
sources:
    calendar(poll_interval=600, days_ahead=7)
```

### `webhook` — listen for inbound HTTP POSTs (push-style)

A push-style source. Spins up a stdlib HTTP listener; each
incoming POST becomes one DisSysLab message. Useful for receiving
notifications from third-party services (GitHub, Stripe, Zapier),
forwarding the output of one office into another over HTTP, or
poking your office from `curl` while you develop.

**Arguments:**
- `port` *(int, default `8000`)* — TCP port to listen on.
- `path` *(str, default `"/webhook"`)* — URL path that triggers a
  message. Other paths return 404.
- `host` *(str, default `"127.0.0.1"`)* — interface to bind.
  Default is localhost-only. Pass `host="0.0.0.0"` to accept
  posts from other machines (read the security note below).

**Setup:** none. The source uses Python's stdlib `http.server`.

**Reachability for real third-party webhooks.** A localhost
listener is not visible from the public internet. To receive
webhooks from GitHub, Stripe, etc., use a tunnel:

```bash
# in one terminal
ngrok http 8000
# copy the https URL it prints, paste into the upstream service
```

`cloudflared`, `localtunnel`, and Tailscale Funnel work the same
way.

**Security:** anyone who can reach the listening port can inject
messages — there is no authentication. Keep the default
`host="127.0.0.1"` unless you've put the listener behind a
reverse proxy that handles TLS and auth, or restricted the
firewall to specific source IPs.

**Example `office.md`:**
```
sources:
    hook: webhook                                  # localhost:8000/webhook
    incoming: webhook(port=9000, path="/incoming")
```

**Each message yielded:**
```python
{
    "source":    "webhook",
    "title":     "...",                  # from JSON body's "title" or "subject"
    "text":      "...",                  # from JSON body's "text", else raw body
    "url":       "...",                  # from JSON body's "url", else ""
    "timestamp": "2026-04-30T...",       # arrival time, ISO 8601 UTC
    # plus any other keys from the JSON body, passed through
}
```

If the body is JSON, every key in it is forwarded; the standard
five keys are filled from the body when present, otherwise from
sensible defaults. Non-JSON bodies become the `text`.

### `mcp_source` — any MCP server tool (advanced)

The general-purpose MCP source. `web` and `search` above are
shortcuts on top of this; reach for `mcp_source` directly when you
need a server that doesn't have a shortcut.

**Arguments:**
- `server` *(str, required)* — server name (`"fetch"`,
  `"brave_search"`, `"github"`, `"filesystem"`, `"sqlite"`) or a
  full `https://...` URL for a remote HTTP server.
- `tool` *(str, required)* — tool name to call on the server.
- `args` *(dict, default `{}`)* — arguments to pass to the tool.
- `poll_interval` *(int seconds, default `300`)*.
- `max_items` *(int, default `None`)*.
- `auth_env_var` *(str, default `None`)* — env var holding an
  auth token (HTTP servers only).

**Setup:** `pip install mcp` plus whichever specific server
you're using.

**Example `office.md`:**
```
sources:
    mcp_source(server="github", tool="search_repositories", args={"query": "language:python stars:>1000"}, poll_interval=3600)
```

### arXiv category feeds (5 named, no key)

New-submission listings for five CS categories, scraped and
normalised into the same message shape as the RSS feeds. Used by
`arxiv_radar`.

| Name in `office.md` | Category                          |
|---------------------|-----------------------------------|
| `arxiv_cs_ai`       | Artificial Intelligence (cs.AI)   |
| `arxiv_cs_lg`       | Machine Learning (cs.LG)          |
| `arxiv_cs_cl`       | Computation and Language (cs.CL)  |
| `arxiv_cs_cv`       | Computer Vision (cs.CV)           |
| `arxiv_cs_ro`       | Robotics (cs.RO)                  |

**Arguments (all optional):** `max_articles`, `poll_interval` — as
for the RSS feeds.

### `weatherapi` — multi-day forecast (needs a free key)

Use `weather` for *current* conditions with no key. Use
`weatherapi` when the office needs a 1–14 day forecast; it returns
one message per run holding the whole forecast. Needs a free
WeatherAPI.com key in `WEATHERAPI_KEY`.

```
sources:
    weatherapi(q="Pasadena", days=3)
```

### `kalshi` — prediction-market prices (no key for public data)

Polls the Kalshi Trade API. Two modes: name tickers explicitly, or
give a keyword and let it discover matching open events and
markets. Used by `kalshi_market_watch`.

```
sources:
    bitcoin: kalshi(tickers=["KXBTC-25DEC31-B100000"])
    hurricanes: kalshi(keyword="hurricane", poll_interval=300)
```

Kalshi's default market listing is dominated by sports, so keyword
discovery searches events as well as markets.

### `file_source` — read a local JSONL, JSON or CSV file

One message per line (`.jsonl`), per top-level item (a `.json` list),
or per row (`.csv`, with the header row naming the fields). The plain
way to get your own data into an office, and the stand-in for any
real source while you build one: replacing it later changes one
declaration line and none of the connections.

```
sources:
    readings: file_source(path="readings.jsonl")
```

### `starter` and `session_starter` — retired

Version 1 offices used `starter` (and `session_starter`,
`session_starter_2`, `session_starter_3`) to send one message that woke
an agent standing in for a source. In this version a source is a source:
use `file_source` with a small data file, or write a local source in
`sources/` (`dsl grammar sources`). `debate`'s problems, for example,
come from `problems.jsonl`.

### Audio and images (sensor sources)

Four sources feed offices that classify signals rather than text.
All four are used by the sensor gallery apps; see the
`sensor-office-builder` skill for how to wrap a model as a role.

| Name              | What it emits                                   |
|-------------------|-------------------------------------------------|
| `audio_mic`       | Chunks of live microphone audio, one per chunk  |
| `audio_clip`      | The same chunks, replayed from one audio file   |
| `audio_folder`    | One message per audio file in a folder          |
| `image_folder`    | One message per image in a folder               |

`audio_mic` and `audio_clip` emit the *same* message shape on
purpose: develop a streaming office against a recorded clip, then
swap in the microphone without touching anything downstream.
`audio_mic` needs portaudio installed; `audio_clip` does not.

`audio_folder` sends the file *path*, not the audio bytes — each
downstream agent opens what it needs, so the queue stays light.
`image_folder` does load pixels, since the analysers all want them.

```
sources:
    clips: audio_folder(path="recordings/", glob="*.mp3")
    photos: image_folder(folder="camera_trap/")
    mic: audio_mic(chunk_ms=1000)
```

---

## Sinks

A sink receives messages at the end of an office: it shows them,
saves them, or sends them on. Sinks are declared under `sinks:` in
`office.md`. These ship with DisSysLab.

### `discard` — drop messages silently

No output, no logging. Use as a routing target when an agent
decides a message is not worth keeping.

**Arguments:** none.

**Example `office.md`:**
```
sinks:
    console_printer
    discard
agents:
    Felix: topic_filter
    Rex: router(on="on_topic")
connections:
    Felix -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
```

### `console_printer` — print to the terminal

Prints each message to stdout. Useful for the simplest possible
office.

**Arguments:**
- `verbose` *(bool, default `False`)* — `True` prints every field
  on its own line; `False` prints a one-line compact form.

**Example `office.md`:**
```
sinks:
    console_printer
connections:
    Sita -> console_printer
```

### `intelligence_display` — color-coded briefing display

Renders each message as a color-coded bordered block. With
`max_items` set, refreshes the display in place showing the most
recent N — like a live dashboard.

**Arguments** -- it never guesses field names; you say which to show:
- `title` -- the field shown as the block's heading.
- `text` -- the field shown as its body.
- `color` -- a field whose value is `CRITICAL`, `HIGH`, `MEDIUM` or
  `LOW` (red, red, green, white).
- `lines` -- a list of fields printed one per line as `field: value`.
- `max_items` *(int, default `None`)* — `None` scrolls
  continuously; an integer (e.g. `8`) keeps the last N visible
  and clears the screen on each update.

**Example `office.md`:**
```
sinks:
    intelligence_display(title="headline", text="summary", color="severity", max_items=8)
connections:
    Riley -> intelligence_display
```

### `jsonl_recorder` — append messages to a JSONL file

Writes each message as one JSON object per line. Useful as an
archive you can grep, tail, or feed back into another office
later.

**Arguments:**
- `path` *(str, default `"anomaly_stream.jsonl"`)* — output file.
  A bare filename like `"briefings.jsonl"` is **relative to the
  office folder**, not to wherever you were standing when you typed
  the command. `dsl run` works from inside the office's folder, so an
  office's output lands next to its `office.md` no matter where you
  ran it from.
  That is usually what you want: the office and its results stay
  together.

  `"./briefings.jsonl"` means the same thing as `"briefings.jsonl"`.
  An **absolute path** (`"/Users/you/briefings.jsonl"`) is the one
  form that escapes the office folder — use it when you deliberately
  want output somewhere else.

  This is why a gallery office is copied with `dsl init <office>
  <folder>` before it is run: its own folder is inside the installed
  package.
- `mode` *(str, default `"w"`)* — `"w"` overwrites at start,
  `"a"` appends.
- `flush_every` *(int, default `1`)* — flush after every N
  records.

**Example `office.md`:**
```
sinks:
    jsonl_recorder(path="briefings.jsonl")
```

After the office runs, the file is in the office's folder.

### Two or more of the same sink

Give each its own name; the kind is the same:

```
sinks:
    kept: jsonl_recorder(path="kept.jsonl")
    rejected: jsonl_recorder(path="rejected.jsonl")
connections:
    Rex.yes -> kept
    Rex.no -> rejected
```

(The `jsonl_recorder_briefing`, `slack_sink_alerts`, `gmail_sink_match`
and similar aliases are from version 1, where a sink could not be
named. They still work, but a name says more.)

### `markdown_digest` — one markdown file, one section per message

Appends each message to a markdown file as it arrives, line-buffered,
so you can `tail -f` the file while the office is still running. Used
by `competitor_watch`.

**Arguments:**
- `path` *(str, default `"morning_digest.md"`)* — output file, resolved
  against the office folder like every other sink path.
- `title` *(str, default `None`)* — the document heading. **When left
  unset it becomes `"Morning digest — <today's date>"`**, which is right
  for a morning brief and wrong for anything else. Set it whenever the
  office is not a morning brief.
- `mode` *(str, default `"w"`)* — `"w"` overwrites at start, `"a"`
  appends across runs.

**Example `office.md`:**
```
sinks:
    markdown_digest(path="competitors.md", title="Competitor watch")
```

### `gmail_sink` — send emails via Gmail (credentialed)

Sends each incoming message as an email via SMTP, using the same
Gmail app password as the `gmail` source.

**Arguments:**
- `to` *(str, required)* — recipient email.
- `subject` *(str, default `"DisSysLab Alert"`)* — overridden by
  a message's `subject` field if present.

The message's `text` field becomes the email body.

**Setup:** same as `gmail` source — set `GMAIL_USER` and
`GMAIL_APP_PASSWORD`.

**Example `office.md`:**
```
sinks:
    gmail_sink(to="you@example.com", subject="Briefing")
```

### `slack_sink` — post to a Slack channel (credentialed)

Posts each incoming message to a Slack channel via an
[Incoming Webhook](https://api.slack.com/messaging/webhooks). No
OAuth, no bot install, no scopes — just one URL bound to one
channel.

**Arguments (all optional):**
- `webhook_url_env` *(str, default `"SLACK_WEBHOOK_URL"`)* —
  environment variable holding the webhook URL. Override this
  when you have multiple webhooks for different channels.
- `username` *(str, default `None`)* — display name for the post,
  overrides the webhook's default.
- `icon_emoji` *(str, default `None`)* — emoji shortcode (e.g.
  `":robot_face:"`) used as the post avatar.
- `timeout` *(float, default `5.0`)* — HTTP timeout in seconds.

The message's `text` field becomes the post body. If `subject`
is present it appears as a bold first line. If `url` is present
it appears on its own line so Slack can unfurl it.

**Setup (one-time):**
1. Go to `api.slack.com/apps` → Create New App → From scratch.
2. Pick a name and a workspace; click Create App.
3. In the sidebar, click **Incoming Webhooks** and toggle it on.
4. Click **Add New Webhook to Workspace**, pick the channel,
   click Allow.
5. Copy the webhook URL and export it:
   ```bash
   export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'
   ```

**Example `office.md`:**
```
sinks:
    slack_sink
```

**Posting to multiple channels.** A webhook URL is bound to one
channel. To post to a second channel, create a second webhook and
a second `slack_sink` instance with a different env var:

```
sinks:
    team: slack_sink
    alerts: slack_sink(webhook_url_env="SLACK_WEBHOOK_URL_ALERTS")
```

then `export SLACK_WEBHOOK_URL_ALERTS='...'` for the second URL.

### `webhook_sink` — POST each message to an arbitrary HTTP endpoint

The general-purpose outbound webhook. POSTs the message dict as
JSON to a configured URL. Use it to forward to Discord, Zapier,
Make, your own server, an inbound `webhook` source in another
DisSysLab office, or any HTTP service that accepts JSON.

For Slack specifically, prefer `slack_sink` — it formats the
message nicely. `webhook_sink` is the unopinionated fallback.

**Arguments:**
- `url` *(str, optional)* — explicit target URL. Highest priority.
- `webhook_url_env` *(str, default `None`)* — env var holding the
  URL. Use this when you don't want the URL in `office.md`.
- If neither is set, the sink reads `WEBHOOK_URL` from the
  environment.
- `headers` *(dict, default `{"Content-Type": "application/json"}`)*.
- `timeout` *(float seconds, default `10`)*.
- `retry_count` *(int, default `3`)* — retries with linear backoff.
- `retry_delay` *(float seconds, default `1`)* — base delay; grows
  with each attempt.

**Example `office.md`:**
```
sinks:
    out: webhook_sink                                       # reads WEBHOOK_URL
    local: webhook_sink(url="http://localhost:8000/webhook")
    zapier: webhook_sink(webhook_url_env="ZAPIER_HOOK_URL")
```

The full message dict is sent as the JSON body. Non-dict messages
are wrapped as `{"data": str(msg)}`.

### `mcp_sink` — send messages to any MCP server tool (advanced)

For each incoming message, merges the message fields with static
args (message fields win) and calls the MCP tool.

**Arguments:**
- `server` *(str, required)* — local server name or HTTPS URL.
- `tool` *(str, required)* — tool name to call.
- `args` *(dict, default `{}`)* — static args merged with each
  message.
- `auth_env_var` *(str, default `None`)*.

**Setup:** `pip install mcp` plus whichever specific server.

**Example `office.md`:**
```
sinks:
    mcp_sink(server="filesystem", tool="write_file", args={"path": "output.txt"})
```

---

## Adding more

The list above is everything that ships today. A few capabilities
are planned:

- **Slack Web API sink** — post to any channel with a bot token
  (today's `slack_sink` is webhook-based and bound to one channel)

Beyond that, you can also use `mcp_sink` and `mcp_source` to
reach any service with an MCP server, or write your own.

**The biggest lever you already have: MCP.** `mcp_source`/`mcp_sink`
can already reach any server in the official [MCP
Registry](https://modelcontextprotocol.info/tools/registry/) — 500+
community servers as of 2026 (Google Drive, Notion, Postgres, and
hundreds more), plus the small set of official reference servers
(fetch, filesystem, git, memory, time, sequential-thinking). If a
prospective office needs a connector, check there before assuming it
needs new DisSysLab code — it very often doesn't.

**Candidates for new first-class registered sources/sinks** — not
built, but easy, because each mirrors an existing entry above almost
exactly (surveyed 2026-07-22, for prospective testers who ask for one
of these by name):

*Sources, same shape as `weather`/`stocks` (free, no signup, no key,
one public JSON/GeoJSON endpoint):*
- USGS real-time earthquake feed
- NOAA / National Weather Service severe-weather alerts (US)
- arXiv's own API — would turn the `arxiv_radar` gallery app's ad-hoc
  fetch into a first-class registered source
- CoinGecko or CoinCap crypto prices — parallels `stocks` exactly
- Wikipedia's recent-changes feed
- GitHub's public events API
- *(An additional RSS feed is **not** on this list: you already have
  `rss(url=...)`. Nothing needs building. See the `rss` section above.)*

*Sinks, same shape as `slack_sink`:*
- **Discord webhook sink** — Discord's incoming webhooks work
  identically to Slack's (one URL, POST JSON)
- **Telegram bot sink** — one HTTP POST with a bot token, no OAuth
- **CSV or SQLite sink** — parallels `jsonl_recorder`, no new
  dependency

None of these are built. They're recorded here because they come up
naturally when someone describes a real office (e.g. "post alerts to
our Discord," "track a crypto price," "email me when there's a big
earthquake near the site") and the honest answer today is "not
supported yet" even though the actual implementation effort is small —
each is a Python class with a `run()` method and a registry entry, the
same pattern as every entry above.

To add your own source or sink (this list's items included), write a
Python class with a `run()` method (generator for sources, regular
function for sinks) and register it in
`dissyslab/office/utils.py:SOURCE_REGISTRY` or `SINK_REGISTRY`.
The existing entries are the simplest reference.
