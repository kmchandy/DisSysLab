# dissyslab/gallery/apps/mac_speed_suite/roles/validation_gate.py

"""
VALIDATION_GATE role -- the default gate. It runs BOTH validations in one
office pass: the walk-forward schedule (a full-history span plus expanding
train/test folds), then n_samples Monte Carlo resamples. The unchanged
COMPARATOR builds the out-of-sample scorecard from the train/test spans and the
robustness distribution from the resamples, so one `dsl run` yields a report
with both sections -- and no office.md editing.

The Monte Carlo sample count is modest by default so a full run stays quick.
Everything is adjustable from office.md (or by asking Cowork in plain English)::

    GATE is a validation_gate(n_samples=100).        # the default: both
    GATE is a validation_gate(n_samples=500).        # tighter distribution
    GATE is a validation_gate(monte_carlo=False).    # walk-forward only (fast)
    GATE is a validation_gate(walk_forward=False).   # Monte Carlo only

window_gate and monte_carlo_gate remain available for a single-purpose run.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _walkforward import _ValidationGate  # noqa: E402

from dissyslab.office.library import AgentRoleEntry

role = AgentRoleEntry(
    name="validation_gate",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda n_folds=4, n_samples=100, seed=42, block_size=20,
    walk_forward=True, monte_carlo=True, stop_pct=0.10: _ValidationGate(
        n_folds=n_folds, n_samples=n_samples, seed=seed, block_size=block_size,
        walk_forward=walk_forward, monte_carlo=monte_carlo, stop_pct=stop_pct,
    ),
)
