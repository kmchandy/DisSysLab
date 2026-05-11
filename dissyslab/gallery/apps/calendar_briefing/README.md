# Calendar Briefing

> A short briefing of what's coming up on your calendar — once
> every few minutes, on your laptop. Free.

`calendar_briefing` pulls upcoming events from your Google
Calendar and writes a one-line summary per event: *what it is,
when, where, and whether it looks important.* Useful for "what
does my afternoon look like" without opening Google Calendar.

A single-agent office that reads from a real personal feed (your
calendar) and writes to your terminal.

## Set it up in 10 minutes

This office reads your Google Calendar, which means a Gmail App
Password is required (Google's two-factor-aware credential for
programs reading your data).

1. **Install DisSysLab** if you haven't yet — see the
   [top-level README](../../../../README.md).

2. **Get a Gmail App Password.** At
   [myaccount.google.com → Security → App Passwords](https://myaccount.google.com/apppasswords),
   create a 16-character password. (Requires 2-Step Verification
   on your Google account.)

3. **Set the credentials** in your environment:

   ```bash
   export GMAIL_USER="your.email@gmail.com"
   export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
   ```

4. **Run the office:**

   ```bash
   dsl run dissyslab/gallery/apps/calendar_briefing/
   ```

Default behavior: poll every 5 minutes, look 7 days ahead.

## What you'll see

For each upcoming event, a briefing appears in your terminal:

```
[Alex]  Tomorrow 9-10am: 1:1 with Dana (Zoom). Routine weekly
        check-in — no prep mentioned.

[Alex]  Friday 2pm: Quarterly board meeting (HQ conf room 4).
        Important; agenda attached to invite.
```

The same lines append to `calendar_briefing.jsonl` for downstream
tools.

## Make it yours

### Tier 1 — Tweak  *(5 minutes, one parameter)*

Change the polling cadence or look-ahead window in `office.md`:

```
Sources: calendar(poll_interval=900, days_ahead=14)
```

`poll_interval=900` is every 15 minutes. `days_ahead=14` looks two
weeks out instead of one.

### Tier 2 — Modify  *(30 minutes, swap a component)*

**Get a single daily summary instead of per-event briefings.**
Combine briefings with `markdown_digest`:

```
Sinks: markdown_digest(path="~/daily_calendar.md")
```

Once a day, `cat ~/daily_calendar.md` for everything ahead.

**Filter for "important" events only.** Edit
[`roles/analyst.md`](roles/analyst.md) so Alex routes to two
ports — `important` and `routine` — and route `important` to a
notification sink (email, Slack).

**Use Claude for high-stakes events, Qwen for routine ones.** See
the [`situation_room_pro`](../situation_room_pro/) pattern for
per-role backend override.

### Tier 3 — Build  *(a few hours)*

Combine your calendar with weather (see
[`weather_monitor`](../weather_monitor/)) for *"Wear a coat for
your 9am client meeting downtown."* Combine with your inbox to
pre-read related emails before each meeting. See
[`docs/BUILD_APPS.md`](../../../../docs/BUILD_APPS.md).

## What you should expect

- **Quality**: one-line factual reads of your calendar events.
  Alex doesn't invent attendees or change times.
- **Speed**: a few seconds per event briefing. Total run time
  depends on event count.
- **Cost**: $0/month recurring. Your Gmail App Password is free.
- **Privacy**: calendar data leaves your machine *only* if you
  configure a paid-LLM backend like Claude. On the default Ollama
  path, your events stay local.

## ⚠ Privacy note

This office reads your real calendar. Treat the
`GMAIL_APP_PASSWORD` like any other credential — don't commit it
to git, don't email it to yourself, rotate it if exposed.

On the recommended Ollama backend, calendar data never leaves
your machine. On a paid-LLM backend, each event's text gets sent
to your chosen provider for analysis. Choose accordingly.

## See also

- [`office.md`](office.md) — the wiring.
- [`roles/analyst.md`](roles/analyst.md) — Alex's job description.
- [`weather_monitor`](../weather_monitor/README.md) — combine
  with this for situational morning briefings.
