"""
dissyslab.office — the office compile pipeline.

Reads ``office.md`` plus role files; produces a runtime Network or
emits a ``build/run.py`` Python file. Most users do not import from
this subpackage; they use the ``dsl`` command-line tool
(``dsl build <office_dir>`` or ``dsl run <office_dir>``).

Pipeline stages (each implemented in its own module):

    1. parser            — office.md text → OfficeSpec
    2. office_spec       — OfficeSpec dataclass and related types
    3. library           — AgentRoleEntry / OfficeRoleEntry, named
                           role helpers (``nl_role``,
                           ``synchronizer_role``, ``specialist_role``),
                           and ``load_roles_dir``
    4. compiler          — OfficeSpec + Library → dissyslab.network.Network
    5. codegen           — emit <office>/build/run.py from a compiled
                           Network
    6. office_run_context — runtime environment injected into
                           ``nl_role`` system prompts

The runtime that executes the produced Network lives in
``dissyslab.network`` (``run_network()`` / ``process_network()``).
"""
from dissyslab.office.agent_spec import AgentSpec
from dissyslab.office.office_spec_constants import EXTERNAL
from dissyslab.office.office_spec import (
    ConnectionStmt,
    Endpoint,
    OfficeSpec,
    RoleRef,
    SinkSpec,
    SourceSpec,
)
from dissyslab.office.parser import IMPLICIT_INPORT, parse_office_dir
from dissyslab.office.parser_errors import ParseError
from dissyslab.office.library import (
    AgentRoleEntry,
    DEFAULT_AI,
    Library,
    OfficeRoleEntry,
    PARAMETERIZED_LIBRARY,
    RoleEntry,
    load_roles_dir,
    nl_role,
    specialist_role,
    synchronizer_role,
)
from dissyslab.office.compiler import (
    CompileError,
    CompileWarning,
    compile_office,
)
from dissyslab.office.codegen import (
    emit_run_py,
    render_run_py,
)
from dissyslab.office.make_office import make_office

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
    "PARAMETERIZED_LIBRARY",
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
    "specialist_role",
    "synchronizer_role",
]
