# dissyslab/components/sources/starter_source.py

"""
Starter — emits exactly one message at startup, then stops.

Use case: an iterative office (debate / consensus / multi-round
agreement) needs a single bootstrap "go" signal to kick off its
cycle. After the first round, the iteration is driven by feedback
edges inside the office — the source's job is done.

Pat-side usage in office.md::

    Sources: starter
    ...
    starter's destination is Sasha.

That single dict ``{"signal": "start"}`` arrives at Sasha; whatever
loop the office wires up takes over from there.

The source returns ``None`` on every subsequent ``run()`` call, which
is the framework's signal that the source has nothing more to emit.
"""


class Starter:
    """Source that fires exactly once.

    Args:
        payload: The dict emitted on first ``run()``. Defaults to
            ``{"signal": "start"}``. Most callers leave it alone.
    """

    def __init__(self, payload: dict | None = None):
        self._payload = payload or {"signal": "start"}
        self._fired = False

    def run(self):
        if self._fired:
            return None
        self._fired = True
        return self._payload
