# Sources and Sinks Reference

Offices in DisSysLab have **sources** that generate messages
come in and **sinks** where messages are stored. This
page lists every source and sink shipped with the framework, what
each one accepts, and how to connect it in `office.md`.
You can also build your own sources and sinks.

For new users, start with the [Getting Started
guide](GETTING_STARTED.md) and the gallery (`dsl list`); come back
here once you want to swap in a different source or send results
somewhere new.

**Conventions used below.**
- Each entry shows a one-line usage example **as it appears in
  `office.md`**.
- Optional arguments show their defaults.
- "Setup" notes describe credentials or installations needed for
  the source/sink to run.

---

## Sources

A source is an agent that generates messages. You declare the sources in 
an office in the `Sources:` line.

### `rss` — any RSS or Atom feed at all (no key)

**Start here.** If a site publishes a feed, you can read it, and you
do not need us to add it. Pass the URL:

```
Sources: rss(url="https://example.com/feed.xml", name="my_feed",
             max_articles=5)
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
Sources: hacker_news(max_articles=20),
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
Sources: console_input(default_message="Summarize the weather for Pasadena.")
Sinks: console_printer
...
Connections:
  console_input's destination is Alex.
  Alex's briefing is console_printer.
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
Sources: weather(city="London", poll_interval=600)
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
Sources: stocks(ticker="AAPL", poll_interval=300, max_readings=1)
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

To backtest, download your own data once and read it from disk:

```bash
pip install "dissyslab[market]"
python3 dissyslab/gallery/apps/mac_speed_suite/download_stock_history_from_yf.py
```

That script reads the ticker list, the data directory and the filename
pattern straight out of `office.md`, so the download always matches what
the office expects. Prices are split- and dividend-adjusted and written
as plain `Date,Open,High,Low,Close,Volume` CSV.

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
- `directory` *(str, required)* — relative paths resolve against the
  **office folder**, not the directory you typed the command in.
  `build/run.py` chdirs there first; see `jsonl_recorder`'s `path`
  argument below for the full explanation. This is why
  `paper_trader` and `mac_speed_suite` reach the shared data with
  `directory='../../../../sp100_data'` — that path is counted from
  the office's own folder.
- `filename_pattern` *(str, default `"{ticker}_1year.csv"`)* — must
  contain `{ticker}`.
- `start` / `end` *(str, default: no bound)* — optionally filter rows
  to a date range after loading.

**Example `office.md`:**
```
Sources: csv_stock_history(tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"],
                            directory="sp100_data")
```

### `salton_wind` — NASA/JPL Salton Sea buoy wind (real, no key, not yet registered)

> **Not yet registered.** The implementation exists
> (`components/sources/jpl_saltonsea_buoy_source.py`) but has no entry
> in `SOURCE_REGISTRY`, so `Sources: salton_wind` in an `office.md`
> does not compile yet. Until it does, wrap it directly:
> `Source(fn=JPLSaltonSeaBuoySource().run, name="salton_wind")`.
> This is why `salton_sea_dashboard` is an xfail in the compiler tests.

One-shot fetch of the two NASA/JPL buoys (SS1, SS1A) moored on the
Salton Sea, CA, from `https://saltonsea.jpl.nasa.gov/get_met_weather`
— wind speed, wind direction, air temp, humidity, and pressure, each
as `{"min":..., "avg":..., "max":...}` over the previous 30 minutes.
Built for the `salton_sea_dashboard` gallery app. JPL's own caveat
("raw data, not quality-checked... informational purposes only") is
passed through on every message as `quality_note`.

Output is nested under a single `"wind"` key (not flattened) so it
merges into `synchronizer` alongside `synthetic_salton_h2s` (nested
under `"h2s"`) without any key collision — see
`jpl_saltonsea_buoy_source.py`'s docstring.

