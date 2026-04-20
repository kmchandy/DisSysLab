# Calendar Briefing

Monitors your calendar for upcoming events over the next week and delivers
a short briefing about what's on your plate.

## What it does

- Polls your calendar every five minutes for events in the next 7 days
- An analyst agent reviews the events and writes a concise summary
- Output streams to your terminal and to `calendar_briefing.jsonl`

## Try it

```bash
dsl init calendar_briefing my_calendar
cd my_calendar
dsl run .
```

## Make it yours

- Change the lookahead in `office.md`: `Sources: calendar(poll_interval=300, days_ahead=7)`
- Rewrite the analyst in `roles/analyst.md` to focus on particular kinds of
  events (meetings only, deadlines, social events)
- Add a second agent that flags conflicts, double-bookings, or gaps
