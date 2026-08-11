# tests/unit/test_mac_speed_suite_walkforward.py
"""
Regression tests for walk-forward out-of-sample validation (Phase 1, D3).

Walk-forward runs as an in-office feedback loop: a WINDOW_GATE releases one
labelled span at a time (a full-history span for the detailed report, then
expanding train/test spans per fold) into the unchanged pipeline, and a
COMPARATOR accumulates each span's evaluation, loops the gate until the
schedule is done, then emits the out-of-sample scorecard.

These lock in the pure schedule/slice/aggregate logic and the gate/comparator
step methods (the live threaded loop itself is exercised by `dsl run`).
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._walkforward import (
    _Comparator,
    _WindowGate,
    aggregate_scorecard,
    build_schedule,
    slice_history,
)


def _hist(dates):
    return {"A": [{"date": d, "open": 1, "high": 1, "low": 1, "close": 1 + i, "volume": 0}
                  for i, d in enumerate(dates)]}


# ── schedule ──────────────────────────────────────────────────────────


def test_schedule_is_full_then_expanding_train_test_folds():
    dates = [f"d{i:02d}" for i in range(9)]
    spans = build_schedule(_hist(dates), n_folds=2)
    roles = [r for (_f, r, _s, _e) in spans]
    assert roles == ["full", "train", "test", "train", "test"]
    # every train span starts at the very first date (expanding window)...
    assert spans[1][2] == dates[0] and spans[3][2] == dates[0]
    # ...and the later fold trains on more (its train_end is later)
    assert spans[3][3] > spans[1][3]
    # test windows do not overlap and come after their train
    assert spans[2][2] > spans[1][3] and spans[4][2] > spans[3][3]


def test_schedule_degrades_to_just_full_when_too_little_data():
    spans = build_schedule(_hist(["d0", "d1"]), n_folds=4)
    assert [r for (_f, r, _s, _e) in spans] == ["full"]


# ── slicing ───────────────────────────────────────────────────────────


def test_slice_history_is_inclusive_by_date():
    full = {"type": "stock_history", "tickers": ["A"],
            "history": {"A": [{"date": f"2020-01-0{i}", "close": i} for i in range(1, 6)]}}
    out = slice_history(full, "2020-01-02", "2020-01-04")
    assert [b["date"] for b in out["history"]["A"]] == ["2020-01-02", "2020-01-03", "2020-01-04"]
    assert out["start"] == "2020-01-02" and out["end"] == "2020-01-04"


# ── scorecard aggregation ─────────────────────────────────────────────


def test_scorecard_ranks_by_out_of_sample_not_in_sample():
    """x is the best in-sample but collapses out-of-sample; y is steadier.
    The honest ranking (by OOS Sharpe) must put y first."""
    train = [{"portfolio_stats": {
        "x": {"sharpe_ratio": 2.0, "annualized_return": 0.30},
        "y": {"sharpe_ratio": 1.0, "annualized_return": 0.10}}}]
    test = [{"portfolio_stats": {
        "x": {"sharpe_ratio": 0.2, "annualized_return": 0.02},
        "y": {"sharpe_ratio": 0.9, "annualized_return": 0.09}}}]
    sc = aggregate_scorecard(train, test)
    assert sc["ranked_by_oos"][0] == "y"
    assert abs(sc["per_variant"]["x"]["is_sharpe"] - 2.0) < 1e-9
    assert abs(sc["per_variant"]["x"]["oos_sharpe"] - 0.2) < 1e-9
    assert sc["n_folds"] == 1


# ── gate step logic ───────────────────────────────────────────────────


def test_gate_emits_full_then_folds_then_nothing_when_exhausted():
    dates = [f"d{i:02d}" for i in range(9)]
    full = {"type": "stock_history", "tickers": ["A"], "history": _hist(dates)}
    gate = _WindowGate(n_folds=2)
    first = gate.next_span(full)
    assert first["_wf_tag"]["role"] == "full"
    assert first["_wf_tag"]["total_spans"] == 5     # 1 full + 2*2 folds
    seq = [first["_wf_tag"]["role"]]
    for _ in range(4):
        seq.append(gate.next_span({"walkforward_next": True})["_wf_tag"]["role"])
    assert seq == ["full", "train", "test", "train", "test"]
    # exhausted -> returns None (and run() just keeps looping, so the office
    # can terminate cleanly)
    assert gate.next_span({"walkforward_next": True}) is None


# ── comparator step logic ─────────────────────────────────────────────


def test_comparator_loops_until_schedule_done_then_scorecards():
    comp = _Comparator()

    def ev(role):
        return {"_wf_tag": {"role": role, "total_spans": 3},
                "portfolio_stats": {"x": {"sharpe_ratio": 1.0, "annualized_return": 0.1}},
                "table": {"A": {}}, "correlation": {}}

    assert comp.accept(ev("full"))[0] == "next"
    assert comp.accept(ev("train"))[0] == "next"
    kind, out = comp.accept(ev("test"))          # 3rd of 3 -> done
    assert kind == "scorecard"
    assert out["walk_forward"]["ranked_by_oos"] == ["x"]
    # the scorecard also carries the full-window fields so the detailed report
    # still renders
    assert "table" in out and "correlation" in out
