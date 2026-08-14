"""
trader.py -- the paper_trader office's single transactional agent.

On the one history message from the source, it runs the whole book forward
(`run_through`): it bootstraps the book on first run, processes every
not-yet-committed trading day in order (catch-up / replay), and emits a summary
brief to the sink. All correctness lives in the tested pure modules + the store;
this role is thin framework glue.

Book files live in `book_dir/` (default `book/`, next to the office):
  config.json   -- OPTIONAL genesis config the user/Cowork edits (universe, cash,
                   initial_positions, policy, strategy). Absent -> sensible
                   defaults (SP-style basket from the source, $100k, flat).
  ledger.jsonl  -- append-only event log (source of truth)   [written by the store]
  book.json     -- derived snapshot cache                     [written by the store]

`as_of` (optional factory arg) caps the replay at a date -- leave unset for "today"
(the latest date in the data); set a past date to replay only up to there.
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP = os.path.dirname(_HERE)               # the paper_trader/ app root
for _p in (_APP, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from day_runner import run_through            # noqa: E402
from paper_store import create_book, read_ledger  # noqa: E402
from strategies import resolve                # noqa: E402

from dissyslab.blocks.role import Role         # noqa: E402
from dissyslab.office.library import AgentRoleEntry  # noqa: E402

_DEFAULT_POLICY = {
    "sizing": "inverse_vol", "no_trade_band": 0.005, "cost_bps": 5.0,
    "slippage_bps": 0.0, "stop_pct": 0.10, "exit_policy": "market_defined",
}


def _default_genesis(history_msg, strategy):
    tickers = list((history_msg.get("history") or {}).keys())
    return {"type": "genesis", "schema_version": 1, "book_id": f"paper:{strategy}",
            "strategy": strategy, "starting_cash": 100000.0, "universe": tickers,
            "initial_positions": {}, "policy": dict(_DEFAULT_POLICY)}


def _bootstrap_genesis(book_dir, history_msg, strategy):
    """Build the genesis for a new book from config.json if present, else
    defaults. config.json is the user-edited genesis config; it is separate from
    book.json (the store's snapshot cache), so the store never overwrites it."""
    cfg_path = os.path.join(book_dir, "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.setdefault("type", "genesis")
        cfg.setdefault("strategy", strategy)
        cfg.setdefault("policy", dict(_DEFAULT_POLICY))
        cfg.setdefault("starting_cash", 100000.0)
        cfg.setdefault("universe", list((history_msg.get("history") or {}).keys()))
        cfg.setdefault("initial_positions", {})
        return cfg
    return _default_genesis(history_msg, strategy)


def make_trader(book_dir, strategy, as_of):
    def trader_fn(history_msg):
        d = book_dir if os.path.isabs(book_dir) else os.path.join(os.getcwd(), book_dir)
        os.makedirs(d, exist_ok=True)
        if not read_ledger(d):                          # first run -> bootstrap
            create_book(d, _bootstrap_genesis(d, history_msg, strategy))
        compute_fn, params = resolve(strategy)
        briefs = run_through(history_msg, d, compute_fn, through=as_of, params=params)
        latest = briefs[-1] if briefs else None
        return {
            "type": "paper_trader_brief",
            "book_dir": d, "strategy": strategy,
            "days_processed": len(briefs),
            "latest_trade_date": latest.get("trade_date") if latest else None,
            "holdings": latest.get("holdings") if latest else None,
            "equity": latest.get("equity") if latest else None,
        }
    return trader_fn


role = AgentRoleEntry(
    name="trader",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda book_dir="book", strategy="mac_fast", as_of=None: Role(
        fn=make_trader(book_dir, strategy, as_of), statuses=["out"]
    ),
)
