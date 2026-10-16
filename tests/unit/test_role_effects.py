"""What a role's own Python reaches for — a lint, and it teaches.

W11 asks whether text from the open web can reach a sink that acts.
That question is *complete* only while an agent's body cannot act: an
English role is a paragraph sent to a model, and whatever the model is
persuaded to say, it can only put words in a message.

Once roles are Python, an agent can open a socket without going near a
sink, and W11 quietly becomes a check on one of two channels — same
output, same tests, smaller coverage, and nothing announcing it.

The exposure itself is **not this project's**. Any student running any
assistant-written Python has it, and a sandbox to solve one instance of
a general problem would be overreach. What is this project's is the
claim: a plain script promises nothing, while an office says its power
is its sinks.

So this is a lint, framed as teaching. It reads imports and a handful
of call names. It cannot see what code does, cannot follow an alias,
and can be evaded by anyone trying. Every test below is about keeping
that boundary honest.
"""
from __future__ import annotations

from pathlib import Path

from dissyslab.office.role_effects import scan_file, scan_office

REPO_ROOT = Path(__file__).resolve().parents[2]


def _role(tmp_path: Path, body: str, name: str = "r.py") -> Path:
    d = tmp_path / "roles"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


# ── what it catches ───────────────────────────────────────────────────


def test_it_catches_a_role_that_reaches_the_network(tmp_path):
    """The scenario, and note that nobody in it is careless. A student
    asks for an agent that checks whether each link is still live; the
    assistant writes `requests.head(msg["url"])`. Sensible request,
    sensible answer — and the office now makes an outbound request to
    whatever URL a stranger's feed supplied, with no sink involved and
    nothing on the graph to see."""
    p = _role(tmp_path, "import requests\n\ndef f(m):\n    return m\n")
    effects = scan_file(p)
    assert [e.kind for e in effects] == ["network"]
    assert "requests" in effects[0].detail


def test_it_catches_running_another_program(tmp_path):
    p = _role(tmp_path, "import subprocess\nsubprocess.run(['ls'])\n")
    kinds = {e.kind for e in scan_file(p)}
    assert kinds == {"process", "dynamic"}


def test_it_catches_code_built_at_run_time(tmp_path):
    p = _role(tmp_path, "def f(m):\n    return eval(m['expr'])\n")
    assert [e.kind for e in scan_file(p)] == ["dynamic"]


def test_os_system_is_caught_but_import_os_is_not(tmp_path):
    """The distinction that decides whether anyone reads this check.
    Fifteen shipped roles import `os` for path handling. Flagging all
    fifteen would teach people to skim it, and the true findings would
    go with them. `os.system` is the half that matters."""
    plain = _role(tmp_path, "import os\np = os.path.join('a', 'b')\n", "a.py")
    assert scan_file(plain) == []

    shelling = _role(tmp_path, "import os\nos.system('rm -rf /')\n", "b.py")
    assert [e.kind for e in scan_file(shelling)] == ["dynamic"]


def test_an_ordinary_role_trips_nothing(tmp_path):
    p = _role(tmp_path, (
        "from typing import Any\n"
        "def f(m: Any):\n"
        "    return [(dict(m, seen=True), 'out')]\n"
    ))
    assert scan_file(p) == []


def test_a_role_that_will_not_parse_is_not_a_lint_failure(tmp_path):
    """A broken role is the compiler's problem to report. A lint that
    also crashes on it buries the message that would have helped."""
    assert scan_file(_role(tmp_path, "def f(:\n")) == []


# ── what it does to a whole office ────────────────────────────────────


