# modules/02_sources/feed_numeric_price.py
#
# Goal:
# - Shows a numeric stream at  ~1 msg/sec.
# - You can swap URL/extractor for any JSON feed.

from dsl import network
from dsl.connectors.live_kv_console import kv_live_sink
from dsl.connectors.numeric_rest_in import NumericREST_In

# Coinbase spot price (no API key). Returns:
# {"data":{"base":"BTC","currency":"USD","amount":"67890.12"}}
URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"


def coinbase_extract_fn(j):
    data = j.get("data", {})
    # Convert "amount" string -> float; add symbol + a local timestamp for display.
    try:
        price = float(data.get("amount")) if data.get(
            "amount") is not None else None
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
    poll_seconds=1.0,   # <- pace you can watch
    # stop after 60s for the demo (set None to run forever)
    life_time=60.0,
    dedupe=True,
    epsilon=1e-4,       # require >=$0.0001 change to emit a new reading
)


def from_price():
    for msg in price_source.run():
        # You can compute derived fields here if you like (e.g., returns)
        yield msg


g = network([(from_price, kv_live_sink)])
g.run_network()

if __name__ == "__main__":
    print("finished")
