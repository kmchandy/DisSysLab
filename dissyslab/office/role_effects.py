"""What a role's own Python reaches for, read from its imports.

This is a **lint, and it is here to teach rather than to protect.**

An office's declared power is its `Sources:` and `Sinks:` lines — four
lines you can read before anything runs. That is true of the office.
It is not true of the Python inside a role, which can open a socket or
run a command without going near a sink, and no reachability check on
the graph will ever see it.

That exposure is not this project's. Any student running any
assistant-written Python has it, and building a sandbox to solve one
instance of a general problem would be overreach. What *is* this
project's is the claim: a plain script promises nothing, while an
office says its power is its sinks. So this check exists to keep that
sentence honest, and to put the general lesson in front of a student
at the one moment it is concrete — when they have just been handed
code they did not write.

**What it can and cannot do.** It parses imports and a few call names.
It cannot see what the code does, it cannot follow an alias, and a
role that wants to hide its reach can. Anyone who describes its
silence as a guarantee has misread it, and this docstring is where
that is written down.

The lists are deliberately narrow. Nothing in the fifty-one Python
roles the gallery ships trips it, which is the property that makes it
worth reading when it does fire: a check that cries wolf is one people
learn to skim, and it takes the true findings with it.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List

#: Modules that reach the network. `os` and `sys` are deliberately
#: absent: fifteen shipped roles import them for path handling, and a
#: check that fires on all fifteen teaches people to ignore it.
NETWORK_MODULES = {
    "aiohttp", "ftplib", "http", "httplib2", "httpx", "imaplib",
    "requests", "smtplib", "socket", "telnetlib", "urllib", "websocket",
}

#: Starting another program.
PROCESS_MODULES = {"multiprocessing", "pty", "subprocess"}

#: Calls that run code or a command chosen at run time. These are
#: matched by name, not by module, because `os.system(...)` is the
#: dangerous half of an `import os` that is otherwise ordinary.
DANGEROUS_CALLS = {
    "eval": "runs code built at run time",
    "exec": "runs code built at run time",
    "compile": "builds code at run time",
    "os.system": "runs a shell command",
    "os.popen": "runs a shell command",
    "os.execv": "replaces this process with another program",
    "subprocess.run": "runs another program",
    "subprocess.call": "runs another program",
    "subprocess.Popen": "runs another program",
}


@dataclass(frozen=True)
class Effect:
    """One thing a role's code reaches for."""

    path: Path
    kind: str  # "network" | "process" | "dynamic"
    detail: str  # what was found, in the words of the file


def _dotted(node: ast.AST) -> str:
    """`os.system` from an ast.Attribute chain; "" for anything else."""
    parts: List[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def scan_file(path: Path) -> List[Effect]:
    """Effects in one Python file. Never raises: a role that will not
    parse is a problem for the compiler to report, not for a lint."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []

    found: List[Effect] = []
    seen: set = set()

    def add(kind: str, detail: str) -> None:
        if (kind, detail) not in seen:
            seen.add((kind, detail))
            found.append(Effect(path, kind, detail))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module] if node.module else []
        else:
            if isinstance(node, ast.Call):
                name = (
                    node.func.id if isinstance(node.func, ast.Name)
                    else _dotted(node.func)
                )
                if name in DANGEROUS_CALLS:
                    add("dynamic", f"{name}() — {DANGEROUS_CALLS[name]}")
            continue

        for full in names:
            root = full.split(".")[0]
            if root in NETWORK_MODULES:
                add("network", f"imports `{full}`")
            elif root in PROCESS_MODULES:
                add("process", f"imports `{full}`")


    return found


def scan_office(office_dir: Path) -> List[Effect]:
    """Every Python file a student's office carries — its roles and its
    own sinks. Not the installed library, which is reviewed; this is
    about the code that arrived by being generated."""
    office_dir = Path(office_dir)
    out: List[Effect] = []
    for sub in ("roles", "sinks", "sources"):
        directory = office_dir / sub
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("__"):
                continue
            out.extend(scan_file(path))
    return out
