# Periodic Brief Pro

> The grown-up `periodic_brief`. News articles pass through a
> sense → think → respond pipeline (entity / topic / urgency
> tagging plus a writer); weather, stocks, calendar, and Gmail
> bypass the thinking layer and go straight to the brief. One
> richly-annotated HTML page each morning.

## Set it up

Three sets of credentials, in order of importance:

```bash
# 1. LLM backend (OpenRouter recommended — without this, the
#    s→t→r news pipeline runs on local Ollama and takes 20–40
#    minutes per run on a typical Mac. On OpenRouter with the
#    default Qwen-2.5-7B it takes 1–3 minutes.)
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...

# 2. Google Calendar (private ICS URL — get it from
#    Settings → Integrate calendar → Secret address in iCal format)
export CALENDAR_ICS_URL='https://calendar.google.com/calendar/ical/...'

# 3. Gmail (app password — not your normal Google password)
export GMAIL_USER='you@gmail.com'
export GMAIL_APP_PASSWORD='your-16-char-app-password'
```

If you only have two of three, comment out the missing source(s)
in `office.md`. The remaining sources still produce a brief.

## Run it

```bash
dsl run periodic_brief_pro
open brief.html
```

About 1–3 minutes on OpenRouter (Qwen-2.5-7B); 20–40 minutes on local Ollama.
The HTML page auto-refreshes every 60 seconds if you leave it
open in your browser — sections fill in as agents finish their
work.

## What you should expect

A multi-section HTML page with:

- A hero banner showing today's date and at-a-glance stats.
- **Schedule:** next 24 hours from your Google Calendar.
- **Weather:** current conditions for Pasadena (edit `office.md`
  for your city).
- **Markets:** Apple, Nvidia, Microsoft (edit for your tickers).
- **Email worth knowing about:** Gmail messages that the
  `mail_summariser` agent decided are real correspondence — bills,
  personal emails, calendar invitations — with one-line headlines.
  Newsletters and noise are filtered out.
- **News:** articles from BBC and NPR, each annotated with
  entities, topic, urgency badges, and a writer-composed
  one-paragraph brief.

Compared to `periodic_brief`, the difference is the *News* section —
in `periodic_brief` it's a raw headline list, in `periodic_brief_pro`
each headline is replaced by a writer-composed paragraph with
entity / topic / urgency tags. Also the *Email* section, which
the simpler office doesn't have.

## Cost

- OpenRouter: ~5–10 cents per run (depends on inbox size).
- Anthropic Claude (per-role): a few cents per run if just the
  writer uses Claude; ~50 cents per run if all agents use Claude.
- Cron daily: pennies to a dollar per month depending on backend.

## Make it yours

The office is hybrid: the news pipeline follows sense → think →
respond (see [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)),
while weather / stocks / calendar / gmail bypass it. You can edit
each part independently:

- **Sources:** change the news feeds, the weather city, the stock
  tickers, or the Gmail filters.
- **News thinkers:** Eve / Tom / Sam in `Agents:`. Drop one or
  swap in a different library role.
- **Writer:** Riley uses `summary_writer`. Edit
  `dissyslab/roles/summary_writer.md` (or override locally) to
  change the brief style.
- **Mail filter:** `roles/mail_summariser.md` decides which emails
  make the brief and writes the one-line headlines. Edit to taste.
- **Sinks:** swap `periodic_brief_html_sink` for the markdown
  version if you prefer plain text.

## See also

- [`periodic_brief`](../periodic_brief/) — the credential-free,
  no-LLM version. Try this first to see the framework working in
  ten seconds.
- [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
  — the pattern instantiated by the news pipeline.
- [`docs/LANGUAGE_MODELS.md`](../../../../docs/LANGUAGE_MODELS.md)
  — backend choice, per-role overrides, cost comparisons.
