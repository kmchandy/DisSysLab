"""The gallery offices (dissyslab/gallery/), run end to end.

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
import sys
from pathlib import Path

import pytest

from dissyslab.backends import register_backend
from dissyslab.office.build import run_office

EXAMPLES = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"


def copy_example(name: str, tmp_path: Path) -> Path:
    dst = tmp_path / name
    shutil.copytree(EXAMPLES / name, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def record_source(office: Path, name: str, items: list[dict]) -> None:
    """Replace source ``name`` by a file of recorded items, keeping its name."""
    (office / f"{name}.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items),
                                            encoding="utf-8")
    md = office / "office.md"
    text, n = re.subn(rf"^(\s+){name}\b.*$", rf'\g<1>{name}: file_source(path="{name}.jsonl")',
                      md.read_text(encoding="utf-8"), count=1, flags=re.M)
    assert n == 1, f"no source line for {name}"
    md.write_text(text, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


class Scripted:
    def __init__(self, answer):
        self.answer = answer

    def complete(self, *, system, user, max_tokens=1024, temperature=1.0, model=None):
        return self.answer(system, json.loads(user))


@pytest.fixture
def every_model(monkeypatch):
    """Make every model -- whatever ai= names -- a scripted one, for one test."""
    import dissyslab.backends as backends

    def use(answer):
        for name in list(backends._REGISTRY):
            monkeypatch.setitem(backends._REGISTRY, name, lambda: Scripted(answer))
            monkeypatch.delitem(backends._CACHE, name, raising=False)
    return use


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
    # Not in ticket order: a decision reaches the recorder and releases the
    # next ticket (Gate.done) in parallel. Compare by ticket.
    outcomes = sorted(read_jsonl(office / "outcomes.jsonl"), key=lambda o: o["ticket_id"])
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


# ── situation_room_pro ─────────────────────────────────────────────────────


def _analyst(system, m):
    """One scripted model playing all five built-in roles, by prompt."""
    if "named entities" in system:
        return json.dumps({"entities": {"people": [], "organizations": [],
                                        "places": [m["title"].split()[0]], "events": []}})
    if "how significant" in system.lower() or "Decide how significant" in system:
        return json.dumps({"severity": "CRITICAL" if "war" in m["text"] else "LOW"})
    if "Assign it exactly one topic" in system:
        return json.dumps({"topic": "politics"})
    if "where in the world" in system:
        return json.dumps({"location": {"country": "", "region": "global"}})
    if "Write a briefing" in system:
        assert {"severity", "topic", "location", "entities"} <= set(m), m
        return json.dumps({"headline": "Briefly: " + m["title"],
                           "summary": f"{m['title']} ({m['severity']}, {m['topic']})."})
    raise AssertionError(f"unexpected prompt: {system[:60]!r}")


def test_situation_room_pro(tmp_path, model, monkeypatch):
    office = copy_example("situation_room_pro", tmp_path)
    story = {"url": "u1", "title": "Geneva peace talks", "text": "talks resume"}
    record_source(office, "bbc_world", [story, {"url": "u2", "title": "Kyiv war", "text": "war"}])
    record_source(office, "npr_news", [story])  # a repeat: Sasha drops it
    record_source(office, "al_jazeera", [{"url": "u3", "title": "Lima budget", "text": "..."}])
    model(_analyst)
    # Riley's ai="anthropic" must reach the scripted model too, for this
    # test only (monkeypatch restores the real one afterwards).
    import dissyslab.backends as backends
    monkeypatch.setitem(backends._REGISTRY, "anthropic", lambda: Scripted(_analyst))
    monkeypatch.delitem(backends._CACHE, "anthropic", raising=False)
    assert run_office(office) == 0
    briefs = {b["url"]: b for b in read_jsonl(office / "briefings.jsonl")}
    assert sorted(briefs) == ["u1", "u2", "u3"]  # each article once
    assert briefs["u2"]["severity"] == "CRITICAL"
    assert briefs["u2"]["headline"] == "Briefly: Kyiv war"
    assert briefs["u1"]["entities"]["places"] == ["Geneva"]


# ── debate ─────────────────────────────────────────────────────────────────


def _panel_and_moderator(system, m):
    for name in ("qwen", "gpt", "claude"):
        if f"You are { {'qwen': 'Qwen', 'gpt': 'GPT', 'claude': 'Claude'}[name]}," in system:
            # On math-01 round 0, Claude disagrees; everyone agrees otherwise.
            wrong = name == "claude" and m["problem_id"] == "math-01" and m["round"] == 0
            return json.dumps({name: {"answer": "257" if wrong else "A",
                                      "reasoning": "r", "confidence": 0.9}})
    if "You moderate a panel" in system:
        answers = {m[n]["answer"] for n in ("qwen", "gpt", "claude")}
        if len(answers) == 1:
            return json.dumps({"agreement": "unanimous", "final_answer": answers.pop(), "note": ""})
        return json.dumps({"agreement": "none", "final_answer": "A",
                           "note": "Claude, check your multiplication."})
    raise AssertionError(f"unexpected prompt: {system[:60]!r}")


def test_debate(tmp_path, every_model, capsys):
    office = copy_example("debate", tmp_path)
    every_model(_panel_and_moderator)
    assert run_office(office) == 0
    answers = {a["problem_id"]: a for a in read_jsonl(office / "debate_answers.jsonl")}
    assert sorted(answers) == ["fact-01", "math-01", "mcq-01"]
    assert answers["math-01"]["rounds_used"] == 2  # one more round after disagreement
    assert answers["math-01"]["history"][0]["note"] == "Claude, check your multiplication."
    assert answers["fact-01"]["rounds_used"] == 1
    assert all(a["agreement"] == "unanimous" for a in answers.values())
    # The transcript has every round: 3 problems + 1 extra round.
    assert len(read_jsonl(office / "debate_transcript.jsonl")) == 4
    assert "another round. Claude, check your multiplication." in capsys.readouterr().out


# ── arxiv_radar ────────────────────────────────────────────────────────────

ARXIV_ITEM = """<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"><channel>
<title>cs.AI updates on arXiv.org</title>
<item>
  <title>Streaming LLM agents for personal assistants</title>
  <link>https://arxiv.org/abs/2610.00001</link>
  <description>arXiv:2610.00001v1 Announce Type: new
