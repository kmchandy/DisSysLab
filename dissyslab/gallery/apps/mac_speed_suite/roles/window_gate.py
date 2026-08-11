# dissyslab/gallery/apps/mac_speed_suite/roles/window_gate.py

"""
WINDOW_GATE role -- the walk-forward gate. Holds the full history and a
schedule of labelled spans, and releases one span at a time into the pipeline
on each inbound signal (the source's full history first, then the comparator's
"next" signals). See _walkforward.py for the logic and the debate office for
the pattern.

office.md::

    GATE is a window_gate(n_folds=4).
    csv_stock_history's out is GATE.
    GATE's out is MKT.
    COMPARATOR's next is GATE.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _walkforward import WALKFORWARD_DEFAULT_FOLDS, _WindowGate  # noqa: E402

from dissyslab.office.library import AgentRoleEntry

role = AgentRoleEntry(
    name="window_gate",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda n_folds=WALKFORWARD_DEFAULT_FOLDS: _WindowGate(n_folds=n_folds),
)
