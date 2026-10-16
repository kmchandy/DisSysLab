"""The one front-matter reader (spec section 4.4).

As for the office parser: unit tests of each rule, and every role shown in
the spec and the nine paper ports must be read without error, so the
documents students copy and the reader cannot drift apart.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dissyslab.office.frontmatter import (
    Conditional,
    Field,
    FrontMatterError,
    parse_front_matter,
    read_front_matter,
)

REPO = Path(__file__).resolve().parents[2]
DESIGN = REPO / "docs" / "internals" / "design"

TOPIC_FILTER = """\
---
emits: whether a news article is on the topic
in: title, text
out: on_topic (yes | no)
---
You read one news article, given as a JSON object.

Return only a JSON object with one field, "on_topic".
"""


def test_an_english_role():
    fm = parse_front_matter(TOPIC_FILTER)
    assert fm.emits == "whether a news article is on the topic"
    assert fm.kind == "annotator" and not fm.is_author
    assert fm.inputs == ("title", "text")
    assert fm.outputs == (Field("on_topic", ("yes", "no")),)
    # The prompt is exactly the text after the block.
    assert fm.body == ("You read one news article, given as a JSON object.\n\n"
                       'Return only a JSON object with one field, "on_topic".\n')


def test_no_front_matter_means_nothing_declared():
    fm = parse_front_matter("Just a prompt.\n")
    assert fm.inputs is None and fm.outputs is None
    assert fm.body == "Just a prompt.\n"


def test_an_author_with_conditional_out_lines():
    fm = parse_front_matter(
        "---\n"
        "kind: author\n"
        "out: next (finish | continue), problem_id, history\n"
        "out if next is finish: final_answer, agreement\n"
        "out if next is continue: round\n"
        "---\n")
    assert fm.is_author
    assert fm.outputs == (Field("next", ("finish", "continue")), Field("problem_id"),
                          Field("history"))
    assert fm.conditionals == (
        Conditional("next", "finish", (Field("final_answer"), Field("agreement"))),
        Conditional("next", "continue", (Field("round"),)),
    )


def test_same_as_in_and_needs():
    fm = parse_front_matter("---\nkind: author\nout: same as in\nneeds: birdnetlib, librosa\n---\n")
    assert fm.same_as_in and fm.outputs is None
    assert fm.needs == ("birdnetlib", "librosa")


def test_values_may_be_any_word():
    fm = parse_front_matter("---\nout: severity (CRITICAL | HIGH), region (north_america | global)\n---\n")
    assert fm.outputs == (Field("severity", ("CRITICAL", "HIGH")),
                          Field("region", ("north_america", "global")))


@pytest.mark.parametrize("block, message", [
    ("outboxes: keeper, discard", "old form; a role has one outbox"),
    ("adds: text", "old form; write the fields under out:"),
    ("AI: claude", "old form; choose the model in the office file"),
    ("ouT: x", None),  # keys are case-insensitive: this one is fine
    ("emitz: x", "unknown key 'emitz:'. Did you mean 'emits:'"),
    ("kind: writer", "kind: is 'author'"),
    ("out: a, a", "listed twice"),
    ("out: a (x | )", "empty value"),
    ("out: next (go | stop)\nout if next is wait: x", "with the value 'wait'"),
    ("in: title, the text", "is not a field name"),
    ("in: a\nin: b", "given twice"),
    ("no colon here", "expected 'key: value'"),
])
def test_errors(block, message):
    text = f"---\n{block}\n---\n"
    if message is None:
        parse_front_matter(text)
        return
    with pytest.raises(FrontMatterError, match=message):
        parse_front_matter(text)


def test_errors_name_the_line():
    with pytest.raises(FrontMatterError) as info:
        parse_front_matter("---\nemits: x\nin: a\nadds: text\n---\n")
    assert info.value.line == 4


def test_an_unclosed_block_is_an_error():
    with pytest.raises(FrontMatterError, match="never ends"):
        parse_front_matter("---\nout: x\n")


def test_a_python_file_is_read_from_its_docstring_without_importing(tmp_path):
    path = tmp_path / "clerk.py"
    path.write_text(
        '"""\n---\nemits: approves small refunds\nin: amount\n'
        'out: clerk_decision (approve | escalate)\n---\nArguments: limit.\n"""\n'
        "raise SystemExit('importing this file would stop the test')\n")
    fm = read_front_matter(path)
    assert fm.inputs == ("amount",)
    assert fm.outputs == (Field("clerk_decision", ("approve", "escalate")),)
    assert fm.body == ""


# ── Every role in the spec and the paper ports is read without error ───────


def _role_blocks():
    fence = re.compile(r"^```(\w*)\n(.*?)^```", re.M | re.S)
    docs = sorted((DESIGN / "officespeak_ports").glob("*.md"))
    docs.append(DESIGN / "officespeak_revised.md")
    for doc in docs:
        # "## Before" sections show the old form on purpose; skip them.
        text = re.sub(r"^## Before\n.*?(?=^## )", "", doc.read_text(encoding="utf-8"),
                      flags=re.M | re.S)
        for lang, block in fence.findall(text):
            if lang == "" and block.startswith("---\n"):
                yield pytest.param(block, id=f"{doc.stem}:md")
            elif lang == "python" and block.startswith('"""\n---\n'):
                doc_text = block.split('"""')[1]
                yield pytest.param(doc_text, id=f"{doc.stem}:py")


ROLES = list(_role_blocks())


def test_the_documents_show_enough_roles():
    assert len(ROLES) >= 10


@pytest.mark.parametrize("block", ROLES)
def test_every_role_in_the_documents_is_read(block):
    fm = parse_front_matter(block)
    assert fm.outputs is not None or fm.same_as_in or fm.emits
