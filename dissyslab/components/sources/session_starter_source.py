# dissyslab/components/sources/session_starter_source.py

"""
SessionStarterSource: emits one parameterized kickoff message, then
stops. Built for adaptive_tutor (PLANNER needs a "start this session
with variant=X" message to begin), but generic enough for any office
that needs a one-shot start signal carrying office.md-supplied
parameters -- the built-in `starter` source (starter_source.py) covers
the parameterless case (`{"signal": "start"}`); this is its
parameterized cousin.

Message shape:
    {"kind": "start", **kwargs}

Usage:
    Sources: session_starter(variant="easy")
"""

from typing import Any, Dict


class SessionStarterSource:
    def __init__(self, **kwargs: Any):
        self.kwargs: Dict[str, Any] = kwargs

    def run(self):
        yield {"kind": "start", **self.kwargs}
