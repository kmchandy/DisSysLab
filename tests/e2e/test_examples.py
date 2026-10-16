"""The 2.0 examples (dissyslab/office_examples/), run end to end.

Each test copies an example into a temporary folder (running it writes
output files) and runs it with ``run_office``, the new path. Where an
example reads the network, its sources are replaced by recorded data
with the same names, so the connections are untouched: only the
declaration line changes, which is the point the examples make about
stand-in and real sources (spec section 7). Language models are scripted.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from dissyslab.backends import register_backend
from dissyslab.office.build import run_office

EXAMPLES = Path(__file__).resolve().parents[2] / "dissyslab" / "office_examples"


def copy_example(name: str, tmp_path: Path) -> Path:
    dst = tmp_path / name
    shutil.copytree(EXAMPLES / name, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def record_source(office: Path, name: str, items: list[dict]) -> None:
    """Replace source ``name`` by a file of recorded items, keeping its name."""
    (office / f"{name}.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    md = office / "office.md"
    text, n = re.subn(rf"^(\s+){name}\b.*$", rf'\g<1>{name}: file_source(path="{name}.jsonl")',
                      md.read_text(), count=1, flags=re.M)
    assert n == 1, f"no source line for {name}"
    md.write_text(text)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


class Scripted:
    def __init__(self, answer):
        self.answer = answer

    def complete(self, *, system, user, max_tokens=1024, temperature=1.0, model=None):
        return self.answer(system, json.loads(user))


@pytest.fixture
def model(monkeypatch):
    """Make the default model a scripted one: ``model(answer)``."""
    def use(answer):
        register_backend("examples_test", lambda: Scripted(answer))
        monkeypatch.setenv("DSL_BACKEND", "examples_test")
    return use


# ── org_news_filter ────────────────────────────────────────────────────────


def test_org_news_filter(tmp_path, model, capsys):
    office = copy_example("org_news_filter", tmp_path)
    record_source(office, "al_jazeera", [{"title": "Gaza talks", "text": "..."},
                                         {"title": "Brazil floods", "text": "..."}])
    record_source(office, "bbc_world", [{"title": "Canada election", "text": "..."}])
    americas = ("Brazil", "Canada", "Mexico")
    model(lambda system, m: json.dumps(
        {"on_topic": "yes" if any(w in m["title"] for w in americas) else "no"}))
    assert run_office(office) == 0
    printed = capsys.readouterr().out
    assert "Brazil floods" in printed and "Canada election" in printed
    assert "Gaza talks" not in printed


# ── returns_desk ───────────────────────────────────────────────────────────


def test_returns_desk(tmp_path):
    office = copy_example("returns_desk", tmp_path)
    assert run_office(office) == 0
    outcomes = read_jsonl(office / "outcomes.jsonl")
    assert [o["ticket_id"] for o in outcomes] == ["T1", "T2", "T3", "T4"]
    assert [(o["clerk_decision"], o.get("manager_decision")) for o in outcomes] == [
        ("approve", None), ("escalate", "approve"), ("approve", None), ("escalate", "approve")]


# ── room_climate_monitor ───────────────────────────────────────────────────


def test_room_climate_monitor(tmp_path, capsys):
    office = copy_example("room_climate_monitor", tmp_path)
    assert run_office(office) == 0
    alerts = [line for line in capsys.readouterr().out.splitlines() if "'alert': 'yes'" in line]
    assert [("10:01" in a, "10:03" in a) for a in alerts] in (
        [(True, False), (False, True)], [(False, True), (True, False)])


# ── Every example explains itself ──────────────────────────────────────────


@pytest.mark.parametrize("name", sorted(
    p.name for p in EXAMPLES.iterdir() if (p / "office.md").is_file()))
def test_every_example_has_a_readme(name):
    assert (EXAMPLES / name / "README.md").is_file()
