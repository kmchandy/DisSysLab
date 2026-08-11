# dissyslab/gallery/apps/mac_speed_suite/roles/comparator.py

"""
COMPARATOR role -- the walk-forward comparator. Accumulates each span's
evaluation, signals the gate to release the next span, and once the whole
schedule is done emits the out-of-sample scorecard (plus the full-window
evaluation, so the detailed report still renders) to the report. See
_walkforward.py for the logic; the debate moderator (continue/finish) is the
pattern.

Two outports: "out" (semantic) -> the report and console; "next" -> the gate.

office.md::

    COMPARATOR is a comparator.
    EVAL's out is COMPARATOR.
    COMPARATOR's next is GATE.
    COMPARATOR's out are console_printer and report_html.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _walkforward import _Comparator  # noqa: E402

from dissyslab.office.library import AgentRoleEntry

role = AgentRoleEntry(
    name="comparator",
    in_ports=("in_",),
    out_ports=("out", "next"),
    factory=_Comparator,
)
