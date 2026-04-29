# Sources and Sinks Reference

Offices in DisSysLab have **sources** that generate messages
come in and **sinks** where messages are stored. This
page lists every source and sink shipped with the framework, what
each one accepts, and how to connect it in `office.md`.
You can also build your own sources and sinks.

For new users, start with the [Getting Started
guide](../GETTING_STARTED.md) and the gallery (`dsl list`); come back
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

Polls Gmail via IMAP using a Gmail **app password** (not OAuth).

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
- `mode` *(str, default `"w"`)* — `"w"` overwrites at start,
  `"a"` appends.
- `flush_every` *(int, default `1`)* — flush after every N
  records.

**Example `office.md`:**
```
Sinks: jsonl_recorder(path="briefings.jsonl")
```

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

- **Slack sink** — post briefings to a channel
- **First-class Gmail polish** — drop the IMAP layer
- **HTTP webhook source/sink** — generic HTTP integration

Until those land, you can reach the same outcomes today through
`mcp_sink` (Slack and HTTP are both supported via MCP servers) or
through `gmail_sink` and `gmail` (which already work as
documented above).

To add your own source or sink, write a Python class with a
`run()` method (generator for sources, regular function for
sinks) and register it in
`dissyslab/office/utils.py:SOURCE_REGISTRY` or `SINK_REGISTRY`.
The existing entries are the simplest reference.