**Arguments:**
- `url` *(str, default JPL's live page)*.
- `timeout` *(float seconds, default `15.0`)*.

```
Sources: salton_wind
```

### `synthetic_salton_h2s` — synthetic Salton Sea H2S readings (no network, not real data, not yet registered)

> **Not yet registered.** As with `salton_wind` above: the
> implementation exists, the registry entry does not.

Prototyping stand-in for four named CARB hydrogen-sulfide monitoring
sites near the Salton Sea (Salton Sea Park, Torres-Martinez,
Mecca-Saul Martinez, Niland English), while the mapping from those
sites' public "ARB codes" to CARB AQMIS2's own internal `site=` query
parameter is unresolved (queries return "No Data Available" even for
old, settled dates — looks like an id-namespace mismatch, not an
actual data gap; CARB's download tool and the `H2S` parameter code
are otherwise confirmed working). Every message is stamped
`"synthetic": True`. Same `"h2s"`-nested message shape a real
CARB-backed source would use, so `salton_sea_dashboard` can swap this
out with zero downstream changes once the real site ids are found.

**Arguments:**
- `spike_probability` *(float, default `0.15`)* — chance any one
  site shows a synthetic odor-event spike this run.
- `seed` *(int, default `None`)* — set for reproducible output.

```
Sources: synthetic_salton_h2s
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
Sources: bluesky(max_posts=None, lifetime=None,
                 filter_keywords=["AI", "python"])
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
Sources: web(url="https://example.com/news", poll_interval=600)
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
Sources: search(query="AI policy", poll_interval=900)
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
Sources: gmail(poll_interval=60, unread_only=True)
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
Sources: calendar(poll_interval=600, days_ahead=7)
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
Sources: webhook                              # localhost:8000/webhook
Sources: webhook(port=9000, path="/incoming")
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
Sources: mcp_source(server="github",
                    tool="search_repositories",
                    args={"query": "language:python stars:>1000"},
                    poll_interval=3600)
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
Sources: weatherapi(city="Pasadena", days=3)
```

### `kalshi` — prediction-market prices (no key for public data)

Polls the Kalshi Trade API. Two modes: name tickers explicitly, or
give a keyword and let it discover matching open events and
markets. Used by `kalshi_market_watch`.

```
Sources: kalshi(tickers=["KXBTC-25DEC31-B100000"])
Sources: kalshi(keyword="hurricane", poll_interval=300)
```

Kalshi's default market listing is dominated by sports, so keyword
discovery searches events as well as markets.

### `file_source` — read a local CSV or JSON file

One message per row (CSV) or per top-level item (JSON). The plain
way to get your own data into an office.

```
Sources: file_source(path="data/readings.csv")
```

### `starter` and `session_starter` — one message, to start a loop

`starter` emits exactly one message at startup and then stops. An
office built as a cycle — a debate, a negotiation, anything that
runs until it converges — needs one bootstrap message to set the
first round going; after that the feedback edges keep it moving.
Used by `debate`, `trading_room`, `returns_desk`,
`shipment_release`.

```
Sources: starter
```

`session_starter` (and the numbered `session_starter_2`,
`session_starter_3`) do the same for offices that open a
multi-turn session rather than a single round.

Because a starter is *meant* to send one message and stop, it is
the usual reason to reach for `allow_empty` — not because it
produces nothing, but because offices built around it often want
the empty-source guard relaxed elsewhere. See the guard's own
message when it fires.

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
Sources: audio_folder(folder="recordings/")
Sources: image_folder(folder="camera_trap/")
Sources: audio_mic(chunk_seconds=1.0)
```

---

## Sinks

A sink is an agent that saves messages. You declare the sinks in 
an office in the `Sinks:` line. The following sinks are shipped
with the framework.

### `discard` — drop messages silently

No output, no logging. Use as a routing target when an agent
decides a message is not worth keeping.

**Arguments:** none.

**Example `office.md`:**
```
Sinks: discard
...
Connections:
  Alex's throw_away is discard.
```

### `console_printer` — print to the terminal

Prints each message to stdout. Useful for the simplest possible
office.

**Arguments:**
- `verbose` *(bool, default `False`)* — `True` prints every field
  on its own line; `False` prints a one-line compact form.

**Example `office.md`:**
```
Sinks: console_printer
...
Connections:
    Sita's display is console_printer
```

### `intelligence_display` — color-coded briefing display

Renders each message as a color-coded bordered block. With
`max_items` set, refreshes the display in place showing the most
recent N — like a live dashboard.

**Arguments:**
- `max_items` *(int, default `None`)* — `None` scrolls
  continuously; an integer (e.g. `8`) keeps the last N visible
  and clears the screen on each update.

The sink colors blocks by a `significance` field on the message
(`CRITICAL`, `HIGH`, `MEDIUM`, `LOW` → red, yellow, green,
white). Messages without that field render as `LOW`.

**Example `office.md`:**
```
Sinks: intelligence_display(max_items=8)
....
Connections:
  Zhou's cockpit is intelligence_display
```

### `jsonl_recorder` — append messages to a JSONL file

Writes each message as one JSON object per line. Useful as an
archive you can grep, tail, or feed back into another office
later.

**Arguments:**
- `path` *(str, default `"anomaly_stream.jsonl"`)* — output file.
  A bare filename like `"briefings.jsonl"` is **relative to the
  office folder**, not to wherever you were standing when you typed
  the command. The generated `build/run.py` does
  `os.chdir(<office folder>)` before starting, so an office's output
  lands next to its `office.md` no matter where you ran it from.
  That is usually what you want: the office and its results stay
  together.

  `"./briefings.jsonl"` means the same thing as `"briefings.jsonl"`.
  An **absolute path** (`"/Users/you/briefings.jsonl"`) is the one
  form that escapes the office folder — use it when you deliberately
  want output somewhere else.

  One consequence worth knowing: running a *shipped* gallery office
  in place writes into your `site-packages`, because that is where
  that office's folder is. `dsl init <office> <folder>` copies it
  somewhere of your own first, which is why the course tells you to
  start there.
- `mode` *(str, default `"w"`)* — `"w"` overwrites at start,
  `"a"` appends.
- `flush_every` *(int, default `1`)* — flush after every N
  records.

**Example `office.md`:**
```
Sinks: jsonl_recorder(path="briefings.jsonl")
```

After the office runs, find the file with `ls -la *.jsonl` from
the directory you launched `dsl run` from.

### `jsonl_recorder_*` — multiple JSONL files in one office

If your office needs more than one JSONL file (e.g. one for
discards, one for keepers), use these aliases. Each is a distinct
sink instance using the same `JSONLRecorder` class.

| Alias                       | Suggested use            |
|-----------------------------|--------------------------|
| `jsonl_recorder_discard`    | dropped messages         |
| `jsonl_recorder_briefing`   | finalized briefings      |
| `jsonl_recorder_archive`    | full archive             |
| `jsonl_recorder_raw`        | raw upstream input       |

Each takes the same arguments as `jsonl_recorder`. Add more
aliases in `dissyslab/office/utils.py:SINK_REGISTRY` if you need
them.

**Example `office.md`:**
```
Sinks: jsonl_recorder_discard(path="discards.jsonl"),
       jsonl_recorder_briefing(path="briefings.jsonl")
```

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
Sinks: markdown_digest(path="competitors.md",
                       title="Competitor watch")
```

### `report_html` — a single styled HTML report

**Arguments:** `path` *(str, default `"report.html"`)*, `title` *(str,
default `"Backtest Report"`)*. Built for `salton_sea_dashboard` and the
backtesting apps; usable anywhere you want one self-contained page.

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
Sinks: gmail_sink(to="you@example.com", subject="Briefing")
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
Sinks: slack_sink
```

**Posting to multiple channels.** A webhook URL is bound to one
channel. To post to a second channel, create a second webhook and
a second `slack_sink` instance with a different env var:

```
Sinks: slack_sink(webhook_url_env="SLACK_WEBHOOK_URL_ALERTS")
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
Sinks: webhook_sink                                   # reads WEBHOOK_URL
Sinks: webhook_sink(url="http://localhost:8000/webhook")
Sinks: webhook_sink(webhook_url_env="ZAPIER_HOOK_URL")
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
Sinks: mcp_sink(server="filesystem",
                tool="write_file",
                args={"path": "output.txt"})
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
