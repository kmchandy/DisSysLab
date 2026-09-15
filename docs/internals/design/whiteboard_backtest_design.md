# A whiteboard office for strategy search — schema and verbs

Sketch, 2026-09-12. Maps a shared read-write whiteboard with agent
spawning onto the existing `mac_speed_suite` contract. Nothing here is
built; this is for deciding whether it fits before any kernel exists.

---

## Two things already in the code that decide the design

**1. The proposal/code boundary already exists.** `_signal_common.py`
splits every strategy family into three parts, and only one of them is
code:

| part | what it is | who may author it |
|---|---|---|
| `VARIANTS` | `name -> params` — a dict | **data**, so an agent may propose one |
| `compute_variant_signal(bars, params)` | the family's math | **code**, human-reviewed only |
| the shared wrapper | written once, reused | fixed |

So "an agent proposes a strategy" means "an agent writes a row of a
VARIANTS table" — a params tuple, never a function. That is exactly the
typed-request discipline a safe kernel needs, and it is already how the
office is organised. The line is clean: **agents extend families,
humans add families.** Adding a family stays what it is today, a
reviewed code contribution through `backtest-strategy-builder`.

**2. The reference monitor already exists.** `_contract_checks.py` runs
on each variant's first real message:

- `check_no_lookahead` — `signal[t]` depends only on `bars[0..t]`
- `check_deterministic` — same input twice, same output
- `check_finite` — no NaN, no inf
- `check_signal_range` — directional vs sizing, with declared bounds

These already refuse a bad variant before it can produce a ranking. The
whiteboard kernel does not invent a gatekeeper; it **promotes this one**
from a per-run assertion to a capability: a variant with no passing
`signal_check/*` fact cannot be backtested at all.

Note this matters even though families are fixed. A bad *parameter* —
a Donchian window of 0, a MAC pair with `fast_span > slow_span` — produces
a degenerate or non-finite signal from perfectly good code.

---

## Whiteboard schema

Every fact is write-once and carries `author`, `step`, and `cites` (the
keys its author had read). That last field is the dataflow graph.

| key | value | written by |
|---|---|---|
| `universe/<uid>` | `{tickers, filename_pattern, first_date, last_date}` | boot |
| `window/<wid>` | `{uid, start, end, role: train\|holdout}` | boot |
| `family/<fam>` | `{module, signal_type, signal_range}` | boot |
| `variant/<fam>/<name>` | `{family, params}` — one VARIANTS row | searcher |
| `signal_check/<fam>/<name>` | `{no_lookahead, deterministic, finite, in_range}` | CHECKER only |
| `result/<fam>/<name>/<wid>` | `{ann_return, ann_vol, sharpe, sortino, max_dd, calmar, n_trades}` | RUNNER only |
| `holdout/<fam>/<name>/<wid>` | same shape | REFEREE only, N total |
| `claim/<cid>` | `{variant, assertion, cites:[result keys]}` | searcher |

`result` mirrors what EVALUATOR already emits, so the whiteboard stores
what the office already computes rather than a parallel vocabulary.
Variant names stay family-prefixed (`mac_fast`, `donchian_20`) exactly
as they are now, so nothing collides.

---

## Verb table

Seven verbs. This is the complete list of things an agent can do.

| verb | args | who | the kernel checks |
|---|---|---|---|
| `read` | pattern | all | pattern within the agent's read capability |
| `propose` | fam, name, params | searcher | family exists; name unused; params match the family's schema; writes `variant/*` |
| `check` | variant | CHECKER | runs `_contract_checks` with those params; writes `signal_check/*` |
| `backtest` | variant, wid | searcher | `window.role == train`; a passing `signal_check` exists; charges budget; kernel runs signal → backtester → evaluator; writes `result/*` |
| `spawn` | role, budget, caps, region | searcher | `budget <= parent's remaining`; `caps ⊆ parent's caps`; splits, never copies |
| `claim` | variant, text, cites | searcher | every cited key exists |
| `adjudicate` | variant | REFEREE | consumes one of N holdout looks; writes `holdout/*` |

There is no verb that reaches a broker, a network, or a filesystem. The
price data is reachable only inside `backtest`, which the kernel
executes. **Absent, not gated.**

---

## Invariants

Each is inductive — true at boot, preserved by one step, provable
without reasoning about interleavings.

| | invariant | buys |
|---|---|---|
| I1 | `Σ(live budgets) + spent ≤ initial` | termination by construction, *and* a bound on the number of strategies tried |
| I2 | `⋃(live capabilities) ⊆ root capabilities` | a population of any size can do nothing the root could not |
| I3 | `count(holdout/*) ≤ N` | the out-of-sample window is looked at N times, however many agents exist |
| I4 | every key written at most once | a read attributes to exactly one write |
| I5 | every `result` cites a `variant` and a `window`; every `claim` cites existing keys | provenance is total |

I3 is the one doing statistical work. REFEREE holds the only capability
to read a `role=holdout` window and cannot spawn, so **no amount of
population growth buys more out-of-sample looks**. That is the capability
lattice enforcing a statistical discipline, not a metaphor for one.

I1 doubles as a multiple-comparisons budget: the same number that
guarantees the run ends also bounds how many hypotheses were tested,
which is what a family-wise correction needs.

---

## What the dataflow graph is for here

I4 and I5 mean the kernel builds the lecture-3 graph live. Its shape
answers the question the statistics actually need:

> How many *independent* strategies did we try?

A `variant` whose author had read no prior `result` is an independent
proposal. A `variant` proposed after reading three results is not — it
is a child of them, and counting it as a fresh trial overstates the
evidence. Walking the graph gives the effective number of independent
trials, which is the denominator for any honest claim about the winner.

---

## What this replaces

`office.md` today wires eleven backtesters by hand, each with its own
`JOIN` inbox, and adding a variant means editing the file. The
whiteboard office has **no Connections section and no fixed population**:
searchers appear and split budget, and the JOIN disappears because
results accumulate on the board instead of being synchronised.

That is the whole trade. The static graph is what makes today's office
easy to reason about; the whiteboard gives that up and buys it back with
the invariants above.

---

## Open questions

1. **Cost.** Budget must be denominated in something that includes LLM
   tokens, not just backtest count, or the bound is not a real bound.
2. **Does `validation_gate` move onto the board, or stay inside
   `backtest`?** Walk-forward and Monte Carlo already exist
   (`n_folds=4, n_samples=100, block_size=20`). Simplest is to leave
   them inside the tool so every `result` is already validated, and keep
   `holdout` for a final, separate, N-look window.
3. **Who writes `claim`, and does anyone read it?** A claim is the one
   free-text field. It is where an LLM can be confidently wrong without
   violating any invariant — the mechanism/content boundary, made
   concrete and visible in one key.
4. **Does REFEREE decide, or report?** If REFEREE ranks, it becomes the
   scorer the swarm will try to reverse-engineer. Safer if it only
   records, and a human ranks.
