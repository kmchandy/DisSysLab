"""Find the DisSysLab skills an assistant would actually load.

Why the package asks this, and not the assistant
------------------------------------------------
The setup script used to end by telling the user to ask their assistant
which version of the skill it had. That asks the possibly-unreliable
thing whether it is reliable: an assistant that never loaded the skill
still answers the question, and answers it plausibly. The failure this
is guarding against -- a skill install that quietly did not take, so
the assistant improvises its own concurrency and looks like it is
working -- is exactly the failure that self-report cannot detect.

Where a skill lives is a question about the filesystem. So ask the
filesystem.

Vendor-neutral by construction
------------------------------
Skills are an open format: a directory holding ``SKILL.md`` with YAML
frontmatter carrying ``name`` and ``description``. The same file loads
in Claude Code, Codex and Gemini CLI. Only the *directories* differ, so
this module knows three vendors' conventions and belongs to none of
them.

It reports which roots it searched, always. A skill installed somewhere
this module has never heard of would otherwise read as "not
installed", which is the same silent-wrong-answer this exists to
prevent -- one level up.
"""
from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class SkillInfo:
    """One skill this project ships.

    The blurb is here, in the package, rather than read from the
    skill's own ``SKILL.md`` -- because the point of ``dsl skills`` is
    to name a skill that is *not installed*, whose SKILL.md is
    therefore not on this machine. Skills are not in the wheel; they
    install from the repository. So the catalogue has to travel with
    the code that prints it, and a test pins the names to ``skills/``.
    """

    name: str
    kind: str  # "basic" | "domain"
    blurb: str


#: Everything this project ships, in the order it should be read.
#:
#: **Basic** skills are what everyone needs; absence is worth
#: reporting, because without them an assistant improvises its own
#: concurrency.
#:
#: **Domain** skills are a field's, installed deliberately by someone
#: working in that field. Absence is the normal case and is not
#: reported as missing: telling a twelve-year-old watching Mars news
#: that she lacks a trading skill is a false alarm, and a doctor that
#: cries wolf stops being read.
CATALOGUE = (
    SkillInfo(
        "office-builder",
        "basic",
        "build, check and run an office -- the grammar, the roles, "
        "the sources and sinks, and what to do when it does nothing",
    ),
    SkillInfo(
        "sensor-office-builder",
        "basic",
        "classify audio, images or sensor readings -- wrap a model or "
        "a signal-processing step as one role and gate its output",
    ),
    SkillInfo(
        "backtest-strategy-builder",
        "domain",
        "describe a trading strategy in English, have it written, "
        "checked against the signal contract, and ranked with the rest",
    ),
)

BASIC_SKILLS = tuple(s.name for s in CATALOGUE if s.kind == "basic")
DOMAIN_SKILLS = tuple(s.name for s in CATALOGUE if s.kind == "domain")

#: Skills that belong to this project. A directory called something
#: else is somebody else's skill and none of our business.
DISSYSLAB_SKILLS = BASIC_SKILLS + DOMAIN_SKILLS

#: Where an assistant is told to install them from. Skills are not in
#: the wheel: they are an open format installed from the repository,
#: which is also what makes them work in Codex and Gemini CLI.
REPO_URL = "https://github.com/kmchandy/DisSysLab"

_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)
_VERSION_RE = re.compile(r"Skill version: `(\d{4}-\d{2}-\d{2}[a-z]?\.[0-9a-f]{7})`")


@dataclass(frozen=True)
class FoundSkill:
    name: str
    version: str | None
    path: Path


def search_roots(cwd: Path | None = None) -> list[Path]:
    """Every directory an assistant is known to load skills from.

    Claude Code and Cowork read ``~/.claude/skills`` and a project's
    ``.claude/skills``. Codex reads ``$HOME/.agents/skills``, a repo's
    ``.agents/skills``, and ``/etc/codex/skills``. Both also load
    skills bundled inside an installed plugin or extension, which is
    why the glob roots are here too.

    Order is home-first then project, which is only presentation: a
    skill found twice is reported twice, deliberately, because two
    copies at different versions is a real thing to see.
    """
    home = Path.home()
    cwd = Path(cwd or Path.cwd())
    roots = [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
        Path("/etc/codex/skills"),
        cwd / ".claude" / "skills",
        cwd / ".agents" / "skills",
    ]
    # Bundled inside a plugin or extension. Globbed rather than named,
    # because the bundle's own directory name is the author's choice.
    for pattern_root, pattern in (
        (home / ".claude" / "plugins", "*/skills"),
        (home / ".gemini" / "extensions", "*/skills"),
        (home / ".codex" / "plugins", "*/skills"),
    ):
        if pattern_root.is_dir():
            roots.extend(sorted(p for p in pattern_root.glob(pattern) if p.is_dir()))
    return roots


def _read_skill(skill_md: Path) -> FoundSkill | None:
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    name_m = _NAME_RE.search(text)
    name = name_m.group(1) if name_m else skill_md.parent.name
    if name not in DISSYSLAB_SKILLS:
        return None
    version_m = _VERSION_RE.search(text)
    return FoundSkill(
        name=name,
        version=version_m.group(1) if version_m else None,
        path=skill_md.parent,
    )


