# Paper port 9: `mac_speed_suite` (the larger application)

Ported by hand against `officespeak_revised.md`. Nothing here runs yet. The
facts about the current office come from a full read of its 20 files (office,
roles, helper modules, sink, source, and the `backtest-strategy-builder`
skill).

Four families of trend-following rules (moving-average crossover, Donchian,
Turtle, relative strength), 11 variants in all, are backtested on five stocks.
Each run is validated twice: walk-forward (a full span, then 4 train/test
folds) and Monte Carlo (100 resampled histories). That is 109 spans, each
passing once through the whole network. A report collects the results.

## How it works today

```
csv_stock_history → GATE → MKT → 4 signal computers → 11 backtesters → JOIN → EVAL → CMP ─ out  → console, report.html
                     ↑                                                                    └─ next → GATE
```

- **The source** sends one message holding ten years of daily bars for all
  five tickers.
- **GATE** (a framework `Agent` subclass with its own loop) stores it, makes a
  plan of 109 spans, and sends one span at a time. A span is a slice of the
  history (walk-forward) or a resampled history (Monte Carlo), tagged with
  `_wf_tag = {fold, role, total_spans, run_config}`. Each later message on
  the same inbox, from CMP's `next`, releases the next span.
- **MKT** adds a market `context` (used only by the relative-strength rule).
- **Each signal computer** builds a new message of daily signals for its
  family's variants. The history and context are not forwarded.
- **Each backtester** (`speed_name='mac_fast'`, …) puts its result under a
  field **named by its argument**: `{"mac_fast": {...}}`.
- **JOIN** merges the 11 results positionally.
- **EVAL** treats every field except `type`, `ticker_volatility` and `_wf_tag`
  as a variant's result.
- **CMP** (another `Agent` subclass) accumulates 109 evaluations. After each
  one it sends `{"walkforward_next": true}` back to GATE; after the last, it
  sends the scorecard instead.

Every role imports `dissyslab`. Two are `Agent` subclasses; the rest return
`(message, port)` pairs. Helper modules are imported through a
`sys.path.insert` in each role file.

## After

```
sources:
    prices: csv_stock_history(tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"],
                              filename_pattern="{ticker}_10_year.csv")

sinks:
    console_printer
    report_html(path="report.html")

agents:
    Plan: validation_plan(n_folds=4, n_samples=100, seed=42, block_size=20, stop_pct=0.10)
    MKT: market_context
    MAC: mac_signal
    DON: donchian_signal
    TURTLE: turtle_signal
    RS: rs_trend

    BT_MAC_FAST: backtester(variant="mac_fast")
    BT_MAC_MED_FAST: backtester(variant="mac_med_fast")
    BT_MAC_MED: backtester(variant="mac_med")
    BT_MAC_MED_SLOW: backtester(variant="mac_med_slow")
    BT_MAC_SLOW: backtester(variant="mac_slow")
    BT_DON_20: backtester(variant="donchian_20")
    BT_DON_55: backtester(variant="donchian_55")
    BT_TURTLE_S1: backtester(variant="turtle_s1")
    BT_TURTLE_S2: backtester(variant="turtle_s2")
    BT_RS_FAST: backtester(variant="rs_fast")
    BT_RS_SLOW: backtester(variant="rs_slow")

    JOIN: synchronizer(on="span", collect="results")
    EVAL: evaluator
    CMP: comparator
    Rex: router(on="msg_type")

connections:
    prices -> Plan -> MKT -> MAC, DON, TURTLE, RS
    MAC -> BT_MAC_FAST, BT_MAC_MED_FAST, BT_MAC_MED, BT_MAC_MED_SLOW, BT_MAC_SLOW
    DON -> BT_DON_20, BT_DON_55
    TURTLE -> BT_TURTLE_S1, BT_TURTLE_S2
    RS -> BT_RS_FAST, BT_RS_SLOW
    BT_MAC_FAST -> JOIN.mac_fast
    BT_MAC_MED_FAST -> JOIN.mac_med_fast
    BT_MAC_MED -> JOIN.mac_med
    BT_MAC_MED_SLOW -> JOIN.mac_med_slow
    BT_MAC_SLOW -> JOIN.mac_slow
    BT_DON_20 -> JOIN.donchian_20
    BT_DON_55 -> JOIN.donchian_55
    BT_TURTLE_S1 -> JOIN.turtle_s1
    BT_TURTLE_S2 -> JOIN.turtle_s2
    BT_RS_FAST -> JOIN.rs_fast
    BT_RS_SLOW -> JOIN.rs_slow
    JOIN -> EVAL -> CMP -> Rex
    Rex.next -> Plan
    Rex.scorecard -> console_printer, report_html
```

The run settings testers tune are now all on two declaration lines (`prices`
and `Plan`) plus `cost_bps=` on the backtesters; the 30 lines of comments
explaining them move to the README.

### The roles under the new rules

| Agent | Kind | `in:` | `out:` | State |
|---|---|---|---|---|
| Plan (`validation_plan`) | Python author | `msg_type` | `msg_type (span)`, `span`, `span_info`, `tickers`, `history` | the full history, the plan, a cursor |
| MKT (`market_context`) | Python annotator | `history` | `context` | none |
| MAC, DON, TURTLE, RS | Python authors | `span`, `span_info`, `history` (RS also `context`) | `msg_type (signals)`, `span`, `span_info`, `tickers`, `series`, `ticker_volatility` | none |
| BT_* (`backtester`) | Python author | `span`, `series` | `msg_type (backtest)`, `span`, `span_info`, `variant`, `result`, `ticker_volatility` | none |
| JOIN | synchronizer | | `span`, `results` | per-span groups |
| EVAL (`evaluator`) | Python author | `span`, `span_info`, `results` | `msg_type (evaluation)`, `span`, `span_info`, `table`, `ranked`, … | none |
| CMP (`comparator`) | Python author | `span_info`, `table`, … | `msg_type (next \| scorecard)`; `out if msg_type is scorecard:` the report fields | the evaluations so far |

