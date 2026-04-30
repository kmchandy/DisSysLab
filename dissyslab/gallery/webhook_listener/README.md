# Webhook Listener

Listens for inbound HTTP POSTs and lets an analyst summarize each
one. Useful as a starting point for any office that needs to
react to events from another service — GitHub pushes, Stripe
charges, Zapier triggers, or another DisSysLab office posting
across the network.

**Tags:** webhook, single-agent, http, push

## What it does

- Spins up a stdlib HTTP listener on `localhost:8000/webhook`
- For every POST that arrives, an analyst agent decides whether
  the payload is real or a health check / malformed
- Real payloads get a one-sentence summary printed to your
  terminal; everything else lands in `webhook_log.jsonl` for
  spot-checking

## Files in this office

```
webhook_listener/
    office.md          ← the org chart: source, agent, sinks
    roles/
        analyst.md     ← what the agent does, in plain English
```

## Try it

```bash
dsl init webhook_listener my_listener
cd my_listener
dsl run .
```

In a second terminal, post a test message:

```bash
curl -X POST http://localhost:8000/webhook \
  -H 'Content-Type: application/json' \
  -d '{"title":"test","text":"hello from curl"}'
```

You should see the analyst's one-sentence summary appear in the
first terminal. Try a few more — empty body, JSON without a
`text` field, a ping payload — and watch the analyst route them
to keep or discard.

## Make it yours

- Change the port or path in `office.md`:
  `Sources: webhook(port=9000, path="/incoming")`
- Rewrite the analyst in `roles/analyst.md` to match the kind of
  events you're receiving — a GitHub push hook is very different
  from a Stripe charge hook
- Swap `console_printer` for `slack_sink` to forward summaries
  to a Slack channel, or `gmail_sink` to email yourself
- See [`docs/SOURCES_AND_SINKS.md`](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  for the full list of sources and sinks you can swap in

**Recipe.** [How to receive webhooks](https://github.com/kmchandy/DisSysLab/blob/main/docs/recipes/receive-webhooks.md)
walks through the listener setup, shows how to test with `curl`,
and explains how to make the listener reachable from the public
internet using `ngrok`.