Abstract: We present small language models that process event streams.</description>
  <pubDate>Wed, 14 Oct 2026 00:00:00 -0400</pubDate>
  <dc:creator>A. Patel, M. Garcia</dc:creator>
</item></channel></rss>
"""


def test_the_arxiv_source_gives_abstract_and_authors(monkeypatch):
    """The source as it reads arXiv's RSS feed (recorded, 14 Oct 2026 format)."""
    import feedparser

    from dissyslab.components.sources.arxiv_rss import arxiv_cs_ai

    real_parse = feedparser.parse
    monkeypatch.setattr(feedparser, "parse", lambda url: real_parse(ARXIV_ITEM))
    (paper,) = list(arxiv_cs_ai(max_articles=1).run())
    assert paper["source"] == "arxiv_cs_ai"
    assert paper["title"] == "Streaming LLM agents for personal assistants"
    assert paper["authors"] == "A. Patel, M. Garcia"
    assert paper["abstract"] == "We present small language models that process event streams."
    assert paper["url"] == "https://arxiv.org/abs/2610.00001"
    assert "Abstract: We present" in paper["text"]


def test_arxiv_radar(tmp_path, model, capsys):
    office = copy_example("arxiv_radar", tmp_path)
    paper = {"source": "arxiv_cs_ai", "title": "Streaming LLM agents", "url": "u1",
             "authors": "A. Patel", "abstract": "Small language models on streams.",
             "timestamp": ""}
    record_source(office, "arxiv_cs_ai", [paper])
    record_source(office, "arxiv_cs_lg", [{**paper, "title": "Adam revisited", "url": "u2",
                                           "abstract": "A weight-decay tweak."}])
    record_source(office, "arxiv_cs_cl", [])

    def answer(system, m):
        if "Classify the paper" in system:
            return json.dumps({"paper_type": "SYSTEM"})
        llm = "language models" in m["abstract"]
        return json.dumps({"relevance": "HIGH" if llm else "LOW",
                           "reason": "streams and LLMs" if llm else "none"})

    model(answer)
    assert run_office(office) == 0
    shown = capsys.readouterr().out
    assert "Streaming LLM agents" in shown and "Adam revisited" in shown
    assert "paper_type: SYSTEM" in shown and "reason: streams and LLMs" in shown
    assert "authors: A. Patel" in shown


