# How to send messages to the outside world

**Goal.** Send the messages your agents produce to a file, a
terminal, an email inbox, a chat channel, or any other place
outside the office.

An office is a closed system of agents passing messages to each
other. The only way an office can affect anything outside itself
is through a **sink**. A sink can write to a file, send an email,
post to Slack, drive a physical actuator, or do anything else
that has an effect on the outside world. Every sink shipped with
the framework is listed in
[`docs/SOURCES_AND_SINKS.md`](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md);
this recipe shows the four most common destinations.

## Run a working example

`org_news_filter` already uses two sinks — `console_printer` for
articles to keep, `jsonl_recorder` for the rest:

```bash
dsl init org_news_filter my_filter
cd my_filter
dsl run .
```

Articles about the Americas stream to your terminal. Everything
else lands in `filtered_output.jsonl`. Both behaviors come from
the `Sinks:` line in `office.md`:

```
Sinks: console_printer, jsonl_recorder(path="filtered_output.jsonl")
```

## Send to a file

`jsonl_recorder` writes each incoming message as one JSON Lines
record — one line per message, easy to grep, easy to read back.

```
Sinks: jsonl_recorder(path="output.jsonl")

Connections:
Alex's briefing is jsonl_recorder.
```

Each line of `output.jsonl` is a complete JSON object with all
the fields the agent produced (`source`, `title`, `text`, `url`,
plus anything the agent added).

**Multiple files in one office.** If you want two distinct files,
use the numbered aliases:

```
Sinks: jsonl_recorder_briefing(path="briefings.jsonl"),
       jsonl_recorder_discard(path="discards.jsonl")

Connections:
Alex's keep is jsonl_recorder_briefing.
Alex's discard is jsonl_recorder_discard.
```

The aliases (`jsonl_recorder_briefing`, `jsonl_recorder_discard`,
`jsonl_recorder_archive`, `jsonl_recorder_raw`) all use the same
underlying class — the alias just lets the org chart name
distinct file destinations.

## Print to the terminal

`console_printer` is the simplest sink. No setup, no path, no
arguments:

```
Sinks: console_printer

Connections:
Alex's briefing is console_printer.
```

Useful while you're developing — you watch each message as it's
produced. Replace it with a file sink once the office is doing
what you want.

## Send email via Gmail

`gmail_sink` sends each incoming message as an email. The
message's `text` field becomes the email body. Requires a one-time
Gmail app password setup (a few minutes).

**One-time setup:**

1. Go to `myaccount.google.com` → Security → enable 2-Step
   Verification.
2. Same page → App passwords → generate a password for "Mail".
3. Set two environment variables in the shell where you'll run
   `dsl run`:

```bash
export GMAIL_USER='you@gmail.com'
export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'
```

**In `office.md`:**

```
Sinks: gmail_sink(to="alerts@example.com", subject="DisSysLab Briefing")

Connections:
Alex's briefing is gmail_sink.
```

Every message Alex routes to `briefing` becomes an email. If a
message has its own `subject` field, that overrides the default.

**Be polite.** A high-volume RSS feed plus an unfiltered office
will mail you hundreds of messages an hour. Filter first, mail
second — pair `gmail_sink` with a filter agent (see [How to filter
for a topic](filter-for-a-topic.md)) or set a small
`max_articles` while you're testing.

## Send to Slack

