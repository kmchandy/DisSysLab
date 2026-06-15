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

To add your own source or sink, write a Python class with a
`run()` method (generator for sources, regular function for
sinks) and register it in
`dissyslab/office/utils.py:SOURCE_REGISTRY` or `SINK_REGISTRY`.
The existing entries are the simplest reference.