- `_wf_tag` becomes two fields: `span` (a short name, `"full"`, `"train_2"`,
  `"mc_017"`, used as the synchronizer's key) and `span_info` (the rest).
- Plan receives two kinds of message on one inbox: the price history
  (`msg_type: "history"`, set by the source) and CMP's `{"msg_type": "next"}`.
  They share a field that tells them apart, as section 14 asks.
- A signal computer and a backtester are authors because they deliberately
  build a smaller message: forwarding ten years of bars through 11
  backtesters would multiply memory for nothing.

## Findings

1. **A synchronizer over many identical workers needs a collected form.**
   Today each backtester writes its result under a field named by its
   argument (`speed_name`), and EVAL guesses that every unrecognised field is
   a result. A field whose *name* depends on an argument cannot be declared in
   `out:`, and the guess breaks as soon as any other field travels with the
   message. **Proposal:** a synchronizer option,
   `synchronizer(on="span", collect="results")`: the merged message is the
   key plus one field, `results`, mapping each inbox name to the message that
   arrived on it. Nothing is merged, so nothing can conflict. Each backtester
   says which variant it is in a `variant` field, so EVAL reads
   `results.values()` and needs no names at all.
   (In `debate` the plain merge stays right: three different fields from
   three panellists.)

2. **A failure inside a loop stops the loop.** If any role fails on one span
   (a contract check, a bad ticker), that span never reaches CMP, CMP never
   sends `next`, Plan waits for ever, and the office goes quiet with no
   report. The same holds for every gate loop (`debate`, `returns_desk`).
   Section 4.5 drops and counts the failed message, which is right, but then
   says "the office continues", which here it cannot. **Proposal:** when the
   office goes quiet, the run summary says which agents were still waiting,
   and on which inbox (Plan waiting on `in` for `next`, JOIN holding an
   incomplete group for span `mc_017`), next to the first failure. `dsl run`
   exits non-zero. Nothing is retried or invented. Termination detection
   already knows when the office is quiet; this only reports what it sees.

3. **Helper modules in `roles/`.** 3,276 lines of shared machinery
   (`_walkforward.py`, `_signal_common.py`, `_backtester_core.py`,
   `evaluator.py`, `_contract_checks.py`, …) are imported by the role files
   through `sys.path.insert`. **Proposal:** a file in `roles/` whose name
   starts with `_` is a helper module, not a role. The framework puts
   `roles/` on the import path, so a role writes `from _signal_common import
   …` with no path trick. Section 3.2 says this in one sentence.

4. **"No base class" means no *framework* base class.** The four signal
   roles are built by one factory over shared code. Under 4.3 each becomes a
   one-class file, e.g. `class MacSignal(SignalComputer)` where
   `SignalComputer` lives in `_signal_common.py`. **Proposal:** 4.3 says "no
   DisSysLab base class or import"; inheriting from the office's own helper
   is allowed.

5. **Argument names.** `speed_name` becomes `variant`, the word the code and
   the report already use. Every backtester sends `type: "mac_backtest"`,
   whatever the family; it becomes `msg_type: "backtest"`.

6. **Silent fallbacks.** A backtester skips a ticker whose signal is missing
   or the wrong length; a signal computer skips a ticker with fewer than two
   prices. Under the standing habit ("a branch never taken is a branch never
   tested") these become failures with a message, not silent skips. The
   price source already reports missing files in an `errors` field; that
   stays, and the report shows it.

7. **The skill must be rewritten with the office.** `backtest-strategy-builder`
   edits `office.md` in the old form (`is a backtester(speed_name=…)`,
   extending JOIN's `inboxes=[…]`, `'s out are … and …`). In the new form an
   added strategy is: one signal line, one backtester line per variant, one
   fan-out line and one `-> JOIN.<variant>` line per variant; no inbox list
   to extend. The skill's text is also already out of date in five places
   (three strategies instead of four, wiring "from the source" instead of
   from MKT, cross-sectional ranking listed as unsupported, a deprecated
   `make_report.py`, nine variants instead of 11).

8. **Dead and stale files.** `draft_workers/` (839 lines), `window_gate.py`
   and `monte_carlo_gate.py` are not wired. `build/run.py` still passes a
   `directory` argument that `office.md` no longer has, and an `office.md`
   comment explains it. Header comments in two helpers still name
   `draft_workers/`. `_contract_checks.py` is a byte-identical copy of the
   skill's `check_no_lookahead.py`. These belong to the code clean-up, not
   the spec.

9. **Where the machinery lives.** The skill requires the shared files to stay
   unchanged ("zero diff") when a strategy is added. That makes them library
   code that happens to sit in an office's `roles/` folder. Whether they move
   to a package of their own is a question for the code clean-up.

10. **Size, for the record.** 26 connection sentences become 19 lines, and the
    11-name `inboxes=[…]` list disappears (inboxes come from connections).
    The office remains the largest example by far: about 3,700 lines of Python
    behind 40 lines of `office.md`, of which about 410 are strategy-specific.