def find_installed(cwd: Path | None = None) -> tuple[list[FoundSkill], list[Path]]:
    """Return (skills found, roots searched)."""
    roots = search_roots(cwd)
    found: list[FoundSkill] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            skill_md = entry / "SKILL.md"
            if skill_md.is_file():
                skill = _read_skill(skill_md)
                if skill is not None:
                    found.append(skill)
    return found, roots


def _shorten(path: Path) -> str:
    """``~/.claude/skills`` reads better than the absolute form, and it
    is what the user would type."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def report_lines(cwd: Path | None = None) -> list[str]:
    """The `dsl doctor` section, as lines. Never raises."""
    try:
        found, roots = find_installed(cwd)
    except Exception:  # noqa: BLE001 - doctor must always finish
        return ["  [    ] could not read the skill directories"]

    by_name = {}
    for skill in found:
        by_name.setdefault(skill.name, []).append(skill)

    lines: list[str] = []
    for name in DISSYSLAB_SKILLS:
        hits = by_name.get(name, [])
        if not hits:
            # A domain skill nobody in this field installed is not a
            # fault, so it is not reported at all.
            if name not in DOMAIN_SKILLS:
                lines.append(f"  [    ] {name}: not installed")
            continue
        for skill in hits:
            version = skill.version or "no version string"
            lines.append(f"  [OK] {name} {version}")
            lines.append(f"         {_shorten(skill.path)}")
        if len(hits) > 1:
            lines.append(
                f"         {len(hits)} copies of {name} — an assistant loads "
                "one of them, and which one is not yours to choose. Remove "
                "the ones you do not want."
            )

    if not by_name.get("office-builder"):
        lines.append("")
        lines.append("         Without office-builder an assistant will improvise its")
        lines.append("         own concurrency instead of assembling tested parts. Ask")
        lines.append("         your assistant to install the office-builder skill from")
        lines.append("         https://github.com/kmchandy/DisSysLab, then run this again.")

    lines.append("")
    lines.append("         searched: " + ", ".join(_shorten(r) for r in roots))
    return lines


def print_report(cwd: Path | None = None) -> None:
    print("Skills:")
    for line in report_lines(cwd):
        print(line)


# ── the catalogue, for `dsl skills` ───────────────────────────────────
#
# `dsl doctor` answers "is what I need installed?". This answers a
# different question -- "what is there?" -- and it is the only thing
# that can, because an assistant cannot see a skill that is not
# installed. A skill's `description:` is what an assistant matches
# against your words, and a skill that is not on disk has no
# description on this machine. So discovery of an uninstalled skill has
# to come from something that is not the assistant.


def catalogue_lines(cwd: Path | None = None) -> list[str]:
    """The `dsl skills` listing, as lines. Never raises."""
    try:
        found, roots = find_installed(cwd)
    except Exception:  # noqa: BLE001 - a listing must always finish
        found, roots = [], []

    installed: Dict[str, list[FoundSkill]] = {}
    for skill in found:
        installed.setdefault(skill.name, []).append(skill)

    lines = ["Skills that come with DisSysLab.", ""]

    for kind, heading in (
        ("basic", "Basic — build an office by describing it"),
        ("domain", "For one field — add the one you work in"),
    ):
        entries = [s for s in CATALOGUE if s.kind == kind]
        if not entries:
            continue
        lines.append(f"  {heading}")
        for entry in entries:
            hits = installed.get(entry.name, [])
            if hits:
                version = hits[0].version or "no version string"
                lines.append(f"    [OK] {entry.name}  {version}")
            else:
                lines.append(f"    [  ] {entry.name}  (not installed)")
            lines.extend(
                textwrap.wrap(
                    entry.blurb,
                    width=72,
                    initial_indent="         ",
                    subsequent_indent="         ",
                )
            )
            if len(hits) > 1:
                lines.append(
                    f"         {len(hits)} copies are installed — an "
                    "assistant loads one of them, and which one is not "
                    "yours to choose."
                )
        lines.append("")

    missing = [s for s in CATALOGUE if s.name not in installed]
    if missing:
        lines.append("  To install one, ask your assistant:")
        lines.append("")
        lines.append(
            f"      Install the {missing[0].name} skill from {REPO_URL}"
        )
        lines.append("")
        lines.append(
            "  Then run `dsl skills` again. Do not ask the assistant "
            "whether it worked —"
        )
        lines.append(
            "  an assistant that never loaded a skill will answer anyway. "
            "Where a skill"
        )
        lines.append("  lives is a question about the filesystem.")
        lines.append("")

    lines.append("  searched: " + ", ".join(_shorten(r) for r in roots))
    return lines


def print_catalogue(cwd: Path | None = None) -> None:
    for line in catalogue_lines(cwd):
        print(line)


if __name__ == "__main__":  # pragma: no cover
    os.chdir(os.getcwd())
    print_report()
