"""
dissyslab.office_v2 — refactored office compiler (work in progress).

Built piece by piece on the refactor/compiler-v2 branch alongside the
existing dissyslab.office package. Replaces dissyslab.office at cutover.

Layers, built in order:
    1. (retired) Edge          — runtime uses 4-tuples; no v2 type
    2. (retired) Network spec  — runtime Network is the spec
    3. AgentSpec               — name, in_ports, out_ports             (done)
    4. OfficeSpec + parser     — agents are uniform RoleRefs; parser
                                 reads only office.md (no roles/*.md) (done)
    4b. Role library           — AgentRoleEntry / OfficeRoleEntry,
                                 nl_role, load_roles_dir               (done)
    5. Compiler                — OfficeSpec + Library ->
                                 dissyslab.network.Network             (done)
    6. Codegen                 — emit <office>/build/run.py from a
                                 compiled tree                         (done)
    6. (Runner is unchanged — see dissyslab.network)
    7. AgentImpl factory       — RoleEntry -> runtime Agent            (todo)

First-year students normally do not import from this subpackage
directly; they run the CLI (`dsl build <office_dir>` or
`dsl run <office_dir>`).
"""
from dissyslab.office_v2.agent_spec import AgentSpec
from dissyslab.office_v2.office_spec_constants import EXTERNAL
from dissyslab.office_v2.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office_v2.parser import IMPLICIT_INPORT, parse_office_dir
from dissyslab.office_v2.parser_errors import ParseError
from dissyslab.office_v2.library import (
    AgentRoleEntry,
    DEFAULT_AI,
    Library,
    OfficeRoleEntry,
    RoleEntry,
    load_roles_dir,
    nl_role,
)
from dissyslab.office_v2.compiler import (
    CompileError,
    CompileWarning,
    compile_office,
)
from dissyslab.office_v2.codegen import (
    emit_run_py,
    render_run_py,
)
from dissyslab.office_v2.make_office import make_office

__all__ = [
    "AgentRoleEntry",
    "AgentSpec",
    "CompileError",
    "CompileWarning",
    "ConnectionStmt",
    "DEFAULT_AI",
    "Endpoint",
    "EXTERNAL",
    "IMPLICIT_INPORT",
    "Library",
    "OfficeRoleEntry",
    "OfficeSpec",
    "ParseError",
    "RoleEntry",
    "RoleRef",
    "SinkSpec",
    "SourceSpec",
    "compile_office",
    "emit_run_py",
    "load_roles_dir",
    "make_office",
    "nl_role",
    "parse_office_dir",
    "render_run_py",
]
