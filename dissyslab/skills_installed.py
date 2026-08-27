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
    #
    # The Cowork entry was added on 2026-08-26 after `dsl doctor` told
    # this project's own author that office-builder was not installed
    # while he was actively using it. The desktop app materialises
    # account skills two UUID levels down, under a directory named for
    # a *session* -- so it must be globbed, and it will move again.
    # That is the argument for `deep_search` below: a list of known
    # places can only ever be behind.
    for pattern_root, pattern in (
        (home / ".claude" / "plugins", "*/skills"),
        (home / ".gemini" / "extensions", "*/skills"),
        (home / ".codex" / "plugins", "*/skills"),
        (
            home / "Library" / "Application Support" / "Claude"
            / "local-agent-mode-sessions" / "skills-plugin",
            "*/*/skills",
        ),
    ):
        if pattern_root.is_dir():
            roots.extend(sorted(p for p in pattern_root.glob(pattern) if p.is_dir()))
    return roots


#: Directories a home-wide search will not enter. Not for correctness
#: -- a skill could in principle live in any of them -- but because
#: walking a node_modules tree turns "slower" into "appears to hang",
#: and a search people abandon finds nothing.
_DEEP_SKIP = {
    ".Trash", ".cache", ".git", ".npm", ".venv", "Caches",
    "__pycache__", "node_modules", "site-packages", "venv",
}

#: How deep a home-wide search goes. A skill is a directory holding
#: SKILL.md; the deepest real case seen so far is eight levels down.
_DEEP_MAX_DEPTH = 12


def deep_search(home: Path | None = None) -> list[FoundSkill]:
    """Walk the home directory for this project's skills.

    The fast search knows five directories and four glob patterns, and
    every one of them is a guess about somebody else's product. When a
    guess goes stale the fast search reports "not found" -- confidently,
    and wrongly.

    This knows nothing about anyone's layout. It looks for a directory
    called ``skills`` holding a subdirectory named after one of ours
    holding ``SKILL.md``. Slower, and it keeps working when a vendor
    renames something.
    """
    root = Path(home or Path.home())
    found: list[FoundSkill] = []
    seen: set[Path] = set()

    def walk(directory: Path, depth: int) -> None:
        if depth > _DEEP_MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if entry.name in _DEEP_SKIP:
                continue
            if entry.name == "skills":
                for candidate in DISSYSLAB_SKILLS:
                    skill_md = entry / candidate / "SKILL.md"
                    if skill_md.is_file() and skill_md.parent not in seen:
                        skill = _read_skill(skill_md)
                        if skill is not None:
                            seen.add(skill_md.parent)
                            found.append(skill)
            walk(entry, depth + 1)

    walk(root, 0)
    return found


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


def is_source_checkout(skill_dir: Path) -> bool:
    """Is this ``skills/<name>/`` inside the project's own repository?

    A home-wide walk finds the repository's `skills/` folder, which is
    the *source* of a skill and not an installed copy of one. Reporting
    it as installed would be the same wrong answer from the other
    direction: an assistant loads what the vendor materialised, not
    what is sitting in a clone, and telling someone their clone counts
    is how they conclude an install took when it did not.
    """
    try:
        return (skill_dir.parent.parent / "pyproject.toml").is_file()
    except Exception:  # noqa: BLE001
        return False