`slack_sink` posts each incoming message to a Slack channel via
an [Incoming Webhook](https://api.slack.com/messaging/webhooks).
No OAuth, no bot install — just one URL bound to one channel.

**One-time setup:**

1. Go to `api.slack.com/apps` → Create New App → From scratch.
2. Pick a name and a workspace; click Create App.
3. In the sidebar, click **Incoming Webhooks** and toggle it on.
4. Click **Add New Webhook to Workspace**, pick the channel,
   click Allow.
5. Copy the webhook URL and export it in the shell where you'll
   run `dsl run`:

```bash
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'
```

**In `office.md`:**

```
Sinks: slack_sink

Connections:
Alex's briefing is slack_sink.
```

Every message Alex routes to `briefing` becomes a Slack post in
the channel the webhook points at. If the message has a `subject`
field, it appears as a bold first line. If it has a `url` field,
Slack will unfurl a preview.

**Posting to multiple channels.** A webhook URL is bound to one
channel at the time you create it. To post to a second channel,
create a second webhook and use one of the shipped aliases —
`slack_sink_alerts`, `slack_sink_briefing`, `slack_sink_archive` —
each is a distinct sink instance sharing the same class:

```
Sinks: slack_sink_briefing(webhook_url_env="SLACK_WEBHOOK_URL_BRIEFING"),
       slack_sink_alerts(webhook_url_env="SLACK_WEBHOOK_URL_ALERTS")

Connections:
Alex's briefing is slack_sink_briefing.
Alex's urgent is slack_sink_alerts.
```

Then export both env vars in your shell. Add more aliases in
`dissyslab/office/utils.py:SINK_REGISTRY` if you need them — they
follow the same pattern as `jsonl_recorder_*`.

## Send to a webhook

`webhook_sink` POSTs each message as JSON to any HTTP endpoint —
Discord, Zapier, Make, your own server, or a `webhook` source in
another DisSysLab office. It's the unopinionated outbound HTTP
sink; for Slack specifically, prefer `slack_sink` (it formats
`subject` and `url` for nice rendering).

**One-time setup.** Get the target URL from whatever service you
want to post to (Discord channel webhook, Zapier "Catch Hook"
URL, etc.) and export it in the shell where you'll run `dsl run`:

```bash
export WEBHOOK_URL='https://example.com/incoming'
```

**In `office.md`:**

```
Sinks: webhook_sink

Connections:
Alex's briefing is webhook_sink.
```

The full message dict goes out as the JSON body. The receiving
service sees every field your agent produced (`source`, `title`,
`text`, `url`, plus anything custom).

**Multiple destinations.** Pass `webhook_url_env=` to point at a
different env var, so each instance can target its own URL:

```
Sinks: webhook_sink(url="http://localhost:9000/incoming"),
       webhook_sink(webhook_url_env="ZAPIER_HOOK_URL")
```

**Office-to-office.** A `webhook_sink` in office A and a `webhook`
source in office B is the standard way to wire two offices across
a process or machine boundary. See [How to receive
webhooks](receive-webhooks.md).

**Don't post too often.** Most webhook receivers rate-limit. A
high-volume source plus an unfiltered office will trip those
limits and get your URL blocked. Filter first, post second — pair
`webhook_sink` with a filter agent (see [How to filter for a
topic](filter-for-a-topic.md)) or set a small `max_articles`
while testing.

## The pattern, in a sentence

A sink is an office's connection to the outside world: every
agent mailbox wired to a sink in `office.md`'s `Connections:`
becomes a path out of the office. The shipped sinks cover files
(`jsonl_recorder`), the terminal (`console_printer`,
`intelligence_display`), email (`gmail_sink`), and arbitrary MCP
tools (`mcp_sink`). Every sink is named the same way in the org
chart — only the arguments differ.

## Variations

**Multiple sinks for one mailbox.** A single mailbox can fan out
to several sinks:

```
Connections:
Alex's briefing is console_printer.
Alex's briefing is jsonl_recorder.
Alex's briefing is gmail_sink.
```

Each briefing now appears on the terminal, in the file, and in
your inbox. Useful for development (watch live + keep a log) and
for production (archive + alert).

**Different sinks for different mailboxes.** This is the more
common pattern. The role's job description routes each message to
one of several mailboxes; each mailbox is then wired to its own
sink:

```
Connections:
Alex's urgent is gmail_sink.
Alex's normal is jsonl_recorder_briefing.
Alex's discard is jsonl_recorder_discard.
```

The role file (`roles/alex.md`) spells out when Alex sends to
`urgent`, `normal`, or `discard`. The org chart wires each one to
a destination.

**Roll your own sink.** Write a Python class with a `run(msg)`
method, register it in `SINK_REGISTRY` in
`dissyslab/office/utils.py`. The existing entries (`Discard`,
`JSONLRecorder`, `GmailSink`) are the simplest references — each
is fewer than 100 lines.

## See also

- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — every shipped sink, with full argument lists and setup
  instructions.
- [`org_news_filter` in the gallery](https://github.com/kmchandy/DisSysLab/tree/main/dissyslab/gallery/org_news_filter)
  — the working example that pairs `console_printer` and
  `jsonl_recorder`.
- [How to filter for a topic](filter-for-a-topic.md) — pair a
  filter with `gmail_sink` so only the messages you care about
  hit your inbox.
- [How to write a custom role](write-a-custom-role.md) — design
  the mailboxes that route to each sink.
