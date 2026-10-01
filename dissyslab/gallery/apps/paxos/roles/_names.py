# dissyslab/gallery/apps/paxos/roles/_names.py

"""The short name of an agent.

Every message in this office carries the id of the agent that sent it,
because the acceptors must reply to the proposer that asked and the
proposers and learners must count answers from M *different*
acceptors. The obvious id is ``self.name`` -- and it is the wrong one.
The office qualifies an agent's name with the office it belongs to, so
at run time ``self.name`` is ``"paxos::Q2"``, not ``"Q2"``.

That matters here because the acceptor looks the sender up in a table
of proposer names written as the office writes them, ``P0 P1 P2``. The
first run of this office sent thirty reads, dropped every one of them
as coming from an unknown proposer, and terminated quietly with no
value agreed and nothing in the error count.

Underscore-first, so the role loader does not look for a ``role`` in
it -- the same convention as ``adaptive_tutor/roles/_subject_common.py``.
"""

from __future__ import annotations


def bare(name: object) -> str:
    """``"paxos::Q2"`` -> ``"Q2"``; anything else unchanged."""
    return str(name).rsplit("::", 1)[-1]
