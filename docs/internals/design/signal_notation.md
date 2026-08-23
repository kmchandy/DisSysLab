# A notation for specifying trading signals

A tutorial. The notation is a small set of operators, borrowed from
Kakushadze's *101 Formulaic Alphas* (2015) and the practice it
describes, in which a signal is written as an expression over price
series rather than as code.

The reason to have it: a formula is reviewable by someone who
understands trading and cannot read Python, and it is precise enough to
generate code from and to test code against. It sits between the paper
and the implementation, and it is the artifact a domain expert can
check.

Status: living. Written 2026-08-21 to specify the four strategies in
`gallery/apps/mac_speed_suite/roles/`.

---

## 1. The data model

A **series** is one value per bar for one instrument: `C` (close), `H`
(high), `L` (low), `V` (volume). Write `C_t` for its value at bar `t`,
with `t = 0` the first bar.

Operators come in two families, and the name tells you which:

- **Time-series operators** look down the time axis for one
  instrument. They are prefixed `ts_`, and each names its window.
- **Cross-sectional operators** look across instruments at one fixed
  bar. `rank` is the one that matters here.

Keeping the two visibly distinct is most of the value of the naming
convention. "The 20-day high" and "the highest of today's stocks" are
different operations and a notation that spells them the same way will
eventually let you write one when you meant the other.

---

## 2. The window convention, which is the whole game

> **`ts_f(x, N)` at bar `t` reads the `N` values
> `x_{t−N+1}, …, x_t` — the last `N` bars, including today.**

That is the only convention you must memorise. Everything else follows
from it, and every off-by-one bug in this domain is a disagreement
about it.

The complementary operator is `delay`:

> **`delay(x, d)` at bar `t` is `x_{t−d}`.**

Together they give exact control. To speak of "the highest high of the
**prior** `N` days, not counting today", you shift first:

```
ts_max(delay(H, 1), N)      at t:  max{ H_{t−N}, …, H_{t−1} }
```

**A useful identity.** `delay` commutes with any `ts_` operator:

```
ts_max(delay(H, 1), N)  ≡  delay(ts_max(H, N), 1)
```

Both name `max{H_{t−N}, …, H_{t−1}}`. Take a moment with that, because
it is the difference between a signal that uses today's high to decide
today's trade and one that does not. Written this way the look-ahead
question becomes **visible in the expression** rather than something a
test has to discover by experiment.

---

## 3. The operators

Definitions, with `x` a series and `N` a window in bars.

### Time-series

| Operator | At bar `t` | Notes |
|---|---|---|
| `delay(x, d)` | `x_{t−d}` | Undefined for `t < d`. |
| `delta(x, d)` | `x_t − x_{t−d}` | Equals `x − delay(x, d)`. The `d`-bar change. |
| `ts_sum(x, N)` | `Σ_{i=0}^{N−1} x_{t−i}` | |
| `ts_mean(x, N)` | `ts_sum(x, N) / N` | The simple moving average. |
| `ts_max(x, N)` | `max{x_{t−N+1}, …, x_t}` | |
| `ts_min(x, N)` | `min{x_{t−N+1}, …, x_t}` | |
| `ts_argmax(x, N)` | bars since the window's maximum | `0` if today is the max. |
| `stddev(x, N)` | standard deviation over the same `N` values | **See the warning below.** |
| `correlation(x, y, N)` | Pearson correlation of the last `N` pairs | In `[−1, 1]`. |

### Cross-sectional

| Operator | At bar `t` | Notes |
|---|---|---|
| `rank(x)` | rank of `x_t` among all instruments at `t`, scaled to `(0, 1]` | This is what a "relative strength percentile" is. |

`rs_trend.py`'s `pct` from `MARKET_CONTEXT` is exactly `rank` applied
to a momentum series. Writing it that way makes visible that the
strategy needs peers, which the Python does not.

### The `stddev` warning

`stddev` has two definitions that differ by whether you divide by `N`
or `N−1`. They are not close for small windows. On the three values
`{11, 12, 13}`:

- dividing by `N`: `√(2/3) = 0.8165`
- dividing by `N−1`: `√(2/2) = 1.0000`

A 22% difference, and the two ecosystems disagree by default — NumPy
divides by `N`, pandas by `N−1`. **Pin it in the specification**, every
time. A z-score or a Bollinger band built on the wrong one is wrong by
a fifth and looks entirely plausible.

---

## 4. Warmup

For `t < N − 1` the window is not full. Three conventions are in use
and you must choose one and write it down:

1. **Undefined** — the series begins at `t = N − 1`. Honest, and forces
   the caller to handle it.
2. **Partial window** — compute over however many bars exist.
   Convenient, and quietly changes the statistic's meaning early on.
3. **Seeded** — start from a fixed value and let a recurrence converge.

The suite currently uses all three. `donchian_signal.py` is (1) in
effect, emitting `0` until the window fills. `_atr_series` in
`turtle_signal.py` is explicitly (2) — a simple mean during warmup.
`_ewma` in `mac_signal.py` is (3), seeded with the first price.

None of these is wrong. Having three unstated ones is.

---

## 5. Composition, and the idioms worth knowing

