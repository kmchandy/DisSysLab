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

### RSS feeds (10 named, no key)

Ten named RSS feeds share one implementation. Each is a free,
public feed; no signups, no API keys.

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

### `stocks` — stock-ticker prices (no key)

Polls [Stooq](https://stooq.com/), a free CSV-over-HTTP financial
data service. Bare US tickers (e.g. `"AAPL"`) work directly; for
other markets, pass the full Stooq symbol (e.g. `"ntt.jp"`,
`"bp.uk"`).

**Arguments:**
- `ticker` *(str, default `"AAPL"`)*.
- `poll_interval` *(int seconds, default `300`)*.
- `max_readings` *(int, default `None`)*.

**Example `office.md`:**
```
Sources: stocks(ticker="AAPL", poll_interval=300)
```

### `stock_history` — bulk historical daily prices (no key)

The backtest-friendly counterpart to `stocks` above. `stocks` polls
Stooq's *live-quote* endpoint forever, one ticker at a time, for
"alert me when AAPL moves" style offices. `stock_history` hits
Stooq's *historical daily-bar* CSV endpoint once per ticker and
yields a single combined message covering every ticker requested,
then stops — for "backtest a strategy on the SP100" style offices.

One HTTP request per ticker (Stooq has no bulk "all these tickers in
one call" endpoint), made in sequence with a small pause between
requests. A ticker Stooq can't serve (typo, delisted, no history in
range) doesn't crash the fetch — its error is recorded under
`errors[ticker]` in the outgoing message and every other ticker's
data still comes through.

**Arguments:**
- `tickers` *(list of str, required)* — e.g. `["AAPL", "MSFT",
  "GOOGL"]`. Bare US tickers get `.us` appended automatically; for
  other markets pass the full Stooq symbol (e.g. `"ntt.jp"`).
- `start` *(str, default `"2026-01-01"`)* — first date to include,
  as `"YYYY-MM-DD"` or `"YYYYMMDD"`. Deliberately a small, recent
  default rather than "as far back as Stooq has," so a first run
  fetches quickly. Pass `start=None` explicitly for Stooq's full
  available history, or any other date for your own window.
- `end` *(str, default `None`)* — last date to include, same
  formats. Omit for through Stooq's most recent close.
- `request_pause` *(float seconds, default `0.25`)* — pause between
  each ticker's request; a polite pace, not a documented Stooq rate
  limit.

**Message shape** (one message, not one per ticker):
```
{
    "type":    "stock_history",
    "tickers": ["AAPL", "MSFT", ...],
    "start":   "20150101",
    "end":     "20250101",
    "history": {
        "AAPL": [{"date": "2015-01-02", "open": ..., "high": ...,
                  "low": ..., "close": ..., "volume": ...}, ...],
        "MSFT": [...],
    },
    "errors": {"BAD.T": "Stooq returned no data for 'bad.t.us'."},
    "timestamp": "2026-07-28T21:34:56+00:00",
}
```

**Example `office.md`:**
```
Sources: stock_history(tickers=["AAPL", "MSFT", "GOOGL"],
                        start="2015-01-01", end="2025-01-01")
```

**Known limitation:** as of 2026-07-28 this endpoint 404s — confirmed
by hand, including opening Stooq's own linked download URL directly
in a browser. Something changed or was discontinued on Stooq's side;
the real fix needs more investigation than this doc currently has.
Until then, use `synthetic_stock_history` below to build and test a
backtest office's plumbing.

### `synthetic_stock_history` — fake daily prices, no network (prototyping only)

Generates a per-ticker geometric random walk (independent, normally
distributed daily log-returns) and yields it in the exact same
message shape as `stock_history` above, with one added key:
`"synthetic": true`. No network call at all — exists specifically to
unblock building and testing a backtest office's downstream agents
(backtester, portfolio-builder, robustness-selector, ...) while
`stock_history`'s real endpoint is broken (see above). Swap in
`stock_history` later with no downstream changes once real data is
reachable again.

**This is not real market data** — no real correlation structure, no
real regime changes, no connection to any actual company. Don't use
it to draw conclusions about an actual trading strategy.

**Arguments:**
- `tickers` *(list of str, required)*.
- `start` *(str, default `"2015-01-01"`)* — a decade-long default
  window, unlike `stock_history`'s short recent default, since this
  exists specifically to unblock multi-year backtests.
- `end` *(str, default: today)*.
- `initial_price` *(float or `{ticker: float}`, default `100.0`)*.
- `annual_drift` *(float, default `0.08`)* — generic long-run
  assumption, not a forecast.
- `annual_volatility` *(float, default `0.25`)*.
- `seed` *(int, default `None`)* — same seed + tickers + dates ->
  identical output every run; omit for a fresh random run each time.

**Example `office.md`:**
```
Sources: synthetic_stock_history(tickers=["AAPL", "MSFT", "GOOGL"],
                                  start="2015-01-01", seed=42)
```

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
  current working directory the office is run from.
- `filename_pattern` *(str, default `"{ticker}_1year.csv"`)* — must
  contain `{ticker}`.
- `start` / `end` *(str, default: no bound)* — optionally filter rows
  to a date range after loading.

**Example `office.md`:**
```
Sources: csv_stock_history(tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"],
                            directory="sp100_data")
```

### `salton_wind` — NASA/JPL Salton Sea buoy wind (real, no key)

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

### `synthetic_salton_h2s` — synthetic Salton Sea H2S readings (no network, not real data)

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
  directory you ran `dsl run` from**, not the office folder. If
  you ran `dsl run path/to/briefing` from your home directory, the
  file lands in your home directory. Pass an absolute path
  (`"/Users/you/briefings.jsonl"`) or a path under the office
  folder (`"./briefings.jsonl"`) if you want it somewhere
  predictable.
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
- Any additional RSS feed at all — the 10 named feeds already share
  one generic implementation; adding a new one is close to a one-line
  change

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
