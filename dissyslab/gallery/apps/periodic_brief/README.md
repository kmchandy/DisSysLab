# Periodic Brief

> One markdown file each morning combining news, weather, your
> calendar, and your email — free, runs on your laptop.

`periodic_brief` is the office that does what most people *wish*
ChatGPT did: combine multiple things you care about into one
cohesive briefing, on a schedule, automatically. Out of the box it
mixes BBC + NPR news and your local weather. Add your Google
Calendar and your unread email with two extra lines.

The showpiece for what an office of AI agents can do that a single
chatbot prompt can't: orchestrate several different sources into
one coherent artifact.

## Set it up in 5 minutes

The default config uses **only news + weather** — no credentials,
no setup beyond DisSysLab itself:

```bash
dsl run dissyslab/gallery/apps/periodic_brief/
```

After ~3-5 minutes (mostly news fetches), `brief.md`
appears in your working directory.

For the full version with calendar and email, see *Tier 2* below.

## What you'll see

A single markdown file like this:

```markdown
# Periodic brief — 2026-05-12

## Weather

Clear and 72°F in Pasadena, no rain expected.

## World

- UN Security Council to vote on Lebanon ceasefire today [bbc_world](https://www.bbc.com/news/...)
- US inflation report due 8:30am ET [npr_news](https://www.npr.org/...)
- New MacBook Pro M5 announced at WWDC [bbc_world](https://www.bbc.com/news/...)
- Iran sends response to US peace proposals [bbc_world](https://www.bbc.com/news/...)
- Cape Verde reaches first World Cup [npr_news](https://www.npr.org/...)
```

Open it in any markdown viewer. Cron-schedule it for 6am and your
morning briefing arrives before you do.

## Make it yours

### Tier 1 — Tweak  *(5 minutes, one parameter)*

Change the city, the number of articles, or add another news feed
in [`office.md`](office.md):

```
Sources: bbc_world(max_articles=10), techcrunch(max_articles=5), weather(city="San Francisco", max_readings=1)
```

Available news feeds: `bbc_world`, `bbc_tech`, `npr_news`,
`al_jazeera`, `hacker_news`, `techcrunch`, `mit_tech_review`,
`venturebeat_ai`, `nasa_news`, `python_jobs`. Pick the ones that
match your information diet.

### Tier 2 — Modify  *(30 minutes, add calendar + email)*

The default brief skips calendar and email because they need
credentials. To add them, edit `office.md`:

```
Sources:
  bbc_world(max_articles=5),
  npr_news(max_articles=5),
  weather(city="Pasadena", max_readings=1),
  calendar(days_ahead=1),
  gmail(unread_only=True, max_emails=20)

Sinks:
  periodic_brief_sink(path="brief.md"),
  discard

Agents:
  Mail is a mail_summariser.

Connections:
  bbc_world's destination is periodic_brief_sink.
  npr_news's destination is periodic_brief_sink.
  weather's destination is periodic_brief_sink.
  calendar's destination is periodic_brief_sink.
  gmail's destination is Mail.
  Mail's keep is periodic_brief_sink.
  Mail's discard is discard.
```

Then set the credentials in your shell:

```bash
# Calendar — Google Calendar private ICS URL
# (Settings → Integrate calendar → Secret address in iCal format)
export CALENDAR_ICS_URL="https://calendar.google.com/calendar/ical/..."

# Email — Gmail App Password (myaccount.google.com/apppasswords)
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
```

Re-run. Your brief now has four sections: Schedule, Weather, Email
worth knowing about, World.

The `Mail` agent runs an LLM-driven `mail_summariser` that decides
which emails matter (skips newsletters, promos, automated
notifications) and writes a one-line summary for each.

### Tier 3 — Build  *(a few hours, write a new role or section)*

**Add a stocks section.** Drop a ticker watch into the brief:

```
Sources: ... , stocks(ticker="AAPL"), stocks(ticker="MSFT")
Connections:
  ... existing
  stocks's destination is periodic_brief_sink.
```

The `periodic_brief_sink` doesn't know about a "stocks" category
yet — it'll route into "World." If you want a dedicated **##
Stocks** section, edit the sink at
[`dissyslab/components/sinks/periodic_brief_sink.py`](../../../components/sinks/periodic_brief_sink.py)
and add a new bucket.

**Use Claude for the writer.** Add a role override that wraps the
framework's roles in `nl_role(prompt, AI="claude")` — see the
[`situation_room_pro`](../situation_room_pro/) pattern.

**Compose with sub-offices.** Have `situation_room` run as a
sub-office that feeds enriched briefings into `periodic_brief`'s
World section. See
[`docs/BUILD_APPS.md`](../../../../docs/BUILD_APPS.md) for the
sub-office pattern.

## What you should expect

- **Quality**: news headlines pass through verbatim; weather is
  one factual line; email summaries are filter-and-paraphrase done
  by Qwen3 (or whichever model you've configured). Mail's
  filtering is calibrated to skip newsletters and notification
  emails — review the prompt in [`roles/mail_summariser.md`](roles/mail_summariser.md)
  to adjust.
- **Speed**: news + weather only — about 30 seconds. With calendar
  + email — 1-3 minutes depending on email volume (each kept email
  is one LLM call).
- **Cost**: $0/month recurring on free local Qwen via Ollama. On
  Claude: roughly $0.05 per run; ~$1.50/month if you run it every
  morning.
- **Privacy**: with Ollama, nothing leaves your machine. With a
  paid backend, each kept email's text goes to that provider for
  the mail_summariser's classification.

## Schedule it

Put this in your crontab (`crontab -e`):

```
0 6 * * *  cd /Users/you/Documents/DisSysLab && DSL_BACKEND=ollama dsl run dissyslab/gallery/apps/periodic_brief/ > /tmp/dsl.log 2>&1
```

At 6am every day, the office runs; `brief.md` is updated;
your morning coffee has reading material.

## See also

- [`office.md`](office.md) — the wiring (six lines).
- [`roles/mail_summariser.md`](roles/mail_summariser.md) — the
  filter-and-summarise role used when Gmail is enabled.
- [`situation_room`](../situation_room/README.md) — the bigger
  cousin: deeper news analysis (severity, entities, geo) on three
  feeds, with editorial review.
- [`weather_monitor`](../weather_monitor/README.md) — the
  simplest possible office. Read this if you want to learn how a
  one-source / one-agent / one-sink office is shaped.
