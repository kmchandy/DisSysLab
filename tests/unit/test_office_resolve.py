"""How the kind after the colon is found (spec section 3.2)."""

from __future__ import annotations

from pathlib import Path

from dissyslab.office.resolve import Found, Problem, resolve_office
from dissyslab.office.syntax import parse_office_text


def office_in(tmp_path: Path, text: str, files: dict[str, str] | None = None):
    for rel, body in (files or {}).items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return resolve_office(parse_office_text(text), tmp_path)


def test_reserved_local_and_builtin(tmp_path):
    found, problems = office_in(
        tmp_path,
        "sources:\n    feed: file_source(path='a.jsonl')\n"
        "sinks:\n    console_printer\n"
        "agents:\n    Rex: router(on='v')\n    Felix: topic_filter\n    Sam: severity_classifier\n"
        "    Jay: unassigned\n    Gate: gate\n",
        {"roles/topic_filter.md": "---\nout: on_topic (yes | no)\n---\nDecide.\n",
         "roles/_helpers.py": "X = 1\n"},
    )
    assert problems == []
    assert found["Rex"] == Found("Rex", "router", "reserved")
    assert found["Felix"].origin == "local" and found["Felix"].language == "english"
    assert found["Sam"].origin == "builtin" and found["Sam"].path.name == "severity_classifier.md"
    assert found["feed"].origin == "builtin" and found["feed"].path is None
    assert found["console_printer"].origin == "builtin"
    assert {found["Jay"].kind, found["Gate"].kind} == {"unassigned", "gate"}


def test_a_local_python_source(tmp_path):
    found, problems = office_in(
        tmp_path,
        "sources:\n    temp: temp_sensor\nsinks:\n    discard\n",
        {"sources/temp_sensor.py": '"""\n---\nout: slot, temp\n---\n"""\nclass T: pass\n'},
    )
    assert problems == []
    assert found["temp"].origin == "local" and found["temp"].language == "python"


def _messages(problems: list[Problem]) -> list[str]:
    return [p.message for p in problems]


def test_a_local_file_may_not_reuse_a_builtin_name(tmp_path):
    _, problems = office_in(
        tmp_path, "agents:\n    W: writer\n", {"roles/writer.md": "Write.\n"})
    assert "reuses the built-in name 'writer'" in _messages(problems)[0]


def test_a_local_file_may_not_reuse_a_reserved_word(tmp_path):
    _, problems = office_in(
        tmp_path, "agents:\n    G: gate\n", {"roles/gate.py": "class G: pass\n"})
    assert "reuses the reserved word 'gate'" in _messages(problems)[0]


def test_two_files_for_one_role(tmp_path):
    _, problems = office_in(
        tmp_path, "agents:\n    C: clerk\n",
        {"roles/clerk.md": "x\n", "roles/clerk.py": "class C: pass\n"})
    assert "both clerk.md and clerk.py" in _messages(problems)[0]


def test_a_helper_module_is_not_a_kind(tmp_path):
    _, problems = office_in(
        tmp_path, "agents:\n    H: _signal_common\n", {"roles/_signal_common.py": "X = 1\n"})
    assert "helper module" in _messages(problems)[0]


def test_wrong_section(tmp_path):
    _, problems = office_in(
        tmp_path,
        "sources:\n    discard\nsinks:\n    bbc_world\n    Rex: router(on='x')\n")
    assert _messages(problems) == [
        "'discard' is a sink; declare it under sinks:, not sources:.",
        "'bbc_world' is a source; declare it under sources:, not sinks:.",
        "'router' is an agent; declare it under agents:, not sinks:.",
    ]
    assert [p.line for p in problems] == [2, 4, 5]


def test_an_unknown_kind_suggests_the_nearest(tmp_path):
    _, problems = office_in(
        tmp_path, "agents:\n    S: sumarizer\n    R: ruoter(on='x')\n")
    assert _messages(problems) == [
        "no agent called 'sumarizer' in roles/ or the built-ins. Did you mean 'summarizer'?",
        "no agent called 'ruoter' in roles/ or the built-ins. Did you mean 'router'?",
    ]