# ── org_two_office_news ────────────────────────────────────────────────────


def test_org_two_office_news(tmp_path, model, capsys):
    office = copy_example("org_two_office_news", tmp_path)
    record_source(office, "al_jazeera", [{"title": "Brazil floods", "text": "Rivers rise in Brazil."},
                                         {"title": "Gaza talks", "text": "Talks resume."}])
    record_source(office, "bbc_world", [{"title": "Canada election", "text": "Canada votes."}])

    def answer(system, m):
        if "The topic is the Americas" in system:
            return json.dumps({"on_topic": "no" if "Gaza" in m["title"] else "yes"})
        if "one plain sentence" in system:
            return json.dumps({"summary": "In short: " + m["text"]})
        raise AssertionError(system[:60])

    model(answer)
    assert run_office(office) == 0
    shown = capsys.readouterr().out
    assert "In short: Rivers rise in Brazil." in shown and "In short: Canada votes." in shown
    assert "Gaza" not in shown


# ── mac_speed_suite ────────────────────────────────────────────────────────


def _price_history(tickers=("AAA", "BBB", "CCC"), days=320):
    """Deterministic made-up daily bars: a trend, a cycle and some noise."""
    import datetime
    import math
    import random

    rng = random.Random(7)
    start = datetime.date(2024, 1, 1)
    history = {}
    for k, t in enumerate(tickers):
        price, bars = 100.0, []
        for d in range(days):
            price *= 1 + 0.0004 * (k + 1) + 0.01 * math.sin(d / (15 + 5 * k)) + rng.gauss(0, 0.01)
            bars.append({"date": (start + datetime.timedelta(days=d)).isoformat(),
                         "open": price, "high": price * 1.01, "low": price * 0.99,
                         "close": price, "volume": 1000})
        history[t] = bars
    return {"type": "stock_history", "tickers": list(tickers), "history": history}


def test_mac_speed_suite(tmp_path, capsys):
    office = copy_example("mac_speed_suite", tmp_path)
    record_source(office, "prices", [_price_history()])
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8").replace("n_folds=4, n_samples=100", "n_folds=2, n_samples=3"),
                  encoding="utf-8")
    assert run_office(office) == 0
    assert "Scorecard written to report.html" in capsys.readouterr().out
    report = (office / "report.html").read_text(encoding="utf-8")
    for variant in ("MAC · fast", "MAC · slow", "DONCHIAN · 20", "TURTLE · s1", "RS · slow"):
        assert variant in report
    assert "walk-forward: 2 folds" in report and "Monte Carlo: 3 samples" in report


# ── backyard_birds ─────────────────────────────────────────────────────────


