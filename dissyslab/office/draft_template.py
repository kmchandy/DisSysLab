# <office_name>.officespeak.py
#
# Draft produced at the end of a Track A conversation (see
# start_instructions_v3.md's final step). Track A fills in every agent's
# name, kind, ports, connections, and plain-English description -- all of
# that is already fully decided by the end of the conversation. Track A
# does **not** write any code or prompt (that is explicitly out of scope
# for Phase 1/2 -- "write no code and no prompt here... a later step, not
# here"), so every body_fn/body_prompt starts out as a placeholder, and
# every source/sink's registered_as starts out as None.
#
# Al's job -- typically *with* Claude's help drafting from each
# description, not alone; see the "Al-Claude conversation" this file's
# case's transcript walks through -- is to turn every placeholder into a
# real, tested body (phase3_approval.md) and every None registered_as into
# a real match (phase3_source_sink_matching.md), then flip approved=True.
#
# Once every worker is approved and every source/sink matched, run:
#   python -m dissyslab.office.assemble <this_file> <target_dir>
#   dsl build <target_dir>
#   dsl run <target_dir>
#
# This file shows the shipment-release case (cold_tests/transcripts/
# full_chain_case_01_shipment_release.md) already carried all the way to
# drafted-but-not-yet-approved bodies (approved=False, one registered_as
# still None) -- i.e. Al and Claude have drafted `_make_scan_fn` and
# friends from Phase 2's descriptions, but no one has tested them or
# matched DOCK yet. A fresh hand-off from Track A would start further
# back, with body_fn=None for every transform too.

from __future__ import annotations

OFFICE_NAME = "shipment_release"


# ── Worker bodies (drafted by Al+Claude from Phase 2's descriptions, from
#    a starting point of body_fn=None; not yet tested/approved below) ──


def _make_scan_fn():
    _EVENTS = [
        {"shipment_id": "S101"},
        {"shipment_id": "S103"},
        {"shipment_id": "S102"},
    ]

    def scan_fn(msg):
        return [({"kind": "scan", **e}, "out") for e in _EVENTS]

    return scan_fn


def _make_manifest_fn():
    _EVENTS = [
        {"shipment_id": "S102"},
        {"shipment_id": "S101"},
        {"shipment_id": "S103"},
    ]

    def manifest_fn(msg):
        return [({"kind": "manifest", **e}, "out") for e in _EVENTS]

    return manifest_fn


def _make_match_fn():
    pending = {}

    def match_fn(msg):
        kind = msg["kind"]
        sid = msg["shipment_id"]
        other_kind = "manifest" if kind == "scan" else "scan"
        slot = pending.setdefault(sid, {})
        if other_kind in slot:
            slot.pop(other_kind)
            if not slot:
                del pending[sid]
            return [({"shipment_id": sid, "release": True}, "out")]
        slot[kind] = msg
        return None

    return match_fn


# ── Agents -- every field Track A already knows, filled in ──────────────

AGENTS = [
    # A registered source Pat's office needs a real kick from. Track A
    # knows this is DisSysLab's built-in `starter`, since every office
    # needs exactly this to begin -- not something Al has to match.
    dict(
        name="STARTER",
        kind="source",
        in_ports=[],
        out_ports=["destination"],
        description="Kicks the office off once, at start.",
        registered_as="starter",
        registered_args={},
    ),
    dict(
        name="SCAN",
        kind="transform",
        in_ports=["in_"],
        out_ports=["out"],
        description=(
            "Whenever a shipment is scanned in at the warehouse, sends a "
            "scan record naming that shipment's ID."
        ),
        body_kind="python",
        body_fn=_make_scan_fn,
        approved=False,  # TODO(Al): run on example inputs (phase3_approval.md), then True
    ),
    dict(
        name="MANIFEST",
        kind="transform",
        in_ports=["in_"],
        out_ports=["out"],
        description=(
            "Whenever a shipment's manifest paperwork comes in, sends a "
            "manifest record naming that shipment's ID."
        ),
        body_kind="python",
        body_fn=_make_manifest_fn,
        approved=False,  # TODO(Al): run on example inputs (phase3_approval.md), then True
    ),
    dict(
        name="MATCH",
        kind="transform",
        in_ports=["in_"],
        out_ports=["out"],
        description=(
            "Keeps a note per shipment ID of whichever of scan/manifest "
            "has arrived so far; once both are in for the same ID, sends "
            "the release notice and clears that shipment's note."
        ),
        body_kind="python",
        body_fn=_make_match_fn,
        approved=False,  # TODO(Al): run on example inputs (phase3_approval.md), then True
    ),
    dict(
        name="DOCK",
        kind="sink",
        in_ports=["in_"],
        out_ports=[],
        description="The loading dock -- where the release notice shows up.",
        registered_as=None,  # TODO(Al): match against docs/SOURCES_AND_SINKS.md
        registered_args={},
    ),
]


# ── Connections -- Track A's own 4-tuples, unchanged ─────────────────────

CONNECTIONS = [
    ("STARTER", "destination", "SCAN", "in_"),
    ("STARTER", "destination", "MANIFEST", "in_"),
    ("SCAN", "out", "MATCH", "in_"),
    ("MANIFEST", "out", "MATCH", "in_"),
    ("MATCH", "out", "DOCK", "in_"),
]
