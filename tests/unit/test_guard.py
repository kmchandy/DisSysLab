"""Guards: a user's own checks around a role, most usefully a model call.

Two properties matter more than any individual behaviour, and most of
this file is about them.

**A guarded role must produce exactly what the unguarded one would**,
when nothing is rejected. A guard that quietly reshapes messages is a
guard nobody can reason about, and it would make "add checks" a change
of behaviour rather than an addition of one.

**A rejection must be audible.** Silence would put a guard in the same
class as a source that returns nothing: an office producing less than it
should, for a reason nobody can see.

See `docs/internals/design/guard_rails.md` for why a guard is composed
inside one agent rather than wired as its own.
"""
from __future__ import annotations

import pytest

from dissyslab.blocks.role import Role, normalise_results
from dissyslab.office.library import AgentRoleEntry, guard


def _inner(out_ports=("keep", "discard")) -> AgentRoleEntry:
    """A stand-in for a model role: adds a field, chooses an outbox."""

    def fn(msg):
        return [({**msg, "seen": True}, "keep" if msg.get("ok") else "discard")]

    return AgentRoleEntry(
        name="fake_filter",
        in_ports=("in_",),
        out_ports=out_ports,
        factory=lambda: Role(fn=fn, statuses=list(out_ports)),
    )


def _run(entry: AgentRoleEntry, msg):
    return entry.factory()._fn(msg)


# ── the two properties ────────────────────────────────────────────────


def test_a_passing_guard_changes_nothing():
    """The property the whole design rests on."""
    plain = _run(_inner(), {"ok": True})
    guarded = _run(guard(_inner(), before=lambda m: None), {"ok": True})
    assert guarded == plain


def test_a_rejection_is_printed(capsys):
    def before(msg):
        raise ValueError("no title")

    _run(guard(_inner(), before=before), {"ok": True})
    assert "no title" in capsys.readouterr().out


# ── rejecting ─────────────────────────────────────────────────────────


def test_an_input_check_stops_the_model_being_called():
    """Not merely that the message is dropped: the wrapped role must not
    run at all. An input guard that rejects *after* paying for the call
    has saved nothing that matters."""
    calls = []

    def fn(msg):
        calls.append(msg)
        return [(msg, "keep")]

    inner = AgentRoleEntry(
        name="counted", in_ports=("in_",), out_ports=("keep",),
        factory=lambda: Role(fn=fn, statuses=["keep"]),
    )

    def before(msg):
        raise ValueError("rejected")

    assert _run(guard(inner, before=before), {"x": 1}) == []
    assert calls == [], "the wrapped role ran despite the input check"


def test_an_output_check_sees_the_chosen_outbox():
    """The reason `after` takes two arguments: a useful check often
    wants to veto the routing rather than the content."""
    seen = []

    def after(msg, outbox):
        seen.append(outbox)

    _run(guard(_inner(), after=after), {"ok": False})
    assert seen == ["discard"]


def test_rejecting_one_of_several_keeps_the_others():
    def fn(msg):
        return [({"n": 1}, "keep"), ({"n": 2}, "keep")]

    inner = AgentRoleEntry(
        name="two", in_ports=("in_",), out_ports=("keep",),
        factory=lambda: Role(fn=fn, statuses=["keep"]),
    )

    def after(msg, outbox):
        if msg["n"] == 1:
            raise ValueError("no")

    assert _run(guard(inner, after=after), {}) == [({"n": 2}, "keep")]


# ── the rejected outbox ───────────────────────────────────────────────


def test_on_reject_adds_an_outbox():
    """And that is what makes an opt-in guard visible in office.md:
    because an unwired outbox is an error, taking this option forces the
    office to say where rejected messages go."""
    g = guard(_inner(), before=lambda m: None, on_reject="rejected")
    assert g.out_ports == ("keep", "discard", "rejected")


def test_a_rejected_message_goes_there():
    def before(msg):
        raise ValueError("no")

    g = guard(_inner(), before=before, on_reject="rejected")
    assert _run(g, {"ok": True}) == [({"ok": True}, "rejected")]


def test_a_colliding_reject_name_is_refused():
    with pytest.raises(ValueError, match="collides"):
        guard(_inner(), before=lambda m: None, on_reject="keep")


# ── the shape of the thing ────────────────────────────────────────────


def test_the_ports_are_the_wrapped_role_s():
    g = guard(_inner(), before=lambda m: None)
    assert g.in_ports == ("in_",)
    assert g.out_ports == ("keep", "discard")


def test_a_guard_with_no_checks_is_refused():
    """It is the unguarded role, and saying so is more useful than
    silently building a pass-through somebody will later mistake for
    protection."""
    with pytest.raises(ValueError, match="unguarded"):
        guard(_inner())


def test_an_unknown_builtin_name_lists_the_real_ones():
    with pytest.raises(ValueError, match="no built-in role"):
        guard("relevanse_filter", before=lambda m: None)


def test_it_wraps_a_builtin_by_name():
    """Set, not sequence. Port *order* is meaningful at run time --
    `out_ports[i]` maps to `out_i` -- and it comes from the order the
    role's prose happens to mention them. Pinning it here would test the
    wording of `relevance_filter.md` rather than anything about guards."""
    g = guard("relevance_filter", before=lambda m: None)
    assert set(g.out_ports) == {"keep", "discard"}
    assert g.in_ports == ("in_",)


# ── the shared normaliser ─────────────────────────────────────────────


@pytest.mark.parametrize("returned,expected", [
    (None, None),
    ("plain", [("plain", "all")]),
    ([{"a": 1}], [({"a": 1}, "all")]),
    ([({"a": 1}, "keep")], [({"a": 1}, "keep")]),
])
def test_all_four_return_shapes(returned, expected):
    """`Role.run` and `guard` must read a role function's return value
    identically. Two copies of this rule would drift, and the drift
    would show as a guarded role behaving differently from the same role
    unguarded."""
    assert normalise_results(returned) == expected


def test_a_role_returning_none_still_drops():
    inner = AgentRoleEntry(
        name="dropper", in_ports=("in_",), out_ports=("out",),
        factory=lambda: Role(fn=lambda m: None, statuses=["out"]),
    )
    assert _run(guard(inner, before=lambda m: None), {}) is None
