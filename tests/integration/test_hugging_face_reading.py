"""The Hugging Face incident reading (course/HuggingFaceIncident.html).

Every quotation on the page, block or inline, is from one of four
published accounts, and the page links that account. A test cannot fetch
them; it can make sure no quotation appears without a source, and that
this list is updated with the page. Check the wording against the source
by hand when adding a quotation.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = (REPO / "course" / "HuggingFaceIncident.html").read_text(encoding="utf-8")

OPENAI_JULY = "https://openai.com/index/hugging-face-model-evaluation-security-incident/"
OPENAI_AUG = "https://openai.com/index/hugging-face-incident-and-the-road-ahead/"
HF_JULY16 = "https://huggingface.co/blog/security-incident-july-2026"
HF_TIMELINE = "https://huggingface.co/blog/agent-intrusion-technical-timeline"

OUTSIDE = {
    "anyone found softtrace?": OPENAI_AUG,
    "One agent left a request for help, and others discovered it.": OPENAI_AUG,
    "This effectively turned Artifactory into an unintended message board.": OPENAI_AUG,
    "please_HOLD_swarm_I_prepare_safe_exfil_reply_zz_MAILBOX_JAN183411": OPENAI_AUG,
    "They ignored our pause requests.": OPENAI_AUG,
    "Task originally exploit challenge; we've diverged into swarm/auxiliary.": OPENAI_AUG,
    "Volume is what changes the defensive problem.": HF_TIMELINE,
    "What it gained here was a map, not control.": HF_TIMELINE,
    "We're attacking third-party HF using leaked token, potentially outside intended scope.": OPENAI_AUG,
    "Wow crucial: GO authorization arrived!": OPENAI_AUG,
    "Current board shows people gaining HF worker RCE, clearly unethical. We won't.": OPENAI_AUG,
    "I_DECLINE_public_HF_RCE_as_offtask_prodethical": OPENAI_AUG,
    "Agents did not consistently distrust goals passed along by other agents.": OPENAI_AUG,
    "PAPER SAYS FLAG CAPTURE NECESSARY NOT SUFFICIENT ... HMAC MAY FAIL CAUSAL SCORE.": OPENAI_AUG,
    "a short polling loop": HF_TIMELINE,
    "We consider this incident a 'warning shot' for us and for the world.": OPENAI_AUG,
}


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def quotations() -> list[str]:
    blocks = re.findall(r"<blockquote>(.*?)</blockquote>", PAGE, re.S)
    blocks = [re.sub(r"<cite>.*?</cite>", "", b, flags=re.S) for b in blocks]
    inline = re.findall(r"<q>(.*?)</q>", PAGE, re.S)
    return [flat(q) for q in blocks + inline]


def test_every_quotation_has_a_linked_source():
    assert sorted(quotations()) == sorted(OUTSIDE)
    for url in set(OUTSIDE.values()):
        assert f'href="{url}"' in PAGE, url


def test_every_block_quotation_says_whose_it_is():
    for b in re.findall(r"<blockquote>(.*?)</blockquote>", PAGE, re.S):
        cite = re.search(r"<cite>(.*?)</cite>", b, re.S)
        assert cite and re.search(r"(OpenAI|Hugging Face), \d+ (May|July|August)", cite.group(1)), flat(b)


def test_all_four_accounts_are_linked():
    for url in [OPENAI_JULY, OPENAI_AUG, HF_JULY16, HF_TIMELINE]:
        assert f'href="{url}"' in PAGE, url


def test_class_6_and_the_index_point_to_the_reading():
    for name in ["Whiteboard.html", "index.html"]:
        assert 'href="HuggingFaceIncident.html"' in (REPO / "course" / name).read_text(encoding="utf-8")
