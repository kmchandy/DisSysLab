# Sample run summary — periodic_brief

A representative invocation, summarised. Claudette reads this
to understand the *shape* of what the office produces, without
needing to actually run it.

---

## Invocation

```bash
dsl run periodic_brief
```

## What each source emitted (representative)

### bbc_world (RSS, max_articles=5)

5 messages, each a dict like:

```json
{
  "source": "bbc_world",
  "title": "UN climate summit ends with limited agreement",
  "url": "https://www.bbc.com/news/world-XXXXXXXX",
  "published_at": "2026-06-25T14:32:00Z",
  "snippet": "Negotiators in Bonn..."
}
```

### npr_news (RSS, max_articles=5)

Similar shape, source = "npr_news".

### weather (Open-Meteo, max_readings=1)

1 message:

```json
{
  "source": "weather",
  "city": "Pasadena",
  "observed_at": "2026-06-25T16:00:00Z",
  "temperature_c": 24.1,
  "conditions": "Sunny",
  "wind_kph": 8.4
}
```

### stocks / stocks_2 / stocks_3 (max_readings=1 each)

1 message per source:

```json
{
  "source": "stocks",
  "ticker": "AAPL",
  "price": 218.43,
  "change_pct": 0.7,
  "as_of": "2026-06-25T20:15:00Z"
}
```

## What the sink produced

A single `brief.html` file. Visual structure:

```
┌─────────────────────────────────────────────┐
│  Periodic Brief — 2026-06-25                │
├─────────────────────────────────────────────┤
│  MARKETS                                    │
│    AAPL    $218.43   +0.7%                  │
│    NVDA    $124.20   +1.3%                  │
│    MSFT    $431.10   -0.2%                  │
│                                             │
│  WEATHER — Pasadena                         │
│    24°C  Sunny  Wind 8 km/h                 │
│                                             │
│  NEWS                                       │
│    [BBC] UN climate summit ends with...     │
│    [BBC] Currency markets steady after...   │
│    [NPR] House passes amended infrastructure│
│    [NPR] Heat wave forecast for Southwest...│
│    ... (10 more)                            │
└─────────────────────────────────────────────┘

<meta http-equiv="refresh" content="60">
```

## Total messages: 13

3 stock + 1 weather + 5 BBC + 5 NPR = 14 inputs, 1 HTML output,
about ten seconds wall time, zero LLM calls, zero API keys.

## What this tells Claudette

If the new task's expected output looks like *"a single
human-readable artifact combining N heterogeneous source types,
each rendered in its own section"*, this office's shape is the
right starting point. If the expected output looks like *"a
per-item structured record" or "an alert" or "a continuously
updated dashboard with persistent state"*, look at other
precedents.
