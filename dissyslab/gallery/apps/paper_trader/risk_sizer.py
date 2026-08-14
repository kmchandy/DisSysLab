"""
risk_sizer.py -- SIZER: turn the strategy's per-ticker signals into target
*positions* (share counts), via a named, disclosed sizing policy. Pure Python,
cloud-testable.

Sizing is a pluggable policy from a small tested menu -- NOT freeform logic --
because it is inside the decision path and must be deterministic and identical to
the backtester's (backtest-live consistency). The user selects one by name in
`policy.sizing`; adding a genuinely new scheme means adding a tested policy here,
shared by both offices.

Menu:
  inverse_vol    (default) -- weight each active name by 1/volatility, normalized
                              (matches the backtester's portfolio construction)
  equal_weight             -- equal dollars per active name
  fixed_fraction           -- a fixed fraction of equity per active name
  risk_based               -- size so each position risks a fixed fraction of
                              equity at its stop (this is where R sizing lives);
                              opt-in, never the default

Signals: ticker -> desired exposure. Sign is direction (long/short); magnitude is
relative conviction for continuous strategies (|signal| ignored by equal/fixed/
risk sizing, used only to rank under a max-names cap). Inactive names (signal 0)
get target 0. Gross exposure is capped at equity by default (no leverage).
"""

from __future__ import annotations

from typing import Any, Dict

_EPS = 1e-12


def _sign(x: float) -> float:
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)


def _apply_max_names(active: Dict[str, float], max_names) -> Dict[str, float]:
    """Cap the number of held names. Rank by |signal| (conviction), tie-break by
    ticker for determinism. (For pure directional signals every |signal| ties, so
    this reduces to alphabetical -- a documented simplification; real selection
    would use conviction or momentum.)"""
    if not max_names or len(active) <= max_names:
        return active
    ranked = sorted(active, key=lambda t: (-abs(active[t]), t))
    return {t: active[t] for t in ranked[:max_names]}


# ── weighters: active names -> signed target notional ─────────────────

def _equal_weight(active, equity, prices, vols, policy):
    n = len(active)
    return {t: _sign(s) * equity / n for t, s in active.items()}


def _inverse_vol(active, equity, prices, vols, policy):
    inv = {t: 1.0 / vols[t] for t in active
           if isinstance(vols.get(t), (int, float)) and vols[t] > 0}
    if not inv:                                    # no vols -> equal weight fallback
        return _equal_weight(active, equity, prices, vols, policy)
    total = sum(inv.values())
    out = {}
    for t in active:
        w = inv.get(t, 0.0) / total                # zero-vol names excluded (w=0)
        out[t] = _sign(active[t]) * w * equity
    return out


def _fixed_fraction(active, equity, prices, vols, policy):
    frac = float(policy.get("fixed_fraction", 0.1))
    return {t: _sign(s) * frac * equity for t, s in active.items()}


def _risk_based(active, equity, prices, vols, policy):
    """Size each position to risk `risk_frac` of equity at its stop. With a
    percentage stop, risk/share = stop_pct * price, so target notional =
    (risk_frac * equity) / stop_pct -- equal risk per name. This is R sizing:
    each position risks one R."""
    risk_frac = float(policy.get("risk_frac", 0.01))
    stop_pct = float(policy.get("stop_pct", 0.10))
    per = (risk_frac * equity) / stop_pct if stop_pct > 0 else 0.0
    return {t: _sign(s) * per for t, s in active.items()}


_WEIGHTERS = {
    "inverse_vol": _inverse_vol,
    "equal_weight": _equal_weight,
    "fixed_fraction": _fixed_fraction,
    "risk_based": _risk_based,
}


def _cap_gross(notionals, equity, allow_leverage):
    """No leverage by default: scale everything down if gross exposure exceeds
    equity."""
    gross = sum(abs(v) for v in notionals.values())
    if not allow_leverage and equity > 0 and gross > equity + _EPS:
        scale = equity / gross
        return {t: v * scale for t, v in notionals.items()}
    return notionals


def target_positions(signals, equity, prices, vols, policy):
    """signals: {ticker: exposure}; equity: total account equity; prices,
    vols: {ticker: value}; policy: {sizing, ...}. Returns {ticker: target_shares}
    for every ticker in `signals` (inactive -> 0.0)."""
    sizing = policy.get("sizing", "inverse_vol")
    weighter = _WEIGHTERS.get(sizing)
    if weighter is None:
        raise ValueError(f"unknown sizing policy: {sizing!r} "
                         f"(known: {sorted(_WEIGHTERS)})")

    targets = {t: 0.0 for t in signals}
    if equity <= 0:
        return targets

    active = {t: float(s) for t, s in signals.items()
              if abs(float(s)) > _EPS and t in prices and prices[t] > 0}
    active = _apply_max_names(active, policy.get("max_names"))
    if not active:
        return targets

    notionals = _cap_gross(weighter(active, equity, prices, vols, policy),
                           equity, bool(policy.get("allow_leverage", False)))
    for t, notional in notionals.items():
        targets[t] = notional / prices[t]
    return targets
