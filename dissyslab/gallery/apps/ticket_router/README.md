# Ticket Router

> An office that listens on a webhook for support tickets,
> classifies each by severity, urgency, and category, composes
> a one-paragraph summary, and posts the keepers to a Slack
> oncall channel.

A sense → think → respond office. Each incoming ticket passes
through three parallel thinkers — `severity_classifier`,
`urgency_classifier`, `category_classifier` — then a
`summary_writer` composes the alert text and posts it to the
configured Slack channel. Rejected tickets are archived to a JSONL
file for audit.

## Set it up

```bash
# Slack webhook for the oncall channel
export SLACK_ONCALL_WEBHOOK='https://hooks.slack.com/services/...'

# A backend with API key (OpenRouter recommended)
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
```

The office listens on `http://localhost:8000/tickets`. Point your
ticket system (or `curl` for testing) at that URL with a JSON
payload like:

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"title": "Login broken", "text": "Users cant log in since 9am", "url": "https://tickets.example/123"}'
```

## Run it

```bash
dsl run ticket_router
```

The office runs forever, waiting for inbound POSTs. Each ticket is
classified and routed to either the oncall Slack channel or the
archive JSONL. Press Ctrl-C to stop.

## What you should expect

- **Latency:** ~10–30 seconds per ticket from POST to Slack post on
  OpenRouter (Qwen-2.5-7B). ~3–8 minutes on local Ollama (one ticket
  at a time; Ollama serialises).
- **Cost:** sub-penny per ticket on OpenRouter.
- **Reliability:** the office is your filter. Make sure the
  thinker prompts match your team's notion of severity / urgency.

## Make it yours

Edit [`office.md`](office.md):

- **SLOT 1 (sources):** change the webhook port or add a second
  source (e.g., gmail for tickets that come by email).
- **SLOT 2 (thinkers):** replace `category_classifier` with a
  `customer_tier_classifier` you write locally; the framework will
  prefer your local override over the library default.
- **SLOT 3 (writer):** edit `summary_writer`'s style — short alert
  vs. structured incident report.
- **SLOT 4 (sinks):** route critical tickets to one Slack channel
  and informational tickets to another, or page someone via a
  webhook to PagerDuty.

See [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for the pattern.
