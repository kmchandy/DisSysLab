# Send results outside: a file, email, Slack, a webhook

**Goal.** Send an office's results somewhere other than the screen. Every
destination is a **sink**: declare it under `sinks:`, connect to it. One
connection line can send the same message to several sinks.

The examples add sinks to the inbox sorter
([GETTING_STARTED.md](../GETTING_STARTED.md), part 6):
`dsl init inbox_sorter my_sorter`.

## To a file

```
sinks:
    urgent: jsonl_recorder(path="urgent.jsonl")
    digest: markdown_digest(path="urgent.md", title="Urgent messages")
connections:
    Rex.urgent -> urgent, digest
```

`jsonl_recorder` writes one JSON object per line: easy to read back into
Python, or into another office with `file_source`. `markdown_digest`
writes one readable section per message. Paths are relative to the
office's folder.

## By email

```
sinks:
    email: gmail_sink(to="staff@example.edu", subject="Urgent student message")
connections:
    Rex.urgent -> urgent, console_printer, email
```

**Try it before you set anything up.** Without Gmail credentials,
`gmail_sink` sends nothing and writes each email it would have sent to
`outbox.md` instead:

```
## Email #1 — 2026-10-16 17:34:52

**To:** staff@example.edu  
**Subject:** Lab 2 deadline

My laptop died last night and I lost my work. Can I get an extension for Lab 2? It is due tomorrow morning.
```

The body is the message's `text`; a message with its own `subject` field
uses it instead of the default subject. When the outbox looks right, add
`GMAIL_USER` and `GMAIL_APP_PASSWORD` to your `.env`
([monitor-your-inbox.md](monitor-your-inbox.md), step 1, says how to get
an app password), and it sends for real.

**Filter first, mail second.** An unfiltered news feed sends you an email
per article.

## To Slack

1. At api.slack.com/apps, create an app, turn on **Incoming Webhooks**,
   and add a webhook for the channel you want. Copy its URL.
2. Add it to `.env`: `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...`

```
sinks:
    team: slack_sink
connections:
    Rex.urgent -> team
```

A second channel needs a second webhook URL, under another name:
`alerts: slack_sink(webhook_url_env="SLACK_WEBHOOK_URL_ALERTS")`.

## To any web service

`webhook_sink` POSTs each message as JSON: to Discord, Zapier, your own
server, or another office's `webhook` source
([receive-webhooks.md](receive-webhooks.md)).

```
sinks:
    out: webhook_sink(url="http://localhost:8000/webhook")
connections:
    Rex.urgent -> out
```

To keep the URL out of `office.md`, use
`webhook_sink(webhook_url_env="MY_HOOK_URL")` and put `MY_HOOK_URL` in
`.env`.

## Check before you send

```bash
dsl check .
```

Email, Slack and webhooks act outside your computer. When text from an
outside source (a news feed, an inbox) can reach one of them, `dsl check`
says so in a note: whoever wrote that text is writing to your Slack
channel too. To send only a short alert, put an author role in front of
the sink that builds a message with just the fields you choose;
[monitor-your-inbox.md](monitor-your-inbox.md) shows one.

Arguments for every sink: `dsl grammar sources`, and
[SOURCES_AND_SINKS.md](../SOURCES_AND_SINKS.md) for the details of each.