def _fake_birdnetlib(folder: Path) -> None:
    """A stand-in BirdNET with the same two names: Analyzer and Recording."""
    pkg = folder / "birdnetlib"
    pkg.mkdir()
    (pkg / "analyzer.py").write_text("class Analyzer:\n    pass\n", encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "HEARD = {'wren.mp3': [{'common_name': 'Carolina Wren',\n"
        "    'scientific_name': 'Thryothorus ludovicianus', 'confidence': 0.87,\n"
        "    'start_time': 12.0, 'end_time': 15.0}]}\n"
        "class Recording:\n"
        "    def __init__(self, analyzer, path, min_conf):\n"
        "        self.path = path\n"
        "    def analyze(self):\n"
        "        import os\n"
        "        self.detections = HEARD.get(os.path.basename(self.path), [])\n",
        encoding="utf-8")
    for name in ("librosa", "resampy"):
        (folder / f"{name}.py").write_text("", encoding="utf-8")


def test_backyard_birds(tmp_path, monkeypatch, capsys):
    office = copy_example("backyard_birds", tmp_path)
    for clip in ("wren.mp3", "quiet.mp3"):
        (office / "samples" / clip).write_bytes(b"")
    fakes = tmp_path / "fakes"
    fakes.mkdir()
    _fake_birdnetlib(fakes)
    monkeypatch.syspath_prepend(str(fakes))
    try:
        assert run_office(office) == 0
    finally:  # forget the stand-ins, so no later test imports them
        for name in ("birdnetlib", "birdnetlib.analyzer", "librosa", "resampy"):
            sys.modules.pop(name, None)
    heard = {d["file"]: d for d in read_jsonl(office / "bird_detections.jsonl")}
    assert heard["wren.mp3"]["species"] == "Carolina Wren"
    assert heard["wren.mp3"]["level"] == "HIGH"
    assert heard["quiet.mp3"]["found"] == "no"
    assert "species" not in heard["quiet.mp3"]


def test_backyard_birds_without_birdnet_stops_before_starting(tmp_path):
    import importlib.util

    if importlib.util.find_spec("birdnetlib"):
        pytest.skip("birdnetlib is installed here")
    office = copy_example("backyard_birds", tmp_path)
    with pytest.raises(Exception, match="pip install"):
        run_office(office)


# ── Every data file an office reads is in the repository ───────────────────


def test_every_file_a_gallery_office_reads_is_tracked_by_git():
    """A file on this disk but not in git passes every other test here and
    fails in CI and for every student. It happened: a blanket `*.jsonl`
    ignore rule kept the gallery's input files out of the Phase 6a commit.
    """
    import subprocess

    repo = EXAMPLES.parents[1]
    if not (repo / ".git").exists():
        pytest.skip("not a git checkout")
    tracked = set(subprocess.run(
        ["git", "ls-files", "dissyslab/gallery"], cwd=repo,
        capture_output=True, text=True, check=True).stdout.split())
    read = []
    for md in EXAMPLES.rglob("office.md"):
        for path in re.findall(r'file_source\(path="([^"]+)"\)', md.read_text(encoding="utf-8")):
            read.append((md.parent / path).relative_to(repo).as_posix())
    assert read, "found no file_source in the gallery: is this test still looking?"
    untracked = sorted(p for p in read if p not in tracked)
    assert not untracked, (
        f"gallery offices read files that are not in git: {untracked}. "
        "Check .gitignore (`git check-ignore -v <file>`), then `git add` them."
    )


# ── inbox_sorter ───────────────────────────────────────────────────────────


def test_inbox_sorter(tmp_path, model):
    office = copy_example("inbox_sorter", tmp_path)

    def answer(system, m):
        assert "Decide how soon it needs an answer" in system
        due = "due" in m["text"] and ("tomorrow" in m["text"] or "hours" in m["text"])
        return json.dumps({"urgency": "urgent" if due else "routine"})

    model(answer)
    assert run_office(office) == 0
    urgent = [m["id"] for m in read_jsonl(office / "urgent.jsonl")]
    later = [m["id"] for m in read_jsonl(office / "later.jsonl")]
    assert sorted(urgent) == [1, 3] and sorted(later) == [2, 4]
