"""Tests for the brief renderer. Pure. python3 -m pytest test_brief.py -q"""

from __future__ import annotations

from brief import render_html, render_text

BRIEF = {
    "trade_date": "2026-08-16", "committed": True, "healed": False,
    "holdings": {"AMD": {"shares": 70, "avg_cost": 143.0, "price": 150.0}},
    "skipped": [{"ticker": "XYZ", "reason": "no open price"}],
    "decisions": {
        "AMD": {"signal": 1, "order": {"side": "buy", "qty": 70},
                "reason": "entry"},
        "NVDA": {"signal": 1, "order": None, "reason": "hold (within no-trade band)"},
    },
    "equity": {"cash": 89980.0, "positions_value": 10500.0, "total": 100480.0,
               "cum_pnl": 480.0},
}


def test_text_has_date_equity_holdings_and_actions():
    t = render_text(BRIEF)
    assert "2026-08-16" in t and "$100,480" in t
    assert "AMD 70" in t
    assert "BUY 70 AMD" in t
    assert "XYZ" in t                       # skipped surfaced


def test_text_for_a_no_action_day():
    t = render_text({"trade_date": "2026-08-17", "committed": False,
                     "reason": "already committed"})
    assert "no action" in t and "2026-08-17" in t


def test_html_is_wellformed_and_contains_sections():
    h = render_html(BRIEF)
    assert h.startswith("<!DOCTYPE html>") and "Holdings" in h and "Today's decisions" in h
    assert "AMD" in h and "paper" in h.lower()


def test_html_handles_flat_book():
    h = render_html({"trade_date": "d", "committed": True, "holdings": {},
                     "decisions": {}, "equity": {"total": 100000.0}})
    assert "flat / all cash" in h
