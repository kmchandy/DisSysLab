"""
dissyslab.office_v2 — refactored office compiler (work in progress).

Built piece by piece on the refactor/compiler-v2 branch alongside the
existing dissyslab.office package. Replaces dissyslab.office at cutover.

Layers, built in order:
    1. Edge          — on-wire connection type                   (done)
    2. Network       — list of Edges + cross-edge validation     (done)
    3. AgentSpec     — agent shape: name, in_ports, out_ports,
                       optional body (for sub-offices)            (done)
    4. OfficeSpec    — agents + connection statements            (todo)
    5. Compiler      — OfficeSpec -> Network (pure function)     (todo)
    6. (Runner is unchanged — see dissyslab.network)
    7. AgentImpl factory — AgentSpec + Backend -> callable       (todo)

First-year students normally do not import from this subpackage
directly; they run the CLI (`dsl build <office_dir>` or
`dsl run <office_dir>`).
"""
from dissyslab.office_v2.agent_spec import AgentSpec
from dissyslab.office_v2.edge import Edge
from dissyslab.office_v2.network import EXTERNAL, Network

__all__ = ["AgentSpec", "Edge", "EXTERNAL", "Network"]
