"""The activity half of termination detection.

`_terminated()` used to name the two kinds of agent that existed —
sources and non-sources — and test each differently. It now asks every
agent the same question: *are you idle, and is that answer current?*

These tests exercise the predicate directly rather than through a running
office, because what changed is the predicate. The rest of the suite
already covers the integration; nothing there fails if the `idle` bit is
ignored entirely, which is exactly why these exist.

See docs/internals/design/termination_detection_design.md §3–§4.
"""
from __future__ import annotations

from dissyslab.core import Agent
from dissyslab.os_agent import OsAgent


class _Stub:
    """Minimal stand-in for an agent. `_terminated` reads only inports."""

    def __init__(self, inports=(), outports=()):
        self.inports = list(inports)
        self.outports = list(outports)


def _os_agent(agents, connections=()):
    return OsAgent(agents=agents, graph_connections=list(connections))


def _reply(os_agent, name, *, idle=True, final=False, round_id=None,
           sent=None, received=None, omit_idle=False):
    """Feed one reply in, as `_drain_responses` would."""
    msg = {
        "agent": name,
        "sent": sent or {},
        "received": received or {},
        "round_id": os_agent._round if round_id is None else round_id,
    }
    if not omit_idle:
        msg["idle"] = idle
    if final:
        msg["final"] = True
    os_agent._update_counts(msg)


# ── The base contract ────────────────────────────────────────────────────


def test_a_reactive_agent_is_always_idle():
    """A reactive agent can only answer from inside `recv`, where it owes
    nothing — so answering is itself the proof, and the base returns a
    constant. If this ever becomes conditional, the round tag is doing
    work it was not designed for."""
    class Reactive(Agent):
        def run(self):
            pass

    a = Reactive(inports=["in_"], outports=["out_"])
    assert a.is_idle() is True
    assert a.is_final() is False


# ── The predicate ────────────────────────────────────────────────────────


def test_an_active_agent_blocks_termination():
    """The point of the whole exercise. Channels balanced, reply current,
    and still not terminated — because the agent says it owes a send."""
    os_agent = _os_agent({"A": _Stub(inports=["in_"])})
    os_agent._round = 1
    _reply(os_agent, "A", idle=False)
    assert os_agent._terminated() is False


def test_the_same_agent_reporting_idle_terminates():
    os_agent = _os_agent({"A": _Stub(inports=["in_"])})
    os_agent._round = 1
    _reply(os_agent, "A", idle=True)
    assert os_agent._terminated() is True


def test_a_stale_idle_reply_is_not_believed():
    """The round tag's job. A reactive agent mid-computation does not
    reply at all; its previous reply said idle, because it was sent from
    inside recv. Believing it would declare termination while the agent
    is running."""
    os_agent = _os_agent({"A": _Stub(inports=["in_"])})
    os_agent._round = 1
    _reply(os_agent, "A", idle=True, round_id=1)
    assert os_agent._terminated() is True

    os_agent._round = 2                      # a new round; A has not answered
    assert os_agent._terminated() is False


def test_a_missing_idle_field_counts_as_active():
    """The conservative default. An agent kind that forgets to report
    must delay termination, never cause a premature one."""
    os_agent = _os_agent({"A": _Stub(inports=["in_"])})
    os_agent._round = 1
    _reply(os_agent, "A", omit_idle=True)
    assert os_agent._terminated() is False


# ── final ────────────────────────────────────────────────────────────────


def test_final_excuses_an_agent_from_later_rounds():
    """How an exhausted source bows out: its thread has ended, so it
    cannot answer round 2, and 'gone' must not read as 'slow'."""
    os_agent = _os_agent({"S": _Stub(outports=["out_"])})
    os_agent._round = 1
    _reply(os_agent, "S", idle=True, final=True)

    os_agent._round = 2
    assert os_agent._terminated() is True     # no reply needed, and none coming


def test_final_is_sticky():
    """A later reply without the flag must not un-finalise an agent."""
    os_agent = _os_agent({"S": _Stub(outports=["out_"])})
    os_agent._round = 1
    _reply(os_agent, "S", idle=True, final=True)
    _reply(os_agent, "S", idle=False, final=False)

    os_agent._round = 2
    assert os_agent._terminated() is True


def test_a_running_source_blocks_termination():
    """A source that has not finished has sent no reply at all, so it is
    neither final nor current. This is the case the old `heard_from`
    check covered, and it must still hold."""
    os_agent = _os_agent({"S": _Stub(outports=["out_"])})
    os_agent._round = 1
    assert os_agent._terminated() is False


# ── activity and channels are independent conditions ────────────────────


def test_idle_agents_with_a_full_channel_do_not_terminate():
    """Every agent idle is not enough — a message in a channel is work
    that will make one of them active again."""
    os_agent = _os_agent(
        {"A": _Stub(outports=["out_"]), "B": _Stub(inports=["in_"])},
        connections=[("A", "out_", "B", "in_")],
    )
    os_agent._round = 1
    _reply(os_agent, "A", idle=True, final=True, sent={"out_": 1})
    _reply(os_agent, "B", idle=True, received={"in_": 0})
    assert os_agent._terminated() is False

    _reply(os_agent, "B", idle=True, received={"in_": 1})
    assert os_agent._terminated() is True
