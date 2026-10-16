"""The guardrail notes of ``dsl check`` (dissyslab.office.check).

Guardrails are recommended, never required (spec, principle 6): each of
these is a note, and the office still checks clean.
"""

from __future__ import annotations

from pathlib import Path

from dissyslab.office.check import check_office


def write(folder: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text, encoding="utf-8")
    return folder


SUMMARIZER = "---\nin: title\nout: summary\n---\nSummarize the article in one sentence.\n"


def test_news_reaching_email_is_a_note(tmp_path):
    office = write(tmp_path / "mailer", {
        "office.md": (
            "sources:\n    bbc_world\n"
            "sinks:\n    gmail_sink(to=\"me@example.com\")\n    console_printer\n"
            "agents:\n    Sam: brief\n"
            "connections:\n    bbc_world -> Sam -> gmail_sink, console_printer\n"),
        "roles/brief.md": SUMMARIZER,
    })
    report = check_office(office)
    assert report.ok, report.problems
    (note,) = report.notes
    assert note.startswith("line 4: text from bbc_world can reach gmail_sink, which sends email.")
    assert "declared in out:" in note


def test_no_note_when_the_acting_sink_is_not_reachable(tmp_path):
    office = write(tmp_path / "split", {
        "office.md": (
            "sources:\n    bbc_world\n    items: file_source(path=\"items.jsonl\")\n"
            "sinks:\n    gmail_sink(to=\"me@example.com\")\n    console_printer\n"
            "connections:\n    bbc_world -> console_printer\n    items -> gmail_sink\n"),
        "items.jsonl": "{}\n",
    })
    assert check_office(office).notes == []


def test_python_that_reaches_the_network_is_a_note(tmp_path):
    office = write(tmp_path / "fetcher", {
        "office.md": (
            "sources:\n    items: file_source(path=\"items.jsonl\")\n"
            "sinks:\n    console_printer\n"
            "agents:\n    F: fetch\n"
            "connections:\n    items -> F -> console_printer\n"),
        "roles/fetch.py": (
            '"""\n---\nin: url\nout: page\n---\n"""\nimport requests\n\n\n'
            "class Fetch:\n    def __call__(self, item):\n"
            "        return {\"page\": requests.get(item[\"url\"]).text}\n"),
        "items.jsonl": "{}\n",
    })
    report = check_office(office)
    assert report.ok, report.problems
    (note,) = report.notes
    assert note.startswith("line 6: roles/fetch.py imports `requests`.")


def test_the_gallery_offices_raise_no_guardrail_notes():
    gallery = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"
    for office in sorted(p.parent for p in gallery.glob("*/office.md")):
        assert check_office(office).notes == [], office.name


def test_a_long_path_is_still_found(tmp_path):
    office = write(tmp_path / "long", {
        "office.md": (
            "sources:\n    hacker_news\n"
            "sinks:\n    slack_sink(channel=\"#x\")\n"
            "agents:\n    A: brief\n    B: brief2\n    C: brief3\n"
            "connections:\n    hacker_news -> A -> B -> C -> slack_sink\n"),
        "roles/brief.md": SUMMARIZER,
        "roles/brief2.md": SUMMARIZER,
        "roles/brief3.md": SUMMARIZER,
    })
    (note,) = check_office(office).notes
    assert "text from hacker_news can reach slack_sink, which posts to Slack." in note


def test_a_trusted_source_or_an_inert_sink_is_not_reported(tmp_path):
    office = write(tmp_path / "quiet", {
        "office.md": (
            "sources:\n    bbc_world\n    items: file_source(path=\"items.jsonl\")\n"
            "sinks:\n    jsonl_recorder(path=\"out.jsonl\")\n    gmail_sink(to=\"me@example.com\")\n"
            "connections:\n    bbc_world -> jsonl_recorder\n    items -> gmail_sink\n"),
        "items.jsonl": "{}\n",
    })
    assert check_office(office).notes == []
