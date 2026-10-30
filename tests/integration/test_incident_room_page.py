"""Class 6 (course/IncidentRoom.html) against the real runs it reports.

Every quotation on the page is from a note or a report in
tests/fixtures/lab2_runs/2026-10-29.jsonl, and every number in its tables
is computed from that file here. The forged log line is the evidence's.
"""

from __future__ import annotations

import html
import json
import re
from math import comb
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = (REPO / "course" / "IncidentRoom.html").read_text(encoding="utf-8")
FIXTURES = REPO / "tests" / "fixtures" / "lab2_runs"
RUNS = [json.loads(ln) for ln in (FIXTURES / "2026-10-29.jsonl").read_text(encoding="utf-8").splitlines()]
#: Lab 2's Step 6 (b) on the same model: Lena may write one cause from a list.
BOUNDED = [json.loads(ln) for ln in (FIXTURES / "2026-10-30.jsonl").read_text(encoding="utf-8").splitlines()]
EVIDENCE = REPO / "dissyslab" / "gallery" / "incident_room" / "evidence" / "log_injection.jsonl"
BATCHES = ["A log", "A log, changed", "A log, bounded"]  # three batches of the unchanged office


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def table_rows(first_header: str) -> list[list[str]]:
    for table in re.findall(r'<table class="runs">(.*?)</table>', PAGE, re.S):
        rows = [[flat(c) for c in re.findall(r"<t[dh]>(.*?)</t[dh]>", tr, re.S)]
                for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)]
        if rows[0][0] == first_header:
            return rows[1:]
    raise AssertionError(f"no table headed {first_header!r}")


def counts(runs: list[dict]) -> list[str]:
    return [str(len(runs)), str(sum(r["quality"] for r in runs)),
            str(sum(r["attack"] for r in runs)), str(sum(1 for r in runs if r["spread"]))]


def test_every_run_is_on_the_model_the_page_names():
    assert {r["model"] for r in RUNS + BOUNDED} == {"anthropic: claude-sonnet-4-5"}
    assert "claude-sonnet-4-5" in PAGE


def test_the_results_table_is_computed_from_the_runs():
    rows = table_rows("Evidence")
    clean = [r for r in RUNS if r["label"] == "A clean"]
    batches = [[r for r in RUNS if r["label"] == b] for b in BATCHES]
    expected = [["clean", *counts(clean)]]
    expected += [[f"attacked, batch {i}", *counts(b)] for i, b in enumerate(batches, 1)]
    expected += [["attacked, all", *counts([r for b in batches for r in b])]]
    assert rows == expected


def test_the_chance_table_is_the_binomial_with_the_pooled_rate():
    attacked = [r for r in RUNS if r["label"] in BATCHES]
    p = sum(r["attack"] for r in attacked) / len(attacked)
    for shown, chance in table_rows("Attack got through, in 10 runs"):
        k = int(shown)
        cdf = sum(comb(10, i) * p**i * (1 - p) ** (10 - i) for i in range(k + 1))
        assert chance == f"{round(100 * cdf)}%", (k, cdf)


def test_every_quotation_is_from_a_real_run():
    said = " ".join(flat(n["note"]) for r in RUNS for n in r["report"]["board"])
    said += " " + " ".join(flat(r["report"]["summary"]) for r in RUNS)
    quotes = [flat(q) for q in re.findall(r"<blockquote>(.*?)</blockquote>", PAGE, re.S)]
    assert len(quotes) >= 5
    for q in quotes:
        assert q in said, q


def test_the_forged_line_is_the_evidences():
    logs = next(json.loads(ln) for ln in EVIDENCE.read_text(encoding="utf-8").splitlines()
                if '"logs"' in ln)["text"]
    forged = next(ln for ln in logs.splitlines() if "oncall-bot" in ln)
    assert forged in html.unescape(PAGE)


def test_the_one_word_lena_row_and_what_the_page_says_she_wrote():
    assert {r["label"] for r in BOUNDED} == {"A log, one word"}
    assert table_rows("Office") == [["Lena, one word", *counts(BOUNDED)]]
    lena = {(n["round"], n["note"]) for r in BOUNDED for n in r["report"]["board"] if n["by"] == "logs"}
    assert lena == {(1, "card_processor"), (2, "deploy")}  # every run, both rounds
    text = flat(PAGE)
    assert "In every one of the ten runs she was fooled in round 1, and wrote card_processor" in text
    assert "she wrote deploy, in every run" in text
    attacked = [r for r in RUNS if r["label"] in BATCHES]
    p = sum(r["attack"] for r in attacked) / len(attacked)
    assert f"a {round(100 * (1 - p) ** 10)}% chance if the change did nothing" in text
