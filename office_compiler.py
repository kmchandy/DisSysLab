#!/usr/bin/env python3
"""
Deprecated shim for office_compiler.

This file exists only so that
    python office_compiler.py <office_dir>
keeps working during the v1.0 transition. It forwards to the real
module at dissyslab.office.office_compiler and prints a one-line
notice suggesting the new invocation.

Prefer either:
    dsl build <office_dir>                              # after pipx install
    python -m dissyslab.office.office_compiler <office_dir>

This shim will be removed in a later release.
"""

import sys
import warnings
import runpy

_NOTE = (
    "[dissyslab] office_compiler.py at the repo root is deprecated. "
    "Use `dsl build <office_dir>` or "
    "`python -m dissyslab.office.office_compiler <office_dir>`."
)

# Visible, unmissable hint for humans.
print(_NOTE, file=sys.stderr)

# Machine-visible deprecation for tooling (pytest, linters, etc).
warnings.warn(_NOTE, DeprecationWarning, stacklevel=2)

# Hand sys.argv through unchanged. runpy executes the module as __main__,
# which means its existing `if __name__ == "__main__":` block runs exactly
# as if the user had invoked the real file directly.
runpy.run_module("dissyslab.office.office_compiler", run_name="__main__")