```
simple moving average       ts_mean(C, N)
N-bar return                delta(C, N) / delay(C, N)
z-score                     (C − ts_mean(C, N)) / stddev(C, N)
Bollinger upper             ts_mean(C, N) + k · stddev(C, N)
prior-N-day channel high    ts_max(delay(H, 1), N)
true range                  max(H − L, |H − delay(C,1)|, |L − delay(C,1)|)
momentum rank vs peers      rank(delta(C, N))
```

**The causality rule.** An expression is causal at `t` if every
operator in it reads only indices `≤ t`. All the operators above are
causal by construction — none can reach forward. So a causal
*expression* is one built only from these. What remains is a separate
question: whether the signal is *tradeable*, which requires that it be
known before the bar it trades on. If the signal is computed from
`C_t` and the trade fills at `C_t`, the expression is causal and the
backtest is still fiction. The convention is to trade `delay(S, 1)`,
and to say so.

---

## 6. Worked example: Donchian(3)

Eight bars.

| t | H | L | C |
|---|---|---|---|
| 0 | 10 | 9 | 10 |
| 1 | 11 | 10 | 11 |
| 2 | 12 | 11 | 12 |
| 3 | 13 | 12 | 13 |
| 4 | 12 | 11 | 11 |
| 5 | 11 | 10 | 10 |
| 6 | 12 | 11 | 12 |
| 7 | 14 | 13 | 14 |

The rule:

```
U_t = ts_max(delay(H, 1), 3)
D_t = ts_min(delay(L, 1), 3)

S_t = +1        if C_t > U_t
      −1        if C_t < D_t
      S_{t−1}   otherwise
S_t =  0        for t < 3, and until the first breakout
```

Evaluating:

| t | U | D | C | test | S |
|---|---|---|---|---|---|
| 0–2 | — | — | | window not full | 0 |
| 3 | max{10,11,12} = 12 | min{9,10,11} = 9 | 13 | 13 > 12 | **+1** |
| 4 | max{11,12,13} = 13 | min{10,11,12} = 10 | 11 | neither | +1 |
| 5 | max{12,13,12} = 13 | min{11,12,11} = 11 | 10 | 10 < 11 | **−1** |
| 6 | max{13,12,11} = 13 | min{12,11,10} = 10 | 12 | neither | −1 |
| 7 | max{12,11,12} = 12 | min{11,10,11} = 10 | 14 | 14 > 12 | **+1** |

Signal: `0, 0, 0, +1, +1, −1, −1, +1`.

Eight bars, every intermediate value written down. This is the worked
example that belongs beside every strategy: it removes the remaining
ambiguity about indices at almost no cost, and it is the first
regression test.

---

## 7. Where the notation runs out

**Recurrences.** Donchian's *"otherwise hold"* makes `S_t` depend on
`S_{t−1}`, so it is not an expression over price alone. Neither is an
EMA. The notation must therefore admit an explicit recurrence, written
with its seed:

```
E[0] = C_0
E[t] = α·C_t + (1−α)·E[t−1],   α = 2/(n+1)
```

A one-line alpha expression cannot say this, which is why the pure
formulaic-alpha style is not sufficient on its own. Expressions where
they suffice; recurrences, with seeds stated, where they do not.

**Path-dependent position state.** Turtle's pyramiding, stops and unit
count are a small state machine, not a formula. Specify it as one —
states, transitions, guards — rather than pretending it is an
expression.

**Anything fitted.** A parameter chosen by optimisation has no closed
form. The formula covers the signal given the parameter; how the
parameter was chosen is a separate specification, and the place
look-ahead most often re-enters.

---

## 8. Why this is worth the trouble

Three claims, in order of how much they matter.

**A formula is checkable by the person who cares.** A trader can read
`ts_max(delay(H,1), 20)` and say whether it is the rule in the paper.
They cannot do that with forty lines of NumPy. This is the same move
as `office.md`: a small readable artifact standing in for machinery
nobody wants to inspect.

**Causality becomes syntactic.** `check_no_lookahead` establishes by
experiment what `delay` states in the expression.

**Two implementations can be checked against each other.** Generate a
naive loop and a vectorised version from one formula, and require them
to agree across the synthetic suite. Disagreement localises a bug with
no oracle at all — and language models write the naive version far
more reliably than the fast one.

---

## 9. Exercises

1. Show that `delta(x, d) ≡ x − delay(x, d)`, and that
   `ts_mean(delta(C,1), N) ≡ delta(C, N)/N`.
2. Write the MAC crossover of `mac_signal.py` in this notation,
   including its seed. What is `S_0` on every dataset, and why?
3. On a constant price series, evaluate Donchian(N). Then evaluate MAC.
   The two answers are different, and one of them is a specification
   decision nobody made on purpose.
4. Write RS-trend using `rank`. What does the expression require that
   a single-instrument test cannot supply?
5. For `p_t = a + bt`, show `ts_mean(C, N)_t = p_{t−(N−1)/2}`. What
   does an off-by-one in `N` do to that lag, and how would you detect
   it from the output alone?

---

See also: `readers_and_surfaces.md` for the same argument about
`office.md`, and `gallery/apps/paper_trader/strategy_selfcheck.py` for
the checks this notation is intended to strengthen.
