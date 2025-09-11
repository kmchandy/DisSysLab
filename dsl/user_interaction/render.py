# dsl/user_interaction/render.py
"""
Minimal rendering helpers for lesson outputs.
- Pretty-print a NetworkSpec as ASCII.
- Show the generated code.
- Save the generated code to disk.
"""

from __future__ import annotations
import os
from dataclasses import asdict
from typing import List

from .lessons import NetworkSpec, CodeBundle


def render_spec_ascii(spec: NetworkSpec) -> str:
    """Return a compact ASCII view of blocks and connections."""
    lines: List[str] = []
    lines.append("Blocks:")
    for name, cls in spec.blocks.items():
        kw = spec.kwargs.get(name, {})
        if kw:
            lines.append(
                f"  - {name}: {cls}({', '.join(f'{k}={repr(v)}' for k, v in kw.items())})")
        else:
            lines.append(f"  - {name}: {cls}()")
    lines.append("Connections:")
    for src, outp, dst, inp in spec.connections:
        lines.append(f"  - {src}.{outp} -> {dst}.{inp}")
    return "\n".join(lines)


def render_code(bundle: CodeBundle) -> str:
    """Return the code exactly as it will be written to disk."""
    return bundle.code.rstrip() + "\n"


def save_code_bundle(bundle: CodeBundle) -> None:
    """Write the generated code to bundle.filename, creating parent dirs if needed."""
    path = bundle.filename
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(bundle.code)
