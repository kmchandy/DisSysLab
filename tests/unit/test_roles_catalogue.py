"""Every role says what it adds to a message.

Nothing could list the role library and nothing said what a role
*emits*, so an assistant asked "what roles are there?" read the
thirteen prompt files and paraphrased — afresh every time, so no two
students were told the same thing about `summarizer`.

The emitted field is the fact a user needs. An agent wired downstream
of `severity_classifier` reads `severity`; someone told only that the
role "decides how significant an article is" wires the next agent
blind and meets the mismatch at run time.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dissyslab.office._internals import _builtin_roles_dir
from dissyslab.office.library import load_roles_dir
from dissyslab.roles_catalogue import (
    builtin_roles_dir,
    catalogue,
    format_catalogue,
    read_role,
    strip_front_matter,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_every_shipped_role_says_what_it_emits():
    """The check that keeps this true as roles are added. A role with
    no `emits:` line is one an assistant will describe by improvising
    from the prompt, which is the situation this replaced."""
    silent = [r.name for r in catalogue() if not r.emits.strip()]
    assert not silent, (
        f"{silent} have no `emits:` line. Add one to the front matter "
        "of the role file — one sentence saying what field the role "
        "adds, because that is what someone wiring the next agent "
        "needs to know."
    )


def test_the_catalogue_covers_the_whole_directory():
    on_disk = {
        p.stem for p in builtin_roles_dir().iterdir()
        if p.suffix in (".md", ".py")
        and not p.name.startswith("_")
        and p.stem.lower() != "readme"
    }
    assert {r.name for r in catalogue()} == on_disk


# ── the front matter must never reach the model ───────────────────────


def test_front_matter_does_not_reach_the_prompt():
    """These files are prompts. Metadata leaking into one changes
    behaviour subtly and is never noticed, so assert it explicitly
    rather than trusting that the loader still strips it."""
    library = load_roles_dir(_builtin_roles_dir())
    for name, entry in library.items():
        text = repr(entry)
        assert "emits:" not in text, (
            f"the role catalogue's front matter is inside {name}'s "
            "prompt. A language model is now reading our metadata."
        )


def test_the_loader_and_the_catalogue_read_the_same_format():
    """Two parsers of one format is the shape that drifts. The loader
    has its own front-matter reader (it predates this one, for
    `contract:` and `AI:`); pin them to the same answer."""
    from dissyslab.office.library import _extract_role_front_matter

    sample = (
        "---\n"
        "emits: adds a `topic` field\n"
        "AI: ollama\n"
        "---\n"
        "You read one item at a time.\n"
    )
    mine_meta, mine_body = strip_front_matter(sample)
    theirs_meta, theirs_body = _extract_role_front_matter(sample)

    # Compared stripped: the two differ by a trailing newline, which
    # is not a difference either caller can observe.
    assert mine_body.strip() == theirs_body.strip()
    assert mine_meta["emits"] == theirs_meta["emits"]
    assert mine_meta["AI"] == theirs_meta["AI"]


def test_a_file_with_no_front_matter_is_returned_whole():
    meta, body = strip_front_matter("You read one item at a time.\n")
    assert meta == {}
    assert body == "You read one item at a time.\n"


# ── what it says ──────────────────────────────────────────────────────


def test_outboxes_agree_with_what_the_framework_wires():
    """The catalogue extracts outboxes by the same `send to <name>`
    rule the framework uses. Pin them together rather than asserting a
    hardcoded list: the order decides which outbox is `out_0`, and a
    catalogue that disagreed about that would be worse than none.

    This caught a real difference. The first version matched a literal
    space, so "send to\nkeep" — a wrapped line, the common case — was
    missed, and the catalogue quietly reported one outbox where the
    office wires two."""
    library = load_roles_dir(_builtin_roles_dir())
    for role in catalogue():
        entry = library.get(role.name)
        theirs = getattr(entry, "out_ports", None)
        if theirs is None:
            continue
        assert role.outboxes == tuple(theirs), (
            f"{role.name}: catalogue says {role.outboxes}, the "
            f"framework wires {tuple(theirs)}"
        )


def test_a_python_role_is_marked_as_costing_nothing():
    by_name = {r.name: r for r in catalogue()}
    assert by_name["confidence_filter"].kind == "python"
    assert not by_name["confidence_filter"].costs_money
    assert by_name["summarizer"].costs_money


def test_the_listing_names_the_branching_roles(tmp_path):
    """A filter's two outboxes, in the order the role declares them.

    The order was hard-coded here as "discard or keep" and had to change
    when `relevance_filter`'s declaration was corrected -- which is the
    wrong way round: a test should not have to be edited because the
    data it describes was wrong. It reads the declaration now, so the
    listing and the role cannot drift apart and this cannot be the thing
    that has to be updated.
    """
    from dissyslab.office.role_ports import read_ports

    text = format_catalogue(catalogue())
    declared = read_ports(builtin_roles_dir() / "relevance_filter.md").outboxes
    assert f"sends to {' or '.join(declared)}" in text
    assert "Python, costs nothing to run" in text
    # and it tells the reader what to do when none of them fit
    assert "write the role from your words" in text


def test_an_unreadable_directory_is_not_a_crash(tmp_path):
    assert catalogue(tmp_path / "nothing-here") == []


def test_readme_is_not_a_role():
    assert read_role(builtin_roles_dir() / "README.md") is None


# ── the subcommand ────────────────────────────────────────────────────


def test_dsl_roles_runs_and_lists_them():
    out = subprocess.run(
        [sys.executable, "-m", "dissyslab.cli", "roles"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert out.returncode == 0
    assert "summarizer" in out.stdout
    # The field name comes from the declaration, not from the emits
    # sentence -- which used to say it too, so the listing printed
    # every field twice and could disagree with itself.
    assert "adds summary" in out.stdout


# ── the first outbox is the fallback, so it has to be the one the
#    role's own prose promises ──────────────────────────────────────────


def test_a_role_that_names_a_fallback_declares_it_first():
    """`out_ports[0]` is where a message goes when the model does not
    choose, so a role that says "when in doubt, send to keep" and
    declares `outboxes: discard, keep` does the opposite of what it says.

    That was live in `relevance_filter` and it was caused by a line
    wrap. The framework used to build the ports by scanning each line
    for `send to <name>`, and the sentence that mattered wrapped:

        Your job. Decide whether the item is relevant. If relevant, send to
        keep. If not, send to discard.

    The first line has `send to` and no name after it; the second has
    `send to discard`. So `discard` was found first, became
    `out_ports[0]`, and an item the model did not classify was silently
    thrown away -- by a role whose own text says, twice, that
    discarding a borderline item is the worse mistake. For a filter,
    that is data loss you cannot see and cannot recover.

    Ports are declared now, which stops the wrap deciding anything. It
    does not by itself stop a declaration disagreeing with the prose
    beside it, and the migration that introduced the declarations could
    not have caught this: it checked that each declaration matched what
    the scan produced, which is the wrong question. It proved the
    behaviour was preserved. The behaviour was the bug.

    This asks the other question. The body is unwrapped before matching,
    because reading a prompt line by line is what caused it.
    """
    import re

    from dissyslab.roles_catalogue import builtin_roles_dir
    from dissyslab.office.role_ports import read_ports

    fallback = re.compile(
        r"(?:when|if)\s+in\s+doubt[^.]*?send\s+to\s+([a-z_][a-z0-9_]*)", re.I
    )

    roots = [Path(builtin_roles_dir())]
    gallery = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"
    roots += sorted(p for p in gallery.glob("**/roles") if p.is_dir())

    checked = 0
    for d in roots:
        for path in sorted(d.glob("*.md")):
            if path.stem == "README" or path.name.startswith("_"):
                continue
            body = " ".join(path.read_text(encoding="utf-8").split())
            m = fallback.search(body)
            if not m:
                continue
            promised = m.group(1)
            declared = read_ports(path).outboxes
            checked += 1
            assert declared and declared[0] == promised, (
                f"{path.name} promises 'when in doubt, send to {promised}' "
                f"but declares outboxes {declared} -- so an unclassified "
                f"message goes to {declared[0]!r}, the opposite of what the "
                f"role says. Put {promised!r} first."
            )
    assert checked, "the fallback phrasing changed; this now checks nothing"


# ── prose says what a field means; the declaration says what it is ────


def _prose_roles() -> list[Path]:
    from dissyslab.roles_catalogue import builtin_roles_dir

    gallery = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"
    roots = [Path(builtin_roles_dir())]
    roots += sorted(p for p in gallery.glob("**/roles") if p.is_dir())
    return [
        p for d in roots for p in sorted(d.glob("*.md"))
        if p.stem != "README" and not p.name.startswith("_")
    ]


def test_no_role_restates_the_output_shape():
    """The reply shape is generated. Nothing may say it a second time.

    Every role used to end with a paragraph naming the keys the model
    should return, and the framework appended its own -- and the two
    disagreed about the one thing that mattered. The role asked for
    every input field plus `summary`; the appended contract asked for
    `send_to` and `text`. Which one the model followed decided whether
    the annotation existed at all, and the shipped annotators worked
    only because capable models follow the longer block.

    ``contract: structured`` roles are exempt, and that is not a
    loophole: nothing is appended to them, so their own prose *is* the
    only statement of the shape. Two of them were wrongly stripped
    while this migration ran, which is how the exemption got noticed.
    """
    import re

    offenders = []
    for path in _prose_roles():
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*contract:\s*structured", text, re.M):
            continue
        if re.search(r"^\s*Output\.\s", text, re.M):
            offenders.append(path.name)
    assert not offenders, (
        "these roles state their own output shape, which the generated "
        f"contract now states: {offenders}"
    )


def test_no_role_tells_the_model_to_preserve_fields():
    """That is a framework guarantee, and the model has no part in it.

    ``role_fn`` merges the upstream message with the model's reply, in
    code. A model returning strictly ``{"summary": ...}`` still
    produces a message carrying `title`, `url` and `timestamp` -- so
    the sentence asking it to preserve them described work it was not
    doing, and cost tokens asking for a copy of the input back.
    """
    import re

    offenders = [
        p.name for p in _prose_roles()
        if re.search(r"[Pp]reserve every existing field", p.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


def test_every_role_that_claims_a_field_declares_it():
    """`emits:` is prose and drifts; `adds:` is read by the framework.

    `deadline_extractor`, written by an assistant in a student session,
    said "adds a `deadline` field" and added two. Ours had the same
    fault: `sentiment_classifier` named one field and declares two,
    and `evaluator`'s sentence named `verdict` while the role adds
    `verdict` and `feedback`.

    So `emits:` no longer names fields at all -- it says what the value
    means, which is the half no declaration can carry. This checks that
    it stays that way.
    """
    import re

    from dissyslab.office.role_ports import read_ports

    offenders = []
    for path in _prose_roles():
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^emits:\s*(.+)$", text, re.M)
        if not m:
            continue
        named = set(re.findall(r"`([a-z_][a-z0-9_]*)`", m.group(1)))
        if named:
            offenders.append((path.name, sorted(named)))
    assert not offenders, (
        "emits: should say what the value means, not name the field -- "
        f"adds: is the name and it cannot drift: {offenders}"
    )
