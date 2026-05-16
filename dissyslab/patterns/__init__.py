"""
dissyslab.patterns — builder functions that turn the documented
agent-network patterns into running offices.

Each pattern in ``docs/PATTERN_*.md`` has a corresponding builder
function in this subpackage. The builder takes the pattern's
customization parameters (e.g. for sense → think → respond:
sources, thinkers, writer, sinks) and writes a working office.md
at a target directory.

Today we ship one builder:

* :func:`sense_think_respond.build_office` — the
  sense → think → respond pattern documented in
  ``docs/PATTERN_sense_think_respond.md``. Most Pat-facing gallery
  offices instantiate this pattern.

Future builders for other patterns (feedback loops, real-time
alerts, hierarchical sub-offices, …) live alongside as separate
modules.
"""

from dissyslab.patterns.sense_think_respond import (
    build_office,
)

__all__ = ["build_office"]
