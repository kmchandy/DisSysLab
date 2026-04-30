# How to receive webhooks

**Goal.** An office that listens for HTTP POSTs from another
service — a GitHub push, a Stripe charge, a form submission, a
Zapier or Make trigger, another DisSysLab office posting across
the network — and lets an agent decide what to do with each one.

## Run a working example

DisSysLab ships with a one-agent webhook listener:

```bash
dsl init webhook_listener my_listener
cd my_listener
dsl run .
```

The listener binds `localhost:8000/webhook` and waits. In a
second terminal, post a test payload:

```bash
curl -X POST http://localhost:8000/webhook \
  -H 'Content-Type: application/json' \
  -d '{"title":"test","text":"hello from curl"}'
```

The first terminal prints a one-sentence summary the analyst
wrote about that payload. Try a few more — an empty body, a
payload without a `text` field, a `{"event":"ping"}` health check
— and watch the analyst route them: real events go to the
terminal, health checks and malformed bodies land in
`webhook_log.jsonl`.

Press `Ctrl+C` to stop.

## How a payload becomes a message

The webhook source accepts any POST and turns the JSON body into
a standard DisSysLab message. If the upstream service already
sends fields named `title`, `text`, `url`, `source`, or
`timestamp`, those values come through. Anything else is preserved
on the message dict, so your analyst can read it.

A POST with body `{"title": "alert", "text": "disk full"}`
becomes:

```python
{
    "source":    "webhook",
    "title":     "alert",
    "text":      "disk full",
    "url":       "",
    "timestamp": "2026-04-30T15:21:08Z",
}
```

A POST with a richer body — a GitHub push hook, say — keeps every
extra field:

```python
{
    "source":     "webhook",
    "title":      "",
    "text":       "",
    "url":        "",
    "timestamp":  "2026-04-30T15:21:08Z",
    "ref":        "refs/heads/main",
    "repository": {"name": "DisSysLab", ...},
    "commits":    [...],
}
```

Your analyst can read whichever fields the upstream service sends.
A non-JSON body becomes the `text` field as a string.

## Change what the analyst does

Open `roles/analyst.md`. The role is short on purpose:

```
You are an analyst who receives webhook payloads from external
services. Each payload is a message with whatever fields the
upstream service sent.

Your job is to write a one-sentence summary of what each payload
is — the kind of event, who or what it concerns, and anything
notable. If a payload looks empty, malformed, or like a health
check (e.g., "ping", "test"), send it to discard. Otherwise send
your summary to keep.

Send to keep or to discard.
```

Rewrite it for the service you're listening to. A few examples:

```
You receive GitHub push hooks. Send a one-line summary —
"<author> pushed <N> commits to <branch>: <first commit
subject>" — to keep. Send tag pushes and branch deletes to
discard.
```

```
You receive Stripe charge events. Send only the `charge.failed`
events to keep, with a summary of the customer email and amount.
Send everything else to discard.
```

```
You receive form submissions. Send entries that look like real
inquiries to keep; send obvious spam (link-only bodies, gibberish
fields) to discard.
```

Save and re-run `dsl run .`. No rebuild — just edit and re-run.

## Make the listener reachable from the public internet

`localhost:8000` is only reachable from your own machine — fine
for testing with `curl`. To receive webhooks from a real upstream
service, you need a public URL.

The easiest way is `ngrok` — it gives you a public HTTPS URL that
forwards to your local listener:

```bash
ngrok http 8000
```

ngrok prints a URL like `https://abc123.ngrok.app`. Paste
`https://abc123.ngrok.app/webhook` into the upstream service's
webhook configuration, and posts will reach your listener.

The URL changes every time you restart ngrok unless you pay for a
reserved domain. Fine for a class demo; less fine for a
production handoff.

## Two things to watch out for

**Don't make personal stuff public.** A webhook URL is a
publicly-reachable HTTP endpoint with no authentication by
default — anyone who guesses or scrapes the URL can POST to it.
Two consequences:

- Don't have your office post or forward sensitive content
  (private messages, medical info, tokens, family details) based
  on a webhook payload alone. Treat every incoming payload as
  untrusted.
- Don't print the full payload to a Slack channel or
  shared file unless you've sanitized it. Run a filter agent
  first that drops or redacts sensitive fields before forwarding.

When you're done testing, stop the listener and stop ngrok. A
public URL pointing at your laptop is a small attack surface, but
it's not zero.

**Don't post too frequently.** When you wire `webhook_sink` to
forward to another service — Slack, Discord, your own server —
you're consuming somebody else's rate limit. A high-volume RSS
source plus an unfiltered office can fire hundreds of POSTs per
minute and get your webhook URL blocked.

- Filter first, post second. Use a filter agent (see
  [How to filter for a topic](filter-for-a-topic.md)) so only
  the messages you actually care about leave the office.
- While testing, pin a `max_articles` on the source or use a
  small input file. Don't point a real RSS feed at a live Slack
  webhook on the first run.
- Slack incoming webhooks specifically allow about 1 message
  per second per webhook; bursts above that get throttled.

## The pattern, in a sentence

The webhook source spins up an HTTP server that turns every POST
into a DisSysLab message; an analyst agent decides which mailbox
each one goes to (`keep` for the real events, `discard` for the
rest); and the org chart in `office.md` wires those mailboxes to
sinks — terminal, file, email, Slack, another webhook, anything
from
[the sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md).

## Variations

**Listen on a different port or path.** Pass them in the source
declaration:

```
Sources: webhook(port=9000, path="/incoming")
```

Useful if you're running two listener offices on the same
machine, or want a path that matches what an upstream service
expects.

**Forward to another service.** Replace `console_printer` with
`slack_sink` to post each summary to a Slack channel, `gmail_sink`
to email yourself, or `webhook_sink` to forward to yet another
HTTP service. See [How to send messages to the outside
world](send-messages-outside.md).

**Two offices wired across the network.** Office A's
`webhook_sink` POSTs to office B's `webhook` source. The two
offices can run on the same machine or on different ones (with
ngrok or a real public URL). Each side stays a closed system; the
HTTP boundary is the only contract between them.

## See also

- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — full webhook source argument list, plus every sink you can
  route incoming events to.
- [`webhook_listener` in the gallery](https://github.com/kmchandy/DisSysLab/tree/main/dissyslab/gallery/webhook_listener)
  — the working example used in this recipe.
- [How to filter for a topic](filter-for-a-topic.md) — pair the
  webhook listener with a filter agent so only the events you care
  about reach the rest of your office.
- [How to write a custom role](write-a-custom-role.md) — design
  the analyst agent that decides what each payload means.
- [How to send messages to the outside world](send-messages-outside.md)
  — route the keepers to email, Slack, or another webhook.
