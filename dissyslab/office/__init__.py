# dissyslab/office/__init__.py
"""
dissyslab.office - Office compilation utilities.

This subpackage contains the machinery that reads role and office
description files and emits runnable app.py files:

  - utils           : shared helpers, registries, file parsing
  - make_office     : generate app.py from an office description
  - make_network    : generate the network wiring
  - office_compiler : top-level driver used by `dsl build` and by the
                      repo-root deprecation shim at office_compiler.py

First-year students normally do not import from this subpackage
directly; they run the CLI (`dsl build <office_dir>`) or the shim
(`python office_compiler.py <office_dir>`).
"""