def _shorten(path: Path) -> str:
    """``~/.claude/skills`` reads better than the absolute form, and it
    is what the user would type."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def locate(cwd: Path | None = None, deep: bool | None = None):
    """Find the skills, falling back to a home-wide walk.

    ``deep=None`` -- the default, and the one that matters -- runs the
    fast search and only walks the home directory if a *basic* skill
    was not found. That is the case where the fast answer is both
    wrong and unactionable, and it is not the user's job to know a
    second command exists. Su is twelve; she did what she was told; a
    message saying "not installed, go install it" is a wall.

    ``deep=True`` forces the walk, ``deep=False`` forbids it.

    Returns ``(skills, roots_searched, went_deep)``.
    """
    found, roots = find_installed(cwd)
    names = {s.name for s in found}
    should = deep is True or (
        deep is None and any(n not in names for n in BASIC_SKILLS)
    )
    if not should:
        return found, roots, False

    by_path = {s.path: s for s in found}
    for skill in deep_search():
        by_path.setdefault(skill.path, skill)
    return list(by_path.values()), roots, True


def report_lines(cwd: Path | None = None, deep: bool | None = None) -> list[str]:
    """The `dsl doctor` section, as lines. Never raises."""
    try:
        found, roots, went_deep = locate(cwd, deep)
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
            #
            # And the wording for a basic one is deliberate. This
            # module knows where it looked; it does not know what
            # exists. It once told this project's author that a skill
            # he was actively using was "not installed" -- the same
            # silent wrong answer it was written to prevent, one level
            # up.
            if name not in DOMAIN_SKILLS:
                lines.append(f"  [    ] {name}: not found")
            continue
        for skill in hits:
            version = skill.version or "no version string"
            mark = "[OK]" if not is_source_checkout(skill.path) else "[    ]"
            lines.append(f"  {mark} {name} {version}")
            lines.append(f"         {_shorten(skill.path)}")
            if is_source_checkout(skill.path):
                lines.append(
                    "         that is the repository's own copy, not an "
                    "installed skill —"
                )
                lines.append(
                    "         an assistant loads what was installed, not what "
                    "is in a clone"
                )
        if len(hits) > 1:
            lines.append(
                f"         {len(hits)} copies of {name} — an assistant loads "
                "one of them, and which one is not yours to choose. Remove "
                "the ones you do not want."
            )

    if not by_name.get("office-builder"):
        lines.append("")
        lines.append("         I could not find office-builder in the usual places")
        if went_deep:
            lines.append("         or anywhere under your home folder. That does not")
            lines.append("         prove it is missing — it proves I could not find it.")
        lines.append("         Without it an assistant will improvise its own")
        lines.append("         concurrency instead of assembling tested parts. Ask your")
        lines.append("         assistant to install the office-builder skill from")
        lines.append(f"         {REPO_URL}, then run this again.")

    lines.append("")
    lines.append("         searched: " + ", ".join(_shorten(r) for r in roots))
    if went_deep:
        lines.append("         and every folder under your home directory")
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


def catalogue_lines(cwd: Path | None = None, deep: bool | None = None) -> list[str]:
    """The `dsl skills` listing, as lines. Never raises."""
    went_deep = False
    try:
        found, roots, went_deep = locate(cwd, deep)
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
                source = is_source_checkout(hits[0].path)
                lines.append(
                    f"    {'[OK]' if not source else '[  ]'} {entry.name}  "
                    f"{version}{'  (repository copy, not installed)' if source else ''}"
                )
                # The path, because "where do my skills live?" cost the
                # author of this project a `find` and two wrong guesses,
                # and because a version with no path cannot tell you
                # which of two copies you are looking at.
                lines.append(f"         {_shorten(hits[0].path)}")
                if len(hits) > 1:
                    lines.append(
                        f"         and {len(hits) - 1} more copy(ies) — an "
                        "assistant loads one of them, and which one is not "
                        "yours to choose"
                    )
            else:
                lines.append(f"    [  ] {entry.name}  (not found)")
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
    if went_deep:
        lines.append("  and every folder under your home directory")
    else:
        lines.append(
            "  `dsl skills --deep` searches your home directory instead — "
            "slower, but"
        )
        lines.append(
            "  it needs to know nothing about where your assistant put them."
        )
    return lines


def print_catalogue(cwd: Path | None = None, deep: bool | None = None) -> None:
    for line in catalogue_lines(cwd, deep):
        print(line)


if __name__ == "__main__":  # pragma: no cover
    os.chdir(os.getcwd())
    print_report()
