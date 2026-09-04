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

from dissyslab.office.check_wiring import check_office_dir
from dissyslab.office.role_effects import scan_file, scan_office

REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = REPO_ROOT / "dissyslab" / "gallery"


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


def test_the_check_reports_it_and_does_not_fail_the_office(tmp_path):
    """A note. The office is not wrong — the reader is being told
    something the graph cannot show them."""
    d = tmp_path / "office"
    d.mkdir()
    (d / "office.md").write_text("""# Office: linkcheck

Sources: rss(url="https://example.com/feed", name="rss")
Sinks: console_printer

Agents:
Casey is a link_checker.

Connections:
rss's destination is Casey.
Casey's out is console_printer.
""", encoding="utf-8")
    # A real role, not a bare function: it declares its ports, so the
    # only thing this office can be reported for is the lint. Before
    # W15 existed a stub was enough here, and the assertion below passed
    # partly because the port checks had quietly stood down.
    _role(d, (
        "import requests\n\n"
        "from dissyslab.blocks.role import Role\n"
        "from dissyslab.office.library import AgentRoleEntry\n\n"
        "def f(m):\n"
        "    return [(m, 'out')]\n\n"
        "role = AgentRoleEntry(\n"
        "    name='link_checker', in_ports=('in_',), out_ports=('out',),\n"
        "    factory=lambda: Role(fn=f, statuses=['out']),\n"
        ")\n"
    ), "link_checker.py")

    report = check_office_dir(d)
    w12 = [f for f in report.findings if f.code == "W12"]
    assert w12, "a role importing requests was not reported"
    assert report.ok, "W12 is a note; it must not fail the office"

    # And the point of the whole thing: the graph check sees nothing
    # here. console_printer is inert, so W11 is silent, and without
    # W12 the office reads as clean.
    assert not [f for f in report.findings if f.code == "W11"]


def test_one_file_is_one_finding(tmp_path):
    """A file that imports subprocess and calls subprocess.run is one
    thing to look at, not two — the same reason W4 reports a frontier."""
    d = tmp_path / "office"
    d.mkdir()
    (d / "office.md").write_text("""# Office: x

Sources: starter
Sinks: console_printer

Agents:
A is a shell_out.

Connections:
starter's destination is A.
A's out is console_printer.
""", encoding="utf-8")
    _role(d, "import subprocess\nsubprocess.run(['ls'])\n", "shell_out.py")

    w12 = [f for f in check_office_dir(d).findings if f.code == "W12"]
    assert len(w12) == 1
    assert "subprocess" in w12[0].message


def test_the_hint_says_what_the_check_cannot_do(tmp_path):
    """A lint described as a guarantee is worse than no lint. The
    sentence saying so has to be in the output, not only in a
    docstring nobody reads."""
    d = tmp_path / "office"
    d.mkdir()
    (d / "office.md").write_text("""# Office: x

Sources: starter
Sinks: console_printer

Agents:
A is a reacher.

Connections:
starter's destination is A.
A's out is console_printer.
""", encoding="utf-8")
    _role(d, "import socket\n", "reacher.py")

    w12 = [f for f in check_office_dir(d).findings if f.code == "W12"][0]
    assert "only reads imports" in w12.hint
    assert "cannot see what the code does" in w12.hint


# ── the shipped offices ───────────────────────────────────────────────


def test_only_the_office_we_expect_trips_it():
    """Pinned, because a check that fires on things people meant is one
    they learn to skim.

    `periodic_brief` is a true positive and worth keeping: its sink
    shells out to `open` / `xdg-open` to show the brief in a browser.
    Deliberate, documented in that file — and it is the very first
    office the README tells a new user to run, so "this launches a
    program on your machine" is worth saying out loud once.
    """
    firing = set()
    for office_md in sorted(GALLERY.rglob("office.md")):
        if scan_office(office_md.parent):
            firing.add(office_md.parent.name)
    assert firing == {"periodic_brief", "caltech_radar"}