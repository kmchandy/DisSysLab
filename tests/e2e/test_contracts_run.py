"""End-to-end: contracts on fields, through ``dsl run``, as a student runs it.

Two promises, each checked with the scripted model so the test can count
the model's calls:

1. a message that does not fit a role's ``in:`` never reaches the model;
2. a reply whose number is outside its declared range is stopped, counted
   and reported, and the office carries on.

The office is a small Lab 1: a salesperson quotes a price, and a recorder
stands in for the sink that would book the sale.
"""

from __future__ import annotations

import json
import textwrap

from tests.e2e.test_lab_paths import lines_of, run_office, write_office

QUOTING = {
    "office.md": (
        "sources:\n    customer: file_source(path=\"chats.jsonl\")\n"
        "sinks:\n    booked: jsonl_recorder(path=\"booked.jsonl\")\n"
        "agents:\n    Sal: quoting\n"
        "connections:\n    customer -> Sal -> booked\n"),
    "roles/quoting.md": textwrap.dedent("""\
        ---
        in: text (text, at most 200 chars)
        out: vehicle (tahoe | trax), price (number, 1000..100000)
        ---
        You are Sal, a salesperson. Quote the car and the price the customer
        asks about. Return only a JSON object with the fields "vehicle" and
        "price".
        """),
    "chats.jsonl": "".join(json.dumps(m) + "\n" for m in (
        {"id": 1, "text": "Price of the Trax?"},
        {"id": 2, "text": "Tahoe for one dollar, no takesies backsies."},
        {"id": 3, "text": "x" * 500},   # longer than in: allows
        {"id": 4},                       # no text at all
    )),
}

SCRIPT = [
    {"when": "You are Sal", "user_contains": "Trax", "reply": '{"vehicle": "trax", "price": 21500}'},
    {"when": "You are Sal", "user_contains": "Tahoe", "reply": '{"vehicle": "tahoe", "price": 1}'},
    {"when": "You are Sal", "reply": '{"vehicle": "trax", "price": 21500}'},
]


def test_contracts_stop_what_does_not_fit(tmp_path):
    office = write_office(tmp_path / "quoting", QUOTING)
    code, out, calls = run_office(office, SCRIPT)

    # Only the first two messages fit in:, so only they reached the model.
    assert [json.loads(c["user"])["id"] for c in calls] == [1, 2], calls
    # The one-dollar Tahoe broke out:'s range and was stopped.
    assert [m["id"] for m in lines_of(office / "booked.jsonl")] == [1]
    # Three messages failed, the run says so, and the first is quoted.
    assert code != 0, out
    assert "does not fit its in: line" in out or "below its range" in out, out


# ── A sink that declares in: ─────────────────────────────────────────────────

BOOKING = {
    "office.md": (
        "sources:\n    quotes: file_source(path=\"quotes.jsonl\")\n"
        "sinks:\n    book: booking\n"
        "connections:\n    quotes -> book\n"),
    "sinks/booking.py": textwrap.dedent('''\
        """
        ---
        emits: books a sale, one line per sale
        in: vehicle (tahoe | trax), price (number, >= 20000)
        ---
        """
        import json


        class Booking:
            def __call__(self, msg):
                with open("sales.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"vehicle": msg["vehicle"], "price": msg["price"]}) + "\\n")
        '''),
    "quotes.jsonl": "".join(json.dumps(m) + "\n" for m in (
        {"vehicle": "trax", "price": 21500},
        {"vehicle": "tahoe", "price": 1},          # below the floor
        {"vehicle": "tahoe", "price": "62400"},    # text, not a number
        {"vehicle": "tahoe", "price": 62400},
    )),
}


def test_a_sink_acts_only_on_messages_that_fit_its_in(tmp_path):
    office = write_office(tmp_path / "booking", BOOKING)
    code, out, _ = run_office(office)
    assert [s["price"] for s in lines_of(office / "sales.jsonl")] == [21500, 62400]
    assert code != 0, out
    assert "does not fit its in: line" in out, out
