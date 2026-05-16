# Inbox Triage

> An office that watches your Gmail inbox, rates each unread email
> by urgency and sentiment, summarises it in one sentence, and
> drops a digest of the keepers into Slack.

A sense → think → respond office. Each unread email passes through
three parallel thinkers — `urgency_classifier`, `sentiment_classifier`,
`summarizer` — then a `summary_writer` composes a short brief per
email and posts the kept ones to Slack.

## Set it up

You need three environment variables:

```bash
# Gmail (app password — not your normal Google password)
export GMAIL_USER='you@gmail.com'
export GMAIL_APP_PASSWORD='your-16-char-app-password'

# Slack incoming webhook for the channel you want digests in
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'

# A backend with API key (OpenRouter recommended)
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
```

Get a Gmail app password at `myaccount.google.com → Security →
App passwords`. Get a Slack incoming webhook at
`api.slack.com/apps → your app → Incoming Webhooks`.

## Run it

```bash
dsl run inbox_triage
```

The office reads up to 20 unread emails, rates and summarises each,
and posts a Slack digest of the keepers. Rejected emails go to
`inbox_discard.jsonl` for audit. Runs in 1–3 minutes on OpenRouter
for a typical inbox.

## What you should expect

- **Quality:** depends on prompt tuning. The default prompts in
  `dissyslab/roles/` are calibrated for general inboxes. Open them
  and edit if you want different criteria.
- **Speed:** ~1–3 minutes on OpenRouter (Qwen-2.5-7B) for 20 emails.
  10–30 minutes on local Ollama.
- **Cost:** under 1 cent per run on OpenRouter for 20 emails.

## Make it yours

Edit [`office.md`](office.md):

- **SLOT 1 (sources):** change Gmail filters; add a webhook to also
  triage form submissions.
- **SLOT 2 (thinkers):** drop `sentiment_classifier`, add
  `category_classifier`, etc.
- **SLOT 3 (writer):** swap `summary_writer` for a custom writer
  that produces a different style of digest.
- **SLOT 4 (sinks):** route to email instead of Slack, or also
  archive everything to JSONL.

See [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for the pattern this office instantiates.
