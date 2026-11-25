"""Class 13 (course/AgentsThatAct.html), sections 6 and 7: every quotation
from a published account names a source that the page links to.

A test cannot fetch the sources. It can make sure no quotation appears
without one, and that the list below is updated with the page. Check the
wording against the source by hand when adding a quotation.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = (REPO / "course" / "AgentsThatAct.html").read_text(encoding="utf-8")
START, END = PAGE.index("<h2>6 &middot;"), PAGE.index("<h2>8 &middot; Questions")
INCIDENTS = PAGE[START:END]

OUTSIDE = {
    "All evidence suggests that the models were hyperfocused on finding a solution "
    "for ExploitGym, going to extreme lengths to achieve a rather narrow testing goal.":
        "https://openai.com/index/hugging-face-model-evaluation-security-incident/",
    "closer to a harness and operational failure than a model alignment failure":
        "https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals",
    "we should have avoided making such strong claims about what Claude believed":
        "https://www.anthropic.com/research/alignment-assessment-cybersecurity-incidents",
    "the model's reasoning persuaded the monitor that the environment was simulated":
        "https://www.anthropic.com/research/alignment-assessment-cybersecurity-incidents",
}


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def test_every_quotation_in_sections_6_and_7_has_a_linked_source():
    quotes = [flat(q) for q in re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", INCIDENTS, re.S)]
    assert sorted(quotes) == sorted(OUTSIDE)
    for url in OUTSIDE.values():
        assert f'href="{url}"' in PAGE, url


def test_section_7_links_a_source_for_every_study():
    section = PAGE[PAGE.index("<h2>7 &middot;"):END]
    for study in ["2505.23836", "detecting-and-reducing-scheming", "2509.15541",
                  "agentic-misalignment", "2412.04984"]:
        assert study in section, study
    assert all(u.startswith("https://") for u in re.findall(r'href="([^"]+)"', section))
