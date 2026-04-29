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

## Send to Slack (today: via MCP; soon: first-class)

A first-class `slack_sink` is on the roadmap. Until it lands, the
working path is `mcp_sink` plus a Slack MCP server.

```
Sinks: mcp_sink(server="slack",
                tool="post_message",
                args={"channel": "#briefings"})

Connections:
Alex's briefing is mcp_sink.
```

This requires running the Slack MCP server alongside DisSysLab.
The setup is more involved than file or Gmail; for most
classroom use, file or email is the easier first stop.

When the first-class `slack_sink` ships, this recipe will be
updated and the `mcp_sink` route will become a fallback for
Slack users who need the full API surface.

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
