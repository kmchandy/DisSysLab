# Weather Monitor

> A weather briefing for your city every hour, on your laptop. Free.

`weather_monitor` polls a live weather service and writes a short
practical-advice briefing about today's conditions: *bring an
umbrella, dress warmly, enjoy the sunshine.* No app to install on
your phone, no service to subscribe to.

The smallest possible office DisSysLab can run: one source, one
agent, one sink.

## Set it up in 5 minutes

If you've already run another DSL office, just:

```bash
dsl run dissyslab/gallery/apps/weather_monitor/
```

If this is your first DSL office, see the
[top-level README](../../../../README.md) for the one-line installer
(installs Ollama + Qwen3 + DSL).

Default city is Pasadena, polled hourly. Change either in
`office.md`.

## What you'll see

Each hour, a one-line briefing appears in your terminal:

```
[Alex]  Current conditions in Pasadena: clear and 72°F. No rain
        expected today; light layers fine.
```

The same line is appended to `weather_monitor.jsonl` so you can
pipe it into other tools.

## Make it yours

### Tier 1 — Tweak  *(5 minutes, one parameter)*

Change the city or the polling interval in `office.md`:

```
Sources: weather(city="San Francisco", poll_interval=3600)
```

`poll_interval` is seconds. `3600` is once an hour; `600` is every
ten minutes; `21600` is once every six hours.

### Tier 2 — Modify  *(30 minutes, swap a component)*

**Make Alex sarcastic, poetic, or terse.** Edit
[`roles/analyst.md`](roles/analyst.md). The role is a single
plain-English prompt — change the persona and re-run.

**Save to a file instead of stdout.** Swap the sink in `office.md`:

```
Sinks: jsonl_recorder(path="~/weather.jsonl")
```

or open the file with your favourite editor when the office is
done.

**Add an alert.** If Alex's briefing mentions rain, route to a
notification sink (Slack, webhook, email). Add a second agent that
parses Alex's output and routes accordingly.

### Tier 3 — Build  *(a few hours)*

Combine weather with your calendar (see
[`calendar_briefing`](../calendar_briefing/)) to get *"Wear a coat
for your 9am client meeting downtown."* That's the kind of
multi-source office DisSysLab is designed for. See
[`docs/BUILD_APPS.md`](../../../../docs/BUILD_APPS.md).

## What you should expect

- **Quality**: clear, factual one-line summaries. Qwen3 reads the
  raw weather data and writes plain prose.
- **Speed**: ~10-30 seconds per briefing. Once an hour means you
  don't notice the latency.
- **Cost**: $0/month recurring. The Open-Meteo API used by the
  `weather` source is free and key-less.
- **Privacy**: the only data leaving your machine is the city name
  (to look up its current weather). Everything else stays local.

## See also

- [`office.md`](office.md) — the wiring (six lines).
- [`roles/analyst.md`](roles/analyst.md) — what Alex does (six
  more).
- [`situation_room`](../situation_room/README.md) — a much bigger
  office (9 agents, 3 sources, fork-merge) for journalists and
  analysts.
