"""docs/GETTING_STARTED.md shows what DisSysLab really prints.

Students who miss a lecture follow that guide line by line and compare
what they see with what it shows. An output quoted there that DisSysLab no
longer prints -- a reworded error, a changed summary -- sends them looking
for a mistake they did not make. So the steps that need no model key are
run here, in folders with the guide's names, and every line the guide
quotes for them must be in the real output.

(The steps with a language model are not run: the model's words vary, and
the guide says so.)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUIDE = (REPO / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
GALLERY = REPO / "dissyslab" / "gallery"


def dsl(*args: str, cwd: Path) -> str:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))", *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return proc.stdout + proc.stderr


def desk(tmp_path: Path, edit=None) -> Path:
    office = tmp_path / "my_desk"
    shutil.copytree(GALLERY / "returns_desk", office, ignore=shutil.ignore_patterns("__pycache__"))
    if edit:
        edit(office)
    return office


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"the guide's edit no longer applies: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _unnumbered(text: str) -> str:
    """Text without console_printer's "[n] " counters, which number messages
    in the order they reach the printer: not always ticket order (in
    returns_desk the gate releases the next ticket while the printer is still
    receiving this one), so a line is compared without its number."""
    return re.sub(r"^\[\d+\] ", "", text, flags=re.M)


def quoted_in_guide_and_printed(lines: list[str], out: str) -> None:
    for line in lines:
        assert line in GUIDE, f"the guide no longer quotes: {line!r}"
        assert _unnumbered(line) in _unnumbered(out), (
            f"the guide quotes a line DisSysLab no longer prints:\n{line}\n\n{out}")


def test_unnumbered_ignores_only_the_counter():
    assert _unnumbered("[3] {'ticket_id': 'T4'}\n[4] {'ticket_id': 'T3'}") == (
        "{'ticket_id': 'T4'}\n{'ticket_id': 'T3'}")
    assert _unnumbered("x [3] y") == "x [3] y"


TICKET_LINES = [
    "[1] {'ticket_id': 'T1', 'customer': 'Ana', 'amount': 20, 'item': 'book', 'reason': 'wrong item', 'clerk_decision': 'approve'}",
    "[4] {'ticket_id': 'T4', 'customer': 'Dee', 'amount': 80, 'item': 'monitor', 'reason': 'defective', 'clerk_decision': 'escalate', 'manager_decision': 'approve'}",
]


def test_part_2_the_first_office(tmp_path):
    office = desk(tmp_path)
    quoted_in_guide_and_printed(["my_desk/office.md:\n  no problems found."], dsl("check", ".", cwd=office))
    quoted_in_guide_and_printed(["    Rex.escalate -> Manager", "    Manager -> Gate.done",
                                 "    Rex              router"], dsl("draw", ".", cwd=office))
    out = dsl("run", ".", cwd=office)
    quoted_in_guide_and_printed(TICKET_LINES + [
        "  my_desk::Gate              sent      4   received      8"], out)


def test_part_3_a_higher_limit(tmp_path):
    office = desk(tmp_path, lambda o: replace(o / "office.md", "clerk(limit=50)", "clerk(limit=100)"))
    quoted_in_guide_and_printed([
        "[4] {'ticket_id': 'T4', 'customer': 'Dee', 'amount': 80, 'item': 'monitor', 'reason': 'defective', 'clerk_decision': 'approve'}",
    ], dsl("run", ".", "--quiet", cwd=office))


def test_part_4_1_a_misspelt_name(tmp_path):
    office = desk(tmp_path, lambda o: replace(o / "office.md", "Clerk: clerk(", "Clerk: clerck("))
    line = "  problem: line 12: no agent called 'clerck' in roles/ or the built-ins. Did you mean 'clerk'?"
    quoted_in_guide_and_printed([line], dsl("check", ".", cwd=office))
    quoted_in_guide_and_printed(["dsl run: my_desk cannot start."], dsl("run", ".", cwd=office))


def test_part_4_2_a_misspelt_router_value(tmp_path):
    office = desk(tmp_path, lambda o: replace(o / "office.md", "Rex.approve ->", "Rex.aprove ->"))
    quoted_in_guide_and_printed([
        "  note: line 13: Rex has no outbox for clerk_decision 'approve' (declared by Clerk) and no otherwise; such a message would fail at run time.",
        "  note: line 18: Rex.aprove can never be used: Clerk declares clerk_decision as approve | escalate. Did you mean 'approve'?",
    ], dsl("check", ".", cwd=office))
    quoted_in_guide_and_printed([
        "    first failure: 'clerk_decision' is 'approve', which has no outbox here and there is no otherwise. Outboxes: aprove, escalate.",
    ], dsl("run", ".", cwd=office))


def _crash(office: Path) -> None:
    replace(office / "roles" / "clerk.py", "def step(item, settings):\n",
            "def step(item, settings):\n"
            "    if item[\"amount\"] > 100:\n"
            "        raise ValueError(f\"no refunds over 100 here, got {item['amount']}\")\n")


def test_part_4_3_and_4_4_a_crash_and_its_stall(tmp_path):
    office = desk(tmp_path, _crash)
    out = dsl("run", ".", cwd=office)
    quoted_in_guide_and_printed([
        "    first failure: ValueError: no refunds over 100 here, got 120",
        "Stalled: my_desk::Gate holds an item it admitted, until done arrives; it will never arrive.",
        "  my_desk::Gate.done <- my_desk::Manager.out: empty; my_desk::Manager is idle, waiting on in",
        "  my_desk::Clerk.in <- my_desk::Gate.out: empty; my_desk::Gate is already on this path",
        "  2 message(s) wait unread on my_desk::Gate.in.",
    ], out)


def test_part_4_4_a_stall_without_a_crash(tmp_path):
    office = desk(tmp_path, lambda o: replace(
        o / "office.md", "Manager -> jsonl_recorder, console_printer, Gate.done",
        "Manager -> jsonl_recorder, console_printer"))
    out = dsl("run", ".", cwd=office)
    quoted_in_guide_and_printed([
        "  my_desk::Rex.in <- my_desk::Clerk.out: empty; my_desk::Clerk is idle, waiting on in",
        "    (the path that proves it is printed above, under 'Stalled:')",
    ], out)
    assert "Manager" not in out.split("Stalled:")[1].split("\n\n")[0]


def test_part_6_the_first_steps_of_the_inbox_sorter(tmp_path):
    office = tmp_path / "inbox_sorter"
    office.mkdir()
    for name in ("messages.jsonl",):
        shutil.copy(GALLERY / "inbox_sorter" / name, office / name)
    head = ("# inbox_sorter: messages to the course staff, sorted by how soon they need an answer.\n\n"
            "sources:\n    inbox: file_source(path=\"messages.jsonl\")\n\nsinks:\n    console_printer\n\n")
    (office / "office.md").write_text(head + "connections:\n    inbox -> console_printer\n",
                                      encoding="utf-8")
    quoted_in_guide_and_printed([
        "[2] {'id': 2, 'subject': 'Office hours', 'text': 'Are office hours on Thursday this week?'}",
    ], dsl("run", ".", cwd=office))
    (office / "office.md").write_text(
        head + "agents:\n    Tri: unassigned\n\nconnections:\n    inbox -> Tri -> console_printer\n",
        encoding="utf-8")
    quoted_in_guide_and_printed([
        "  note: line 10: Tri is unassigned, so this office is a draft: it can be checked, not run.",
    ], dsl("check", ".", cwd=office))
    quoted_in_guide_and_printed([
        "  line 10: Tri is unassigned; a draft office can be checked and drawn, but not run. Give it a role first.",
    ], dsl("run", ".", cwd=office))


def test_the_guide_quotes_the_gallery_inbox_sorter():
    """Step 6.4's role and step 6.5's office are the gallery's own files."""
    role = (GALLERY / "inbox_sorter" / "roles" / "triage.md").read_text(encoding="utf-8").rstrip()
    office = (GALLERY / "inbox_sorter" / "office.md").read_text(encoding="utf-8").rstrip()
    messages = (GALLERY / "inbox_sorter" / "messages.jsonl").read_text(encoding="utf-8").rstrip()
    for text, what in ((role, "triage.md"), (office, "office.md"), (messages, "messages.jsonl")):
        assert f"```\n{text}\n```" in GUIDE, f"step 6 no longer shows the gallery's {what}"


@pytest.mark.parametrize("command", ["dsl grammar", "dsl grammar roles", "dsl grammar sources",
                                     "dsl grammar examples", "dsl roles", "dsl show summarizer"])
def test_the_commands_in_part_9_work(command, tmp_path):
    out = dsl(*command.split()[1:], cwd=tmp_path)
    assert "Traceback" not in out and out.strip(), out
