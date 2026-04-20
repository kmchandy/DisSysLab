# Weather Monitor

Monitors the weather in a city you choose and delivers a short briefing
every hour with practical advice — bring an umbrella, dress warmly, enjoy
the sunshine.

## What it does

- Polls an open weather service once an hour for current conditions
- An analyst agent turns the raw data into a one-sentence briefing
- Output streams to your terminal and to `weather_monitor.jsonl`

## Try it

```bash
dsl init weather_monitor my_weather
cd my_weather
dsl run .
```

## Make it yours

- Change the city in `office.md`: `Sources: weather(city="...", poll_interval=3600)`
- Rewrite the analyst's personality in `roles/analyst.md` — make it terse,
  poetic, sarcastic; your call
- Add a second agent that reacts to the briefing (SMS, email, desktop
  notification)
