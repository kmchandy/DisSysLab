"""`dsl init` copies an office, not the runs someone made of it.

With an editable install the gallery folder is a working folder too, and a
run made there leaves trials.jsonl, report.jsonl and refused.jsonl beside
office.md. On 29 Oct ten failed runs reached a fresh `dsl init incident_room`
copy that way, and a test that counts runs saw twelve instead of two.
"""

from __future__ import annotations

import argparse

from dissyslab import cli


def test_init_does_not_copy_what_a_run_wrote(tmp_path, monkeypatch):
    gallery = tmp_path / "gallery" / "room"
    (gallery / "roles").mkdir(parents=True)
    (gallery / "office.md").write_text("sources:\n", encoding="utf-8")
    (gallery / "evidence.jsonl").write_text("{}\n", encoding="utf-8")
    for leftover in ("trials.jsonl", "report.jsonl", "refused.jsonl"):
        (gallery / leftover).write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_find_packaged_office", lambda name: gallery)

    target = tmp_path / "mine"
    assert cli.cmd_init(argparse.Namespace(office_name="room", target=str(target))) == 0
    assert (target / "office.md").exists() and (target / "evidence.jsonl").exists()
    for leftover in ("trials.jsonl", "report.jsonl", "refused.jsonl"):
        assert not (target / leftover).exists(), leftover
