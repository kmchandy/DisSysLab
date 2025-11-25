# 2.4 • Source: Polling JSON/REST for Numeric Streams

This page shows how to use a **connector** that polls a REST/JSON endpoint and turns it into a numeric stream you can process in DisSysLab.  Connectors are described in module 7.

---

## What you’ll do
Run a tiny script that polls the **Coinbase spot-price** endpoint ~1×/sec and prints a record each time the price changes.

---

## Setup (once)
```bash
pip install requests rich
```
> _Note:_ We use a public Coinbase endpoint (no API key required) purely as an example.  
> You can swap the URL and extractor for any JSON feed.

---

## The REST → Numeric Feed Demo

```python
# modules.ch02_sources.feed_numeric_price

from dsl import network
from dsl.connectors.live_kv_console import kv_live_sink
from dsl.connectors.numeric_rest_in import NumericREST_In

# Coinbase spot price (no API key). Returns JSON like:
# {"data":{"base":"BTC","currency":"USD","amount":"67890.12"}}
URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"


def coinbase_extract_fn(j):
    data = j.get("data", {})
    # Convert "amount" string -> float; include symbol for clarity.
    try:
        price = float(data.get("amount")) if data.get("amount") is not None else None
    except ValueError:
        price = None
    return {
        "symbol": f"{data.get('base', '?')}-{data.get('currency', '?')}",
        "price": price,
        "note": "Coinbase spot (REST)",
    }


price_source = NumericREST_In(
    url=URL,
    extract_fn=coinbase_extract_fn,
    poll_seconds=1.0,    # pace you can watch
    life_time=20.0,      # stop after ~20 s for the demo (None = run forever)
    dedupe=True,         # emit only on change
    epsilon=1e-4,        # require ≥ $0.0001 change to emit a new reading
)


def from_price():
    for msg in price_source.run():
        # Optionally compute derived fields here (e.g., returns, z-scores)
        yield msg


# Wire up the source to a live console sink.
g = network([(from_price, kv_live_sink)])

g.run_network()

if __name__ == "__main__":
    print("finished")
```

---

## Run the demo
Execute the following from the DisSysLab directory:

```python
python -m modules.ch02_sources.feed_numeric_price
```

You’ll see key–value output like this whenever the price changes:
```
----------------------------------------
symbol
BTC-USD

price
67890.12

note
Coinbase spot (REST)
```

You may have to wait for a few minutes to see changes in prices.
---

## Parameters you can modify

| Parameter | Type | Description |
|------------|------|--------------|
| **url** | str | Any JSON endpoint you’d like to poll. |
| **extract_fn** | callable | Maps raw JSON to a dict with at least a numeric field. |
| **poll_seconds** | float | How often to poll (e.g., `1.0`). |
| **life_time** | float \| None | Max wall-clock duration before auto-stop (`None` → run indefinitely). |
| **dedupe** | bool | If `True`, emit only when the numeric value changes. |
| **epsilon** | float | Minimum absolute change required to emit (suppresses noise). |
| **headers** | dict (optional) | Add HTTP headers if your API requires them. |

> _Tip:_ Your `extract_fn` can compute and output multiple fields (e.g., `{price, pct_change, ts}`) for downstream transforms or recorders.

---

## Troubleshooting

- **No output:** With `dedupe=True`, no messages appear until the value changes by at least `epsilon`.  
  Temporarily set `dedupe=False` to confirm polling works.
- **HTTP errors:** Check the URL, connectivity, or rate-limit policies. Increase `poll_seconds` if needed.
- **Non-numeric values:** Ensure `extract_fn` returns a float and handles exceptions defensively.

---

## 👉 Next
[**Replay archived data**  →](./README_5_replay.md). See how you can replay saved data to simulate live message streams.
