# dissyslab/gallery/apps/mac_speed_suite/roles/backtester.py

"""
Parameterized backtester role -- one role file for all five MAC speeds.

Confirmed by reading the DisSysLab compiler directly
(dissyslab/office/compiler.py, the role-resolution path around
_construct_or_pat_error / AgentRoleEntry.__call__): a *static* role's
factory can already accept office.md kwargs. AgentRoleEntry.__call__
forwards keyword arguments straight to whatever signature `factory`
has -- it isn't limited to nl_role's `AI=` override, that's just the
one case exercised elsewhere in the codebase today.

PARAMETERIZED_LIBRARY (synchronizer/router/select/gate/record) is a
separate, heavier mechanism, needed only when a role's *port shape*
(not just its behavior) depends on the parameter -- e.g. synchronizer's
inport names come from `inports=[...]`. This role's shape never varies
(always in_ -> out), only its behavior does, so the plain kwarg-forwarding
factory below is the right fit -- no PARAMETERIZED_LIBRARY involvement
needed.

Usage in office.md:
    BT_FAST is a backtester(speed_name='fast').
    BT_MED_FAST is a backtester(speed_name='med_fast').
    BT_MED is a backtester(speed_name='med').
    BT_MED_SLOW is a backtester(speed_name='med_slow').
    BT_SLOW is a backtester(speed_name='slow').

Replaces the five previous thin wrapper files (backtester_fast.py ...
backtester_slow.py), which existed only because of an earlier, overly
cautious assumption that static roles couldn't take arbitrary kwargs.
_backtester_core.py (the actual make_backtester() logic) is unchanged.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _backtester_core import make_backtester  # noqa: E402

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

role = AgentRoleEntry(
    name="backtester",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda speed_name: Role(
        fn=make_backtester(speed_name), statuses=["out"]
    ),
)
