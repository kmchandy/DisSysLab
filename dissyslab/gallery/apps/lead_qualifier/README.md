# Lead Qualifier

> An office that listens on a webhook for form submissions,
> summarises each lead, tags sentiment and urgency, and forwards
> the qualified ones to your CRM via outbound webhook.

A sense → think → respond office. Each lead passes through three
parallel thinkers — `summarizer`, `sentiment_classifier`,
`urgency_classifier` — then `summary_writer` composes the lead
description and forwards it to your CRM webhook. Discarded leads
go to `leads_discard.jsonl` for audit.

## Set it up

```bash
# Your CRM's incoming webhook URL
export CRM_WEBHOOK_URL='https://your-crm.example.com/incoming'

# A backend with API key (OpenRouter recommended)
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
```

The office listens on `http://localhost:8001/leads`. Point your
form-submission system (or `curl` for testing) at that URL:

```bash
curl -X POST http://localhost:8001/leads \
  -H "Content-Type: application/json" \
  -d '{"title": "Demo request from Acme Corp",
        "text": "Hi, our team of 50 wants to evaluate your product. Budget allocated.",
        "url": "https://forms.example/sub/4421"}'
```

## Run it

```bash
dsl run lead_qualifier
```

The office runs forever, waiting for inbound POSTs. Each lead is
classified and either POSTed onward to the CRM URL or recorded as
discarded. Press Ctrl-C to stop.

## What you should expect

- **Latency:** ~10–30 seconds per lead from POST to CRM forward on
  OpenRouter (Qwen-2.5-7B).
- **Cost:** sub-penny per lead on OpenRouter.
- **Honest limit:** the office classifies general sentiment and
  urgency. To rank leads against *your* product's qualification
  criteria (industry fit, budget threshold, decision-maker
  presence), edit `roles/summarizer.md` locally or add a custom
  thinker.

## Make it yours

Edit [`office.md`](office.md):

- **SLOT 1 (sources):** add `gmail` for leads that come by email,
  or `file_source` for batch processing exported CSVs.
- **SLOT 2 (thinkers):** add a `budget_extractor` you write
  locally, or a `qualified_filter` that scores against your ICP.
- **SLOT 3 (writer):** customise — *one-line slack alert* vs
  *full CRM activity record*.
- **SLOT 4 (sinks):** add a `slack_sink_alerts` so the sales team
  gets a real-time ping in addition to the CRM record.

See [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for the pattern.
