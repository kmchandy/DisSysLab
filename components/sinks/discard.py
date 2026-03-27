# components/sinks/discard.py

"""
Discard: Sink that silently drops every message it receives.

Used when a role routes messages to "discard" in an office spec.
No output, no logging, no side effects.
"""


class Discard:
    """
    Sink that silently drops messages.

    Treated as an ordinary sink — nothing special about it.
    Useful as a routing destination when messages should be ignored.
    """

    def __init__(self):
        self._count = 0

    def __call__(self, msg):
        self._count += 1

    run = __call__

    def finalize(self):
        pass
