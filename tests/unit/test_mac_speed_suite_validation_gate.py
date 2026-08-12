# tests/unit/test_mac_speed_suite_validation_gate.py
"""
Regression tests for the unified VALIDATION_GATE (default gate): one office
pass that runs walk-forward *and* Monte Carlo, so the report shows both
sections with no office.md editing. These lock in the plan/step logic; the
live threaded loop is exercised by `dsl run`.
"""

from __future__ import annotations

from dissyslab.gallery.apps.mac_speed_suite.roles._walkforward import (
    _Comparator,
    _ValidationGate,
)


def _full(dates):
    hist = {"A": [{"date": d, "open": 1, "high": 1, "low": 1,
                   "close": 1 + i, "volume": 0} for i, d in enumerate(dates)]}
    return {"type": "stock_history", "tickers": ["A"], "history": hist}


def _drain(gate):
    """Roles emitted, in order, driving the gate as the office would."""
    dates = [f"2020-{(i // 20) + 1:02d}-{(i % 20) + 1:02d}" for i in range(60)]
    roles = []
    span = gate.next_span(_full(dates))
    while span is not None:
        roles.append(span["_wf_tag"]["role"])
        span = gate.next_span({"walkforward_next": True})
    return roles, dates


def test_default_gate_runs_walk_forward_then_monte_carlo():
    gate = _ValidationGate(n_folds=2, n_samples=3)
    roles, _ = _drain(gate)
    # one full, then 2 folds (train/test each), then 3 mc resamples
    assert roles[0] == "full"
    assert roles.count("train") == 2 and roles.count("test") == 2
    assert roles.count("mc") == 3
    # walk-forward comes entirely before Monte Carlo
    assert roles.index("mc") > max(roles.index("test"), roles.index("train"))


def test_total_spans_is_constant_and_matches_plan_length():
    gate = _ValidationGate(n_folds=2, n_samples=3)
    dates = [f"2020-{(i // 20) + 1:02d}-{(i % 20) + 1:02d}" for i in range(60)]
    span = gate.next_span(_full(dates))
    total = span["_wf_tag"]["total_spans"]
    seen = 1
    while True:
        span = gate.next_span({"walkforward_next": True})
        if span is None:
            break
        assert span["_wf_tag"]["total_spans"] == total  # never drifts
        seen += 1
    assert seen == total  # 1 full + 2*2 folds + 3 mc = 8


def test_monte_carlo_only_still_emits_one_full_span_for_the_report():
    gate = _ValidationGate(n_samples=3, walk_forward=False)
    roles, _ = _drain(gate)
    assert roles[0] == "full"
    assert "train" not in roles and "test" not in roles
    assert roles.count("mc") == 3


def test_walk_forward_only_runs_no_resamples():
    gate = _ValidationGate(n_folds=2, monte_carlo=False)
    roles, _ = _drain(gate)
    assert "mc" not in roles
    assert roles[0] == "full" and roles.count("test") == 2


def test_comparator_builds_both_sections_from_one_pass():
    """Drive the real comparator with the gate's tags and confirm the final
    scorecard carries BOTH a walk_forward and a monte_carlo section."""
    gate = _ValidationGate(n_folds=2, n_samples=3)
    dates = [f"2020-{(i // 20) + 1:02d}-{(i % 20) + 1:02d}" for i in range(60)]
    comp = _Comparator()

    def ev(tag):
        return {"_wf_tag": tag,
                "portfolio_stats": {"x": {"sharpe_ratio": 1.0,
                                          "annualized_return": 0.1,
                                          "max_drawdown": -0.2}},
                "table": {"A": {}}, "correlation": {}}

    span = gate.next_span(_full(dates))
    result = None
    while span is not None:
        kind, out = comp.accept(ev(span["_wf_tag"]))
        if kind == "scorecard":
            result = out
        span = gate.next_span({"walkforward_next": True})

    assert result is not None
    assert "walk_forward" in result and "monte_carlo" in result
    assert result["monte_carlo"]["n_samples"] == 3
    # the detailed full-window fields survive so report.html still renders
    assert "table" in result and "correlation" in result


# ── run-settings receipt (step 1: conversational params + provenance) ──


def test_full_span_carries_a_run_config_receipt():
    gate = _ValidationGate(n_folds=3, n_samples=4)
    dates = [f"2016-{(i % 12) + 1:02d}-{(i // 12) + 1:02d}" for i in range(48)]
    full_span = gate.next_span(_full(dates))
    rc = full_span["_wf_tag"].get("run_config")
    assert rc is not None
    assert rc["n_folds"] == 3 and rc["n_samples"] == 4
    assert rc["start"] == dates[0] and rc["end"] == dates[-1]
    assert rc["n_bars"] == 48
    assert rc["walk_forward"] and rc["monte_carlo"]
    # the receipt rides only on the full span, not every later span
    nxt = gate.next_span({"walkforward_next": True})
    assert "run_config" not in nxt["_wf_tag"]


def test_comparator_surfaces_run_settings_with_cost():
    gate = _ValidationGate(n_folds=2, n_samples=3)
    dates = [f"2016-{(i % 12) + 1:02d}-{(i // 12) + 1:02d}" for i in range(40)]
    comp = _Comparator()

    def ev(tag):
        return {"_wf_tag": tag, "n_days": len(dates), "cost_bps": 7.5,
                "portfolio_stats": {"x": {"sharpe_ratio": 1.0,
                                          "annualized_return": 0.1,
                                          "max_drawdown": -0.2}},
                "table": {"A": {}}, "correlation": {}}

    span = gate.next_span(_full(dates))
    result = None
    while span is not None:
        kind, out = comp.accept(ev(span["_wf_tag"]))
        if kind == "scorecard":
            result = out
        span = gate.next_span({"walkforward_next": True})

    rs = result.get("run_settings")
    assert rs is not None
    assert rs["cost_bps"] == 7.5
    assert rs["n_folds"] == 2 and rs["n_samples"] == 3
    assert rs["tickers"] == ["A"]
