# dissyslab/gallery/apps/mac_speed_suite/roles/monte_carlo_gate.py

"""
MONTE_CARLO_GATE role -- a drop-in replacement for window_gate that feeds the
same loop a *resampled* bank instead of time slices. It releases a
full-history span (for the detailed report), then n_samples seeded
block-bootstrap resamples of the history. The comparator builds an outcome
distribution from the resampled spans; the pipeline and wiring are unchanged.

Monte Carlo answers a different question from walk-forward: not "does the edge
survive out-of-sample?" but "how much of this result is luck, and how fragile
is it?" -- a distribution of outcomes rather than one number.

To run a Monte Carlo pass instead of walk-forward, swap the gate in office.md::

    GATE is a monte_carlo_gate(n_samples=200).

Everything else (COMPARATOR, the pipeline, the sinks) stays the same.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _walkforward import _MonteCarloGate  # noqa: E402

from dissyslab.office.library import AgentRoleEntry

role = AgentRoleEntry(
    name="monte_carlo_gate",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda n_samples=200, seed=42, block_size=20: _MonteCarloGate(
        n_samples=n_samples, seed=seed, block_size=block_size
    ),
)
