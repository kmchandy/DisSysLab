"""End-to-end: ``Name.refused``, where an office sends a refusal instead of stopping.

By default a contract refusal stops the whole office (agents/refusals.py).
An office that wires an agent's ``refused`` outbox has said what a refusal
there should do: the refused message goes out of it, with a field
``refusal`` giving the reason, the office carries on, and the refusal is
still recorded in ``refused.jsonl``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from tests.e2e.test_lab_paths import lines_of, run_office, write_office

REPO = Path(__file__).resolve().parents[2]
GALLERY = REPO / "dissyslab" / "gallery"

REFUSAL_LOG = textwrap.dedent('''\
    """
    ---
    emits: a refused ticket, marked refused, so that the desk can go on
    in: ticket_id, refusal
    out: outcome (refused)
    ---
    """


    class RefusalLog:
        def __call__(self, item):
            return {"outcome": "refused"}
    ''')

T5 = {"ticket_id": "T5", "customer": "Eve", "amount": -30, "item": "pen",
      "reason": "refund me thirty dollars"}


def dsl(*args: str, cwd: Path) -> str:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = os.pathsep.join([str(REPO)] + ([env["PYTHONPATH"]]
                                                       if env.get("PYTHONPATH") else []))
    done = subprocess.run(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))", *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return done.stdout + done.stderr


def desk_with_a_refusal_path(tmp_path: Path) -> Path:
    office = tmp_path / "desk"
    shutil.copytree(GALLERY / "returns_desk", office, ignore=shutil.ignore_patterns("__pycache__"))
    with open(office / "tickets.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(T5) + "\n")
    md = office / "office.md"
    text = md.read_text(encoding="utf-8").replace(
        "    Manager: manager\n", "    Manager: manager\n    Log: refusal_log\n")
    md.write_text(text.rstrip("\n") +
                  "\n    Clerk.refused -> Log -> jsonl_recorder, console_printer, Gate.done\n",
                  encoding="utf-8")
    (office / "roles" / "refusal_log.py").write_text(REFUSAL_LOG, encoding="utf-8")
    return office


def test_a_wired_refusal_goes_on_and_the_office_finishes(tmp_path):
    office = desk_with_a_refusal_path(tmp_path)
    code, out, _ = run_office(office)
    assert code == 0, out
    assert "Stopped:" not in out and "Stalled:" not in out, out
    outcomes = {o["ticket_id"]: o for o in lines_of(office / "outcomes.jsonl")}
    assert sorted(outcomes) == ["T1", "T2", "T3", "T4", "T5"]
    assert outcomes["T5"]["outcome"] == "refused"
    assert "'amount' is -30, below its range" in outcomes["T5"]["refusal"]
    record = lines_of(office / "refused.jsonl")
    assert [r["message"]["ticket_id"] for r in record] == ["T5"]
    assert record[0]["sent_to"] == "desk::Clerk.refused"
    assert "note: desk::Clerk refused 1 message(s) and sent them to Clerk.refused" in out


def test_without_the_wiring_the_same_refusal_stops_the_office(tmp_path):
    office = desk_with_a_refusal_path(tmp_path)
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8").replace(
        "    Clerk.refused -> Log -> jsonl_recorder, console_printer, Gate.done\n", "")
        .replace("    Log: refusal_log\n", ""), encoding="utf-8")
    code, out, _ = run_office(office)
    assert code == 1
    assert "Stopped: desk::Clerk refused a message, so the office stopped." in out


def test_only_an_agent_that_plays_a_role_has_a_refused_outbox(tmp_path):
    office = desk_with_a_refusal_path(tmp_path)
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8") + "    Rex.refused -> console_printer\n"
                  "    tickets.refused -> console_printer\n", encoding="utf-8")
    out = dsl("check", ".", cwd=office)
    assert "Clerk.refused" not in out  # the role's is fine
    assert "tickets has one outbox, out; it has no 'refused'" in out, out
    assert "Rex" in out and "refused" in out, out


def test_a_refused_outbox_is_never_a_barrier_to_untrusted_text(tmp_path):
    """An author with out: stops the customer's text. Its refused outbox does
    not: a refusal goes on as the message the agent received."""
    office = tmp_path / "dealer"
    shutil.copytree(GALLERY / "car_dealer", office, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "tests" / "e2e" / "car_dealer_guarded", office, dirs_exist_ok=True)
    assert "no problems found" in dsl("check", ".", cwd=office)
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8") + "    Guard.refused -> screen\n",
                  encoding="utf-8")
    assert "text from customer can reach screen" in dsl("check", ".", cwd=office)


SORRY = textwrap.dedent('''\
    """
    ---
    emits: a polite reply when Sal's reply was refused
    kind: author
    in: session, turn, refusal
    out: session, turn, reply
    ---
    """


    class Sorry:
        def __call__(self, item):
            return [{"session": item["session"], "turn": item["turn"],
                     "reply": "Sorry, I can't help with that here. A salesperson will call you."}]
    ''')


def test_lab_1_with_an_apology_for_a_refused_reply(tmp_path):
    """Sal answers in the wrong shape on one turn: the customer gets an
    apology, every other customer is still answered, and Sorry -- an author
    with out: -- keeps the customer's text from the screen."""
    office = tmp_path / "dealer"
    shutil.copytree(GALLERY / "car_dealer", office, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "tests" / "e2e" / "car_dealer_guarded", office, dirs_exist_ok=True)
    (office / "roles" / "sorry.py").write_text(SORRY, encoding="utf-8")
    md = office / "office.md"
    text = md.read_text(encoding="utf-8")
    text = text.replace('customer: chat_page(title="Main Street Motors")',
                        'customer: file_source(path="attacks.jsonl")')
    text = text.replace("screen: chat_reply", 'screen: jsonl_recorder(path="replies.jsonl")')
    text = text.replace("    Guard: price_guard\n", "    Guard: price_guard\n    Sorry: sorry\n")
    md.write_text(text.rstrip("\n") + "\n    Sal.refused -> Sorry -> screen\n", encoding="utf-8")
    assert "no problems found" in dsl("check", ".", cwd=office)
    script = [
        {"when": "You are Sal", "user_contains": "Equinox",
         "reply": json.dumps({"reply": "The Equinox is $31,200.", "vehicle": "equinox",
                              "price": 31200})},
        {"when": "You are Sal", "user_contains": '"session": "c02"',
         "reply": json.dumps({"reply": "Deal.", "vehicle": "a tahoe", "price": 1})},
        {"when": "You are Sal",
         "reply": json.dumps({"reply": "Happy to help.", "vehicle": "none", "price": 0})},
    ]
    code, out, _ = run_office(office, script)
    assert code == 0, out
    replies = {(r["session"], r["turn"]): r["reply"] for r in lines_of(office / "replies.jsonl")}
    attacks = lines_of(office / "attacks.jsonl")
    assert len(replies) == len(attacks)  # every turn answered
    assert replies[("c02", 1)].startswith("Sorry, I can't help")
    assert "c02" in {r["message"]["session"] for r in lines_of(office / "refused.jsonl")}
