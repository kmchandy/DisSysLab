# dsl/connectors/numeric_rest_in.py
#
# A simple numeric REST poller that emits dict messages at a steady pace.
# Default example pulls BTC-USD spot price from Coinbase (no API key).

from __future__ import annotations
import time
import json
from typing import Callable, Dict, Iterable, Optional
import urllib.request


class NumericREST_In:
    """
    Polls a REST JSON endpoint at fixed intervals and yields numeric readings.

    Params:
      url: REST endpoint returning JSON.
      extract_fn: function(json_obj) -> Dict  # pick/compute fields to emit
      poll_seconds: seconds between polls.
      life_time: total seconds before STOP (None = run forever).
      dedupe: if True, suppress emits when payload hasn't changed.
      epsilon: float threshold for numeric change detection (if applicable).

    Message shape:
      A dict produced by extract_fn (e.g., {"symbol": "BTC-USD", "price": 67321.12, "ts": "..."}).
    """

    def __init__(
        self,
        *,
        url: str,
        extract_fn: Callable[[dict], Dict],
        poll_seconds: float = 1.0,
        life_time: Optional[float] = 20.0,
        dedupe: bool = True,
        epsilon: float = 1e-9,
        name="NumericREST_In",
    ):
        self.url = url
        self.extract_fn = extract_fn
        self.poll_seconds = poll_seconds
        self.life_time = life_time
        self.dedupe = dedupe
        self.epsilon = epsilon

    def _fetch_json(self) -> dict:
        with urllib.request.urlopen(self.url, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def _equal(self, a: Dict, b: Dict) -> bool:
        if a.keys() != b.keys():
            return False
        for k, va in a.items():
            vb = b.get(k)
            # numeric close?
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                if abs(float(va) - float(vb)) > self.epsilon:
                    return False
            else:
                if va != vb:
                    return False
        return True

    def run(self) -> Iterable[Dict]:
        start = time.time()
        last: Optional[Dict] = None
        while self.life_time is None or (time.time() - start) < self.life_time:
            try:
                j = self._fetch_json()
                payload = self.extract_fn(j)  # must return a dict
                if not self.dedupe or last is None or not self._equal(payload, last):
                    yield payload
                    last = payload
            except Exception as e:
                # Emit an error message but keep going (good for lessons)
                yield {"error": str(e)}
            time.sleep(self.poll_seconds)
