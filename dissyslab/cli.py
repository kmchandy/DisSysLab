# dissyslab/cli.py
"""
`dsl` — command-line entry point for DisSysLab.

After `pip install dissyslab`, users get a `dsl` command with
subcommands aimed at first-year undergraduates:

    dsl list                      list offices that ship with dissyslab
    dsl init <office> <folder>    copy a gallery office into <folder>
    dsl new <folder>              build a new office by chatting with Claude
    dsl edit <office_dir>         modify an existing office by chatting with Claude
    dsl run <office_dir>          run a closed office end-to-end
    dsl build <office_dir>        generate build/run.py for an office
    dsl doctor                    check Python, deps, backend, and run a self-test
    dsl --version                 print the installed dissyslab version

This module is intentionally small: it dispatches to the real
implementation elsewhere in the package. New subcommands should be
added as small handler functions below; keep the top-level
argument parsing boring and readable.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import runpy
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Callable


# ── Helpers ───────────────────────────────────────────────────────────────────

def _eprint(msg: str) -> None:
    """Print to stderr so tooling can separate progress from data output."""
    print(msg, file=sys.stderr)


def _require_dir(label: str, path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_dir():
        _eprint(f"Error: {label} '{path_str}' is not a directory.")
        sys.exit(2)
    return p


def _package_version() -> str:
    """The version, and -- for an editable install -- where the code is.

    A recorded version can lie. ``pip install -e .`` writes the version
    that was in ``pyproject.toml`` at install time and never revisits
    it, while the code that runs is whatever is in the working tree. On
    2026-08-26 that gap was nine commits and two minor versions wide:
    ``dsl --version`` said 1.6.1 while running 1.7.2 plus a week's
    work, and an assistant reading that number would have told a
    student their install had no ``dsl check``.

    So an editable install reports what cannot go stale -- the
    directory the code is being imported from, and the commit if that
    directory is a git working tree:

        dissyslab 1.7.2 (editable: /Users/x/DisSysLab @ f7181c8)

    Derived, not recorded, for the same reason the skill version
    carries a content hash.
    """
    try:
        from importlib.metadata import version
        recorded = version("dissyslab")
    except Exception:
        # Running from a source checkout with no installed dist at all.
        recorded = "unknown (source)"

    editable = _editable_source()
    return f"{recorded} ({editable})" if editable else recorded


def _editable_source() -> str | None:
    """``editable: <dir> @ <commit>`` when the code is not in site-packages.

    Returns ``None`` for a normal wheel install, where the recorded
    version is the whole truth and a path would be noise.
    """
    import dissyslab

    try:
        source = Path(dissyslab.__file__).resolve().parent
    except Exception:  # noqa: BLE001 - a version string must never raise
        return None
    if "site-packages" in source.parts or "dist-packages" in source.parts:
        return None

    root = source.parent
    commit = _git_commit(root)
    return f"editable: {root}" + (f" @ {commit}" if commit else "")


def _git_commit(root: Path) -> str | None:
    """The short commit of the working tree, read without running git.

    Reading the files means this works with no git on PATH and cannot
    hang; a subprocess in a version string is a bad trade. Returns
    ``None`` for anything unexpected -- a version string that raises is
    worse than one that is merely short.
    """
    try:
        head = (root / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref = head.split(None, 1)[1].strip()
            ref_file = root / ".git" / ref
            if ref_file.is_file():
                return ref_file.read_text(encoding="utf-8").strip()[:7]
            # A packed ref -- the loose file is gone after `git gc`.
            packed = (root / ".git" / "packed-refs").read_text(encoding="utf-8")
            for line in packed.splitlines():
                if line.endswith(f" {ref}"):
                    return line.split()[0][:7]
            return None
        return head[:7] if len(head) >= 7 else None
    except Exception:  # noqa: BLE001
        return None


def _packaged_gallery() -> Path:
    """Return a filesystem path to the gallery that ships inside the package.

    Works for normal `pip install dissyslab` installs and for editable
    (`pip install -e .`) installs alike, because importlib.resources
    resolves to the real on-disk location in both cases.
    """
    from importlib.resources import files
    trav = files("dissyslab") / "gallery"
    return Path(str(trav))


# The gallery split (#115) put Pat-facing offices under gallery/apps/
# and Builder demos under gallery/examples/. Older gallery offices
# (pre-split) lived at gallery/<name>/ directly. Both styles need to
# resolve so `dsl init` / `dsl run <name>` keep working.
_GALLERY_SUBSECTIONS = ("apps", "examples", "")


def _find_packaged_office(name: str) -> Path | None:
    """Locate a packaged office by name across the gallery split.

    Searches in priority order: gallery/apps/<name>, gallery/examples/<name>,
    gallery/<name>. Returns the first directory that contains office.md
    (or the legacy network.md). Returns None if nothing matches.
    """
    gallery = _packaged_gallery()
    for sub in _GALLERY_SUBSECTIONS:
        candidate = gallery / sub / name if sub else gallery / name
        if candidate.is_dir() and (
            (candidate / "office.md").is_file()
            or (candidate / "network.md").is_file()
        ):
            return candidate
    return None


def _walk_packaged_offices() -> dict[str, list[Path]]:
    """Walk the packaged gallery and bucket offices by section.

    Returns a dict keyed by section name ('apps', 'examples', or '')
    whose values are sorted lists of office directories in that
    section. An "office directory" is one containing office.md
    (or the legacy network.md). The empty-string key holds any
    pre-split offices that still live directly under gallery/.
    """
    gallery = _packaged_gallery()
    out: dict[str, list[Path]] = {sub: [] for sub in _GALLERY_SUBSECTIONS}
    if not gallery.is_dir():
        return out
    for sub in _GALLERY_SUBSECTIONS:
        root = gallery / sub if sub else gallery
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name.startswith("__"):
                continue
            if child.name in _GALLERY_SUBSECTIONS and sub == "":
                # Skip apps/ and examples/ themselves when listing the
                # legacy root — they are not offices, they are sections.
                continue
            if (child / "office.md").is_file() or (child / "network.md").is_file():
                out[sub].append(child)
    return out


#: Lines that begin an office's *grammar* rather than describe it. An
#: office.md with no prose under its title would otherwise be summarised
#: by its own wiring -- `dsl list` showed eight offices described as
#: "Sources: starter", which tells a reader nothing and looks broken.
_GRAMMAR_PREFIXES = (
    "sources:", "sinks:", "agents:", "connections:", "office:",
)


def _unfinished_reason(office_dir: Path) -> str:
    """Why this office is not expected to work yet, or '' if it is.

    An office that is still being built carries a file named ``WIP``
    whose first line says what is missing. The test sweeps have honoured
    that marker for months -- they report an expected failure instead of
    a hard one -- but `dsl list` did not, so `salton_sea_dashboard` was
    advertised under "ready to run" while `dsl check` reported two
    faults on it. A catalogue that recommends something known not to
    work spends a beginner's afternoon.
    """
    marker = Path(office_dir) / "WIP"
    if not marker.is_file():
        return ""
    try:
        for line in marker.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    except OSError:
        pass
    return "work in progress"


def _one_line_description(office_dir: Path) -> str:
    """A short description of an office for `dsl list`, or '' if none.

    The first line of prose in README.md, falling back to office.md.

    **Nothing is better than something wrong.** This is a catalogue
    somebody browses to choose what to run, so a line that is not a
    description -- a blockquote marker, a wiring declaration -- is worse
    than a blank, which at least reads as "no description" rather than
    as a description that makes no sense.
    """
    for candidate in ("README.md", "office.md"):
        f = office_dir / candidate
        if not f.is_file():
            continue
        # `#` means two different things in the two files. In a README
        # it is a heading, to be skipped. In an office.md only the first
        # one is the title; the rest are comments, and five gallery
        # offices keep their whole description in them -- which is why
        # `dsl list` showed them as "Sources: starter" while a perfectly
        # good sentence sat two lines above.
        comments_are_prose = candidate == "office.md"
        past_title = False
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("**Tags:**"):
                    continue
                if s.startswith("#"):
                    if not comments_are_prose:
                        continue
                    if not past_title:
                        past_title = True
                        continue
                    s = s.lstrip("#").strip()
                    if not s:
                        continue
                # A lead paragraph is often written as a blockquote. The
                # marker is markdown, not part of the sentence.
                while s.startswith(">"):
                    s = s[1:].lstrip()
                if not s:
                    continue
                if s.lower().startswith(_GRAMMAR_PREFIXES):
                    break  # this file describes nothing; try the next
                # Strip simple markdown bold markers so the terminal
                # output reads naturally — e.g. `**Foo.**` → `Foo.`.
                cleaned = s.replace("**", "")
                return cleaned[:80]
        except OSError:
            continue
    return ""


def _read_tags(office_dir: Path) -> list[str]:
    """Read the `**Tags:**` line from an office's README.md.

    The convention, which `dsl list` relies on: every gallery office
    has a single line of the form

        **Tags:** tag1, tag2, tag3

    just under the lead paragraph. Returns the tags in declared order
    with whitespace stripped, or [] if the line is absent.
    """
    f = office_dir / "README.md"
    if not f.is_file():
        return []
    try:
        for line in f.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("**Tags:**"):
                rest = s[len("**Tags:**"):].strip()
                return [t.strip() for t in rest.split(",") if t.strip()]
    except OSError:
        return []
    return []


# Curriculum-ordered concept groups for `dsl list`. Each office's
# group is determined by which concept tag it carries, scanned in the
# order below; the first match wins. (`starter` outranks
# `single-agent` so my_first_office lands under "Starter" rather
# than alongside the polling monitors.)
_CONCEPT_GROUPS: list[tuple[str, str]] = [
    ("starter", "Starter"),
    ("single-agent", "Single-agent monitors"),
    ("filter", "One-agent filter"),
    ("handoff", "Two-agent handoff"),
    ("feedback-loop", "Two-agent feedback loop"),
    ("live-stream", "Live streaming"),
    ("network-of-offices", "Networks of offices"),
]
_FALLBACK_GROUP = "Other"


def _group_for(tags: list[str]) -> str:
    """Return the curriculum group label for an office's tags.

    Priority is *most-specific concept wins* — `starter` outranks
    `single-agent`, `live-stream` outranks `two-agent`, etc. The
    priority order is encoded in `_CONCEPT_GROUPS`.
    """
    # `starter` is the only tag that should outrank `single-agent`.
    # Otherwise prefer the most specific concept tag the office carries.
    if "starter" in tags:
        return dict(_CONCEPT_GROUPS)["starter"]
    # Walk priority order in reverse so more-specific concepts win.
    for tag, label in reversed(_CONCEPT_GROUPS):
        if tag == "starter":
            continue
        if tag in tags:
            return label
    return _FALLBACK_GROUP


# ── Subcommand: run ───────────────────────────────────────────────────────────

def _explain_failure(command: str, exc: BaseException) -> str:
    """
    Convert a raw Python exception from `dsl run` / `dsl build` into a
    Path-A-friendly message with an actionable next step.

    Path A users don't know what `ModuleNotFoundError` or a 401 from
    Anthropic means. This mapper trades a pristine Python traceback for
    a line the student can actually do something with. Unknown errors
    fall through to a typed message + traceback so we never silently
    hide information (an empty `str(exc)` used to mean the user saw
    "dsl run failed:" with nothing after the colon).

    Set DSL_DEBUG=1 to append the full Python traceback to *any* message
    — useful when a friendly mapping fired but you want to see the raw
    exception underneath (e.g. for filing an issue).
    """
    message = _explain_failure_message(command, exc)
    if os.environ.get("DSL_DEBUG"):
        tb = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        if "Full traceback:" not in message:
            message = f"{message}\n\nFull traceback:\n{tb}"
    return message


def _explain_failure_message(command: str, exc: BaseException) -> str:
    """The actual exception → user-message mapper. See _explain_failure."""
    msg = str(exc)

    # OfficeRunError is raised by the framework specifically to be read
    # by the person running the office -- it already names the source,
    # the reason, and the fix. Wrapping it in a traceback would bury
    # the one useful part. (DSL_DEBUG still appends the traceback.)
    from dissyslab.network import OfficeRunError
    if isinstance(exc, OfficeRunError):
        return (
            f"{command}: the office ran but produced nothing.\n\n{msg}"
        )

    # ParseError is the same case as OfficeRunError: it already names
    # the file, the line, the snippet and the three forms an agent line
    # may take. A traceback underneath it is forty lines of framework
    # internals wrapped around a message about a missing article, and
    # the reader's eye goes to the traceback. (DSL_DEBUG still appends
    # it.)
    from dissyslab.office.parser_errors import ParseError
    if isinstance(exc, ParseError):
        return f"{command}: {msg}"

    # Missing Python module — almost always a stale build/run.py or
    # a package the user forgot to install in this venv.
    if isinstance(exc, ModuleNotFoundError):
        name = exc.name or ""
        if name in {"components", "dsl"}:
            return (
                f"{command} failed: the office's build/run.py uses an "
                f"old '{name}' import path.\n"
                f"  Fix: regenerate with  dsl build <office_dir>\n"
                f"       or `dsl init` a fresh copy from the gallery."
            )
        if name in {
            "anthropic", "dotenv", "feedparser", "requests",
            "websocket", "bs4", "PIL", "numpy", "scipy",
        }:
            return (
                f"{command} failed: dependency '{name}' is not importable.\n"
                f"  Fix: pip install --upgrade dissyslab\n"
                f"       (or activate the venv where dissyslab is installed)"
            )
        if name == "dissyslab":
            return (
                f"{command} failed: dissyslab isn't installed in this Python "
                f"environment.\n"
                f"  Fix: compare `which dsl` and `which python` — they must "
                f"match.\n"
                f"       If you're using a venv, activate it first.\n"
                f"       See docs/API_KEY_SETUP.md for details."
            )
        return (
            f"{command} failed: module '{name}' not found.\n"
            f"  The office may depend on a package not yet installed, or\n"
            f"  was generated by an older dissyslab version. Try `dsl doctor`."
        )

    # Anthropic auth / rate-limit errors bubble up as anthropic.APIError
    # subclasses; match on the message text so we don't have to import.
    lower = msg.lower()
    if "401" in msg and ("authentication" in lower or "invalid" in lower and "key" in lower):
        return (
            f"{command} failed: Anthropic rejected the API key (HTTP 401).\n"
            f"  Fix: run `dsl doctor` from the office folder to check .env,\n"
            f"       then re-copy your key from https://console.anthropic.com/\n"
            f"       See docs/API_KEY_SETUP.md for the full checklist."
        )
    if "429" in msg or "rate limit" in lower:
        return (
            f"{command} failed: rate limited by an external API (HTTP 429).\n"
            f"  Fix: wait a minute and try again, or increase poll_interval\n"
            f"       in your office.md so the source polls less often."
        )
    # Two flavors of "no key": (1) our own code raising with the env-var
    # name visible, (2) the Anthropic SDK's own "Could not resolve
    # authentication method…" when the client is constructed with no key
    # at all. The second is what a brand-new student hits first.
    if (
        "anthropic_api_key" in lower
        and ("not set" in lower or "missing" in lower or "none" in lower)
    ) or "could not resolve authentication method" in lower:
        return (
            f"{command} failed: ANTHROPIC_API_KEY isn't set.\n"
            f"  Fix: create a .env file in the office folder:\n"
            f"         echo \"ANTHROPIC_API_KEY=<your-key>\" > .env\n"
            f"       See docs/API_KEY_SETUP.md for the full walkthrough."
        )

    # A target dir with no office.md/network.md yet -- almost always means
    # the Stage 1 draft was never run through assemble.py, not a build/run
    # problem. Check this before the generic FileNotFoundError case below,
    # since this message has no .filename set and would otherwise fall
    # through to the wrong ("build/run.py missing") guidance.
    if isinstance(exc, FileNotFoundError) and "office.md or network.md" in msg:
        return (
            f"{command} failed: {msg}\n"
            f"  Fix: if this is a Stage 1 hand-off file that hasn't been\n"
            f"       generated yet, run\n"
            f"         python -m dissyslab.office.assemble <draft.py> <target_dir>\n"
            f"       first (phase3_al_howto.md, step 5), then retry {command}."
        )

    # Common file-not-found during artifact startup (e.g. missing run.py).
    if isinstance(exc, FileNotFoundError):
        missing = getattr(exc, "filename", None) or "(unknown)"
        return (
            f"{command} failed: file not found: {missing}\n"
            f"  If this is build/run.py, run `dsl build <office_dir>` first.\n"
            f"  If this is .env, see docs/API_KEY_SETUP.md."
        )

    # Port-in-use from the webhook source (or any other socket-binding
    # source). Students who Ctrl+C the listener and immediately re-run
    # hit this constantly because the OS keeps the socket in TIME_WAIT.
    if isinstance(exc, OSError) and (
        "address already in use" in lower
        or getattr(exc, "errno", None) in {48, 98}  # macOS, Linux
    ):
        return (
            f"{command} failed: a port is already in use ({msg}).\n"
            f"  Fix: another process is bound to that port.\n"
            f"       - Wait ~30s if you just stopped the listener (TIME_WAIT).\n"
            f"       - Or pick a different port in office.md, e.g.\n"
            f"           Sources: webhook(port=9000)"
        )

    # Gmail IMAP authentication failure — almost always the student
    # passed their real Google password instead of an app password,
    # or 2-Step Verification isn't on yet.
    if (
        "imap" in lower
        or "authenticationfailed" in lower.replace(" ", "")
        or "application-specific password required" in lower
    ) and (
        "auth" in lower or "login" in lower or "password" in lower
    ):
        return (
            f"{command} failed: Gmail rejected the login.\n"
            f"  Fix: Gmail requires an *app password*, not your normal password.\n"
            f"       1. myaccount.google.com → Security → 2-Step Verification (on)\n"
            f"       2. Same page → App passwords → generate one for 'Mail'\n"
            f"       3. export GMAIL_APP_PASSWORD='<the 16-char password>'"
        )

    # Missing-credential ValueErrors raised from a source/sink __init__.
    # The message itself is already actionable (each component prints
    # the env-var name and a sample export); we just want to strip the
    # traceback so it's the first thing the student sees.
    if isinstance(exc, ValueError) and (
        "credentials not found" in lower
        or "webhook url not found" in lower
        or "slack webhook url" in lower
        or ("environment variable" in lower and "not" in lower)
    ):
        # Indent the multi-line ValueError message so it reads as a block
        # under the "Fix:" header without re-wrapping it.
        body = "\n".join(f"  {line}" for line in msg.splitlines())
        return f"{command} failed: missing credentials.\n{body}"

    # Fall-through: unknown exception. Always show the type name (so the
    # message is non-empty even when str(exc) is empty), plus the full
    # traceback. The traceback is the most useful thing for debugging an
    # unknown error and the most useful thing to paste into a bug report.
    tb = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    summary = str(exc).strip()
    head = (
        f"{command} failed: {type(exc).__name__}: {summary}"
        if summary
        else f"{command} failed: {type(exc).__name__} (no message)."
    )
    return f"{head}\n\nFull traceback:\n{tb}"


def _resolve_office_arg(arg: str, label: str) -> Path | None:
    """Resolve an office argument to a directory.

    Two forms are accepted:

    * A path (relative or absolute) to a directory the user owns.
      This wins if the path exists on disk, so Pat's local copy
      always beats a packaged office of the same name.
    * A bare office name (e.g. ``situation_room``) that resolves
      to a packaged office in the gallery the wheel ships. This
      is the form the README uses now that Pat doesn't have to
      clone the repo.

    Returns the resolved directory, or None if neither form works.
    Emits a Pat-friendly error to stderr before returning None.
    """
    as_path = Path(arg)
    if as_path.is_dir():
        return as_path

    # Only attempt name lookup when the argument is a bare identifier
    # (no slashes, no extension). A typoed path like
    # "dissyslab/gallery/wrong" should surface as "not a directory",
    # not as "no office named '...gallery/wrong'".
    if "/" not in arg and "\\" not in arg and not as_path.suffix:
        found = _find_packaged_office(arg)
        if found is not None:
            return found

    _eprint(f"Error: {label} '{arg}' is not a directory and not a packaged office name.")
    _eprint("Run `dsl list` to see packaged office names, or check the path you typed.")
    return None


def _refuse_if_draft(office_dir, command: str) -> bool:
    """True if the office is still being described, and we said so.

    The check belongs here as well as in the compiler because only here
    can it name *every* agent whose job is undecided. The compiler meets
    them one at a time and stops at the first, which is right for a
    library caller and wrong for a person who wants the whole list.

    Silent on anything it cannot parse: a syntax error has its own,
    better message a few lines further on.
    """
    try:
        from dissyslab.office.office_spec import draft_refusal, unassigned_agents
        from dissyslab.office.parser import parse_office_dir

        pending = unassigned_agents(parse_office_dir(Path(office_dir)))
    except Exception:  # noqa: BLE001
        return False
    if not pending:
        return False
    _eprint(f"{command}: {draft_refusal(pending)}")
    return True


def cmd_run(args: argparse.Namespace) -> int:
    """Build (if stale) and run a closed office via office."""
    office_dir = _resolve_office_arg(args.office_dir, "office_dir")
    if office_dir is None:
        return 2

    if _refuse_if_draft(office_dir, "dsl run"):
        return 1

    # Power-user override: --processes flag asks the runtime to use
    # ``process_network()`` (one OS process per agent — true CPU
    # parallelism) instead of the default ``run_network()`` (threads).
    # Implemented via an environment variable so the generated artifact
    # picks up the choice without needing a code change for every run.
    # Pat does not see this flag in normal use; the help text mentions
    # it for the curious. See examples/module_08 for the canonical
    # CPU-parallelism demo.
    if getattr(args, "processes", False):
        os.environ["DSL_PROCESS_MODE"] = "process"

    # v1.6: propagate checkpoint-resume flags to the generated build/run.py
    # via environment variables that the artifact's __main__ block reads.
    if getattr(args, "snapshot_interval", None) is not None:
        os.environ["DSL_SNAPSHOT_INTERVAL"] = str(args.snapshot_interval)
    if getattr(args, "resume", None) is not None:
        os.environ["DSL_RESUME"] = str(args.resume)

    # v1.7: opt-in per-agent activity-log trace. Off by default (no env
    # var set, no cost). See docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md.
    if getattr(args, "trace", False):
        os.environ["DSL_TRACE"] = "1"

    # Print per-agent message counts when the run finishes. On by
    # default: an office that produced nothing used to look exactly
    # like one that worked, and the counts make that visible without
    # the reader having to know what to expect.
    if not getattr(args, "quiet", False):
        os.environ["DSL_RUN_SUMMARY"] = "1"

    from dissyslab.office.cli_helpers import cli_run

    try:
        return cli_run(office_dir)
    except SystemExit as e:
        # The artifact's __main__ block may sys.exit for clean errors.
        return int(e.code or 0)
    except Exception as exc:  # noqa: BLE001
        _eprint(_explain_failure("dsl run", exc))
        return 1


# ── Subcommand: build ─────────────────────────────────────────────────────────

def cmd_build(args: argparse.Namespace) -> int:
    """Generate build/run.py for an office via office codegen."""
    office_dir = _resolve_office_arg(args.office_dir, "office_dir")
    if office_dir is None:
        return 2

    if _refuse_if_draft(office_dir, "dsl build"):
        return 1

    from dissyslab.office.cli_helpers import cli_build

    try:
        return cli_build(office_dir)
    except SystemExit as e:
        return int(e.code or 0)
    except Exception as exc:  # noqa: BLE001
        _eprint(_explain_failure("dsl build", exc))
        return 1


# ── Subcommand: check ─────────────────────────────────────────────────────────

def cmd_check(args: argparse.Namespace) -> int:
    """Report structural faults in an office's wiring without running it."""
    office_dir = _resolve_office_arg(args.office_dir, "office_dir")
    if office_dir is None:
        return 2

    from dissyslab.office.check_wiring import check_office_dir, format_report

    try:
        report = check_office_dir(office_dir)
    except Exception as exc:  # noqa: BLE001
        _eprint(_explain_failure("dsl check", exc))
        return 1

    print(format_report(report), end="")
    return 0 if report.ok else 1


# ── Subcommand: draw ──────────────────────────────────────────────────────────

def cmd_draw(args: argparse.Namespace) -> int:
    """Show an office's network: as text by default, Mermaid on request.

    Text is the default because that is what the person running the
    command can read. Mermaid is a diagram *somewhere else* -- pasted
    into GitHub or an editor -- and a student who types `dsl draw .`
    expecting to see her office got a wall of flowchart source with no
    hint that a readable form existed.

    The text form also answers the question `office.md` cannot.
    `Screen is a relevance_filter.` says nothing about Screen having an
    outbox called `discard`; the listing names both ends of every edge
    and puts every unconnected port in a block of its own.

    On demand, not after every edit. See the note at the head of
    ``dissyslab/office/draw.py``: a diagram produced on every change
    has to stay stable under change so the reader does not have to
    re-find what they had already understood; one asked for once has
    no such obligation, and that is what keeps this simple.
    """
    office_dir = _resolve_office_arg(args.office_dir, "office_dir")
    if office_dir is None:
        return 2

    from dissyslab.office.draw import draw_office_dir, fenced, text_office_dir

    try:
        if args.mermaid:
            diagram = draw_office_dir(office_dir)
            text = diagram if args.raw else fenced(diagram)
        else:
            text = text_office_dir(office_dir)
    except Exception as exc:  # noqa: BLE001
        _eprint(_explain_failure("dsl draw", exc))
        return 1

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


# ── Subcommand: roles ─────────────────────────────────────────────────────────

def cmd_roles(args: argparse.Namespace) -> int:
    """List the built-in roles and what each one adds to a message.

    Nothing could do this before, so an assistant asked "what roles are
    there?" read the thirteen prompt files and paraphrased -- afresh
    each time, so no two students were told the same thing about
    `summarizer`. The emitted field is the fact a user needs in order
    to wire the next agent.
    """
    from dissyslab.roles_catalogue import catalogue, format_catalogue

    print(format_catalogue(catalogue()), end="")
    return 0


#: What `dsl grammar <topic>` prints. The keys are what a person would
#: type; the values are files in `dissyslab/reference/`.
_REFERENCE_TOPICS = {
    "office": ("grammar.md", "how office.md is written"),
    "roles": ("roles.md", "writing a role, in English or in Python"),
    "sources": ("sources_and_sinks.md", "the sources and sinks, and their arguments"),
    "examples": ("worked_examples.md", "offices built end to end"),
}


def cmd_grammar(args: argparse.Namespace) -> int:
    """Print the office reference, which ships with the code.

    These four documents used to live inside the `office-builder`
    skill. That put the language and the description of the language on
    two release paths -- the skill from GitHub, the parser from PyPI --
    so every grammar change meant re-stamping the skill and asking each
    user to save it again, and a user with yesterday's skill was being
    taught a language their install did not have.

    Here there is one version. An assistant reads this rather than
    carrying a copy, which is why the skill can now be twenty lines
    that contain no facts.
    """
    from dissyslab.reference import __file__ as _ref_init

    topic = (getattr(args, "topic", None) or "office").lower()
    if topic not in _REFERENCE_TOPICS:
        _eprint(
            f"dsl grammar: no topic called {topic!r}.\n\n"
            + "\n".join(
                f"  {name:<10} {blurb}"
                for name, (_f, blurb) in _REFERENCE_TOPICS.items()
            )
        )
        return 2

    filename, _blurb = _REFERENCE_TOPICS[topic]
    path = Path(_ref_init).resolve().parent / filename
    try:
        print(path.read_text(encoding="utf-8"), end="")
    except OSError as exc:
        _eprint(
            f"dsl grammar: could not read {filename} ({exc}). This is a "
            "packaging bug -- please report it at\n"
            "https://github.com/kmchandy/DisSysLab/issues."
        )
        return 2
    return 0


def cmd_checks(args: argparse.Namespace) -> int:
    """Say what a check code means.

    `dsl check` prints `W11` beside a finding. Codes are worth having --
    stable across rewordings, and a way for two people to refer to the
    same finding without quoting a sentence at each other -- but they
    are opaque, and until this existed a reader who did not already
    know had nowhere to go. The meanings lived in the code that raises
    them and in CHANGELOG entries filed by release.
    """
    from dissyslab.office.check_catalogue import catalogue_lines, get

    code = getattr(args, "code", None)
    for line in catalogue_lines(code):
        print(line)
    return 0 if code is None or get(code) is not None else 1


def cmd_skills(_args: argparse.Namespace) -> int:
    """List the skills this project ships and which are installed.

    `dsl doctor` answers "is what I need installed?". This answers
    "what is there?", which nothing could answer before -- and which
    an assistant structurally cannot, because a skill that is not
    installed has no `description:` on this machine for the assistant
    to match your words against. Discovery of an uninstalled skill has
    to come from something that is not the assistant.
    """
    from dissyslab.skills_installed import print_catalogue

    print_catalogue(deep=True if getattr(_args, "deep", False) else None)
    return 0


# ── Subcommand: fetch-prices ──────────────────────────────────────────────────

def cmd_fetch_prices(args: argparse.Namespace) -> int:
    """Download the user's own price history.

    A subcommand rather than a script in one gallery folder, so an
    assistant can run it. A capability an assistant cannot reach is a
    capability the user has to reach themselves, and that is what put a
    git clone and two shell commands in a tester's path to a backtest.
    """
    from dissyslab.market_fetch import (
        DEFAULT_PATTERN, FetchError, confirm_office_reads, fetch, office_basket,
    )

    tickers = list(args.tickers or [])
    pattern = DEFAULT_PATTERN
    years = args.years
    office_dir = None

    if not tickers:
        # No tickers named: take the basket from an office, so the
        # fetch matches what that office will look for.
        office_dir = Path(args.office) if args.office else Path.cwd()
        try:
            tickers, pattern, years = office_basket(office_dir)
        except FetchError as exc:
            _eprint(f"dsl fetch-prices: {exc}")
            return 1
        if args.years is not None:
            years = args.years
        print(f"Reading the basket from {office_dir}/office.md")
    elif years is None:
        years = 10

    try:
        results = fetch(tickers, years=years, pattern=pattern,
                        dest=args.dest, force=args.force)
    except FetchError as exc:
        _eprint(f"dsl fetch-prices: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        _eprint(_explain_failure("dsl fetch-prices", exc))
        return 1

    for r in results:
        note = "already there" if r.skipped else f"{r.rows} rows"
        print(f"  {r.ticker:<8} {note:<12} {r.path}")
    fetched = [r for r in results if not r.skipped]
    print(f"{len(fetched)} downloaded, {len(results) - len(fetched)} already "
          f"present. Re-fetch with --force.")

    # Prove the office can read what was just written. Fetching and
    # reading are two pieces of code agreeing on a directory and a
    # filename; better to find out here than from an office that runs
    # and produces nothing.
    if office_dir is not None:
        unreadable = confirm_office_reads(office_dir, tickers, pattern,
                                          dest=args.dest)
        if unreadable:
            _eprint("but the office still cannot read:")
            for line in unreadable:
                _eprint(f"  {line}")
            return 1
        print(f"The office at {office_dir} can read all "
              f"{len(tickers)} tickers.")
    return 0


# ── Subcommand: explain-trace ─────────────────────────────────────────────────

def cmd_explain_trace(args: argparse.Namespace) -> int:
    """Merge a run's per-agent trace files into one ordered, structured record.

    Reads <trace_dir>/*.jsonl (one file per agent, written by `dsl run
    --trace`) and merges every agent's entries into a single sequence,
    sorted by (t, sent-before-received, agent_name) -- see the sort
    call below for why "sent-before-received" was added to Part 1's
    (t, agent_name) tie-break during implementation.

    This command's job stops here: it emits the ordered record as JSONL,
    it does not narrate it in English. Per the design doc's division of
    labor ("DisSysLab produces the record; Claude produces the English"),
    turning this into a sentence-by-sentence explanation for Pat is
    Cowork's job, done by reading this command's output --
    the same pattern already used for office-structure explanations and
    the debug_demo walkthrough.
    """
    trace_dir = Path(args.trace_dir)
    if not trace_dir.is_dir():
        _eprint(f"Error: trace_dir '{trace_dir}' is not a directory.")
        _eprint(
            "Run an office with `dsl run --trace` first -- trace files "
            "are written to <office_dir>/trace/."
        )
        return 2

    files = sorted(trace_dir.glob("*.jsonl"))
    if not files:
        _eprint(f"No *.jsonl trace files found in '{trace_dir}'.")
        _eprint(
            "Run an office with `dsl run --trace` first, then point "
            "this command at the resulting trace/ directory."
        )
        return 2

    entries = []
    for f in files:
        agent_name = f.stem
        with open(f, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    _eprint(
                        f"Warning: skipping malformed line {line_no} in "
                        f"{f.name}: {exc}"
                    )
                    continue
                entries.append({
                    "t": rec.get("t"),
                    "agent": agent_name,
                    "dir": rec.get("dir"),
                    "port": rec.get("port"),
                    "msg": rec.get("msg"),
                })

    # Part 1's tie-break, with one refinement found during real testing:
    # sort by (t, sent-before-received, agent_name).
    #
    # The design doc's rule (x := max(t, x+1) on receive) guarantees
    # each *agent's own* sequence strictly increases, but does not
    # guarantee a receive's timestamp is strictly greater than the
    # timestamp of the very message it just received -- when the
    # receiver's clock is behind the sender's, max(t, x+1) == t exactly,
    # so a "sent" action and the matching "received" action can land on
    # the identical timestamp. Plain agent_name is not a safe tie-break
    # for that case: two names could easily sort the wrong way, showing
    # a receive before its own send. Breaking ties "sent" before
    # "received" first (and only then by agent_name) keeps every
    # message's send ahead of its receive without changing the clock
    # algorithm itself -- this is purely a display-ordering refinement.
    # Ties between *unrelated* actions at different agents remain an
    # arbitrary but fixed choice, per the design doc's honest framing:
    # this is *a* valid causally-consistent linearization, not *the*
    # one true real-time order.
    entries.sort(key=lambda e: (e["t"], 0 if e["dir"] == "sent" else 1, e["agent"]))

    out_text = "".join(json.dumps(e) + "\n" for e in entries)

    if getattr(args, "output", None):
        out_path = Path(args.output)
        out_path.write_text(out_text, encoding="utf-8")
        print(f"Wrote {len(entries)} ordered actions to {out_path}")
    else:
        sys.stdout.write(out_text)

    return 0


# ── Subcommand: show-checkpoint ───────────────────────────────────────────────

def _json_safe(value: Any, _cutoff: int = 300) -> Any:
    """Best-effort conversion of a pickled value into something
    json.dumps can serialize.

    Plain dict/list/tuple/str/number/bool/None pass through
    recursively unchanged -- the common case, since agent state
    (``save_state()``'s return value) is almost always simple data, as
    every gallery office's actually is. Anything else (a custom class
    instance, a datetime, etc.) falls back to a truncated ``repr()``,
    mirroring core.py's trace-message truncation policy (same 300-char
    cutoff), so an exotic picklable value never crashes this command --
    it just shows up as readable-but-not-structured text instead of
    structured JSON.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v, _cutoff) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, _cutoff) for v in value]
    text = repr(value)
    if len(text) > _cutoff:
        extra = len(text) - _cutoff
        text = text[:_cutoff] + f"... (truncated, {extra} more chars)"
    return text


def cmd_show_checkpoint(args: argparse.Namespace) -> int:
    """Merge one checkpoint's manifest, per-agent state, and in-flight
    channel messages into a single human-readable JSON document.

    Reads files written by `dsl run --snapshot-interval` (see
    docs/algorithms/CHECKPOINT_RESUME.md for the on-disk layout) via
    dissyslab.snapshot's existing reader helpers -- this command adds
    no new file format, it only merges what's already there.

    Same division of labor as `dsl explain-trace`: this command's job
    stops at producing the structured record. Turning it into an
    English explanation for Pat ("at this checkpoint, Alex had
    classified 4010 points as inside...") is Cowork's job,
    done by reading this command's output.
    """
    office_dir = _resolve_office_arg(args.office_dir, "office_dir")
    if office_dir is None:
        return 2

    from dissyslab.snapshot import (
        read_manifest,
        load_agent_state,
        load_channel_state,
        list_snapshots,
        latest_snapshot,
    )

    snapshot_dir = (
        Path(args.snapshot_dir) if getattr(args, "snapshot_dir", None)
        else office_dir / "snapshots"
    )

    if args.N == "latest":
        N = latest_snapshot(snapshot_dir)
        if N is None:
            _eprint(f"No checkpoints found under '{snapshot_dir / 'checkpoints'}'.")
            _eprint(
                "Run the office with `dsl run --snapshot-interval SECONDS` "
                "first to produce checkpoints."
            )
            return 2
    else:
        try:
            N = int(args.N)
        except ValueError:
            _eprint(f"Error: N must be an integer or 'latest', got {args.N!r}.")
            return 2

    try:
        manifest = read_manifest(snapshot_dir, N)
    except FileNotFoundError:
        available = list_snapshots(snapshot_dir)
        _eprint(f"Error: no checkpoint {N} found under '{snapshot_dir / 'checkpoints'}'.")
        if available:
            _eprint(f"Available checkpoint numbers: {available}")
        else:
            _eprint(
                "No checkpoints found at all. Run the office with "
                "`dsl run --snapshot-interval SECONDS` first."
            )
        return 2

    agents_out: dict = {}
    for agent_name in manifest.get("agents", []):
        state = load_agent_state(snapshot_dir, N, agent_name)
        agents_out[agent_name] = _json_safe(state)

    # In-flight messages, keyed by (destination agent, destination
    # port) -- see snapshot.py's module docstring for why that pair
    # uniquely identifies a channel. Each edge is
    # [from_block, from_port, to_block, to_port]; multiple edges can
    # share a destination (e.g. a fan-in), so dedupe on (to_block,
    # to_port) to avoid reading + printing the same channel file twice.
    channels_out: dict = {}
    seen: set = set()
    for edge in manifest.get("edges", []):
        if len(edge) != 4:
            continue
        _from_block, _from_port, to_block, to_port = edge
        key = (to_block, to_port)
        if key in seen:
            continue
        seen.add(key)
        msgs = load_channel_state(snapshot_dir, N, to_block, to_port)
        if msgs:
            channels_out[f"{to_block}::{to_port}"] = [_json_safe(m) for m in msgs]

    doc = {
        "office": manifest.get("office"),
        "N": manifest.get("N", N),
        "timestamp": manifest.get("timestamp"),
        "agents": agents_out,
        "in_flight_messages": channels_out,
    }

    out_text = json.dumps(doc, indent=2) + "\n"

    if getattr(args, "output", None):
        out_path = Path(args.output)
        out_path.write_text(out_text, encoding="utf-8")
        print(f"Wrote checkpoint {N} to {out_path}")
    else:
        sys.stdout.write(out_text)

    return 0


# ── Subcommand: list ──────────────────────────────────────────────────────────

#: `Pat` and `Builders` were the personas this project designs against.
#: They belong in its documents, not in its output: a student reading
#: `dsl list` has never met Pat, and a heading that names someone they
#: cannot ask about is the same defect as an unexplained `W11`.
_SECTION_HEADINGS = {
    "apps": "Apps — ready to run",
    "examples": "Examples — patterns to copy from",
    "": "Other",
}


def cmd_list(args: argparse.Namespace) -> int:
    """List the gallery offices that ship with the installed dissyslab.

    Output is grouped by gallery section (apps vs. examples) so Pat
    can immediately see which offices are intended as ready-to-run
    AI assistants and which are smaller demos for Builders. Within
    each section, offices are sorted alphabetically.
    """
    gallery = _packaged_gallery()
    if not gallery.is_dir():
        _eprint(
            "Could not find the gallery that ships with dissyslab.\n"
            "This is usually a packaging bug — please report it at\n"
            "https://github.com/kmchandy/DisSysLab/issues."
        )
        return 2

    sections = _walk_packaged_offices()
    all_offices = [p for offices in sections.values() for p in offices]
    if not all_offices:
        print("(no offices found — this dissyslab install may be incomplete)")
        return 0

    name_width = max(len(p.name) for p in all_offices)

    print("Offices shipped with dissyslab:")
    print()
    for sub in _GALLERY_SUBSECTIONS:
        group = sections.get(sub) or []
        if not group:
            continue
        print(f"  {_SECTION_HEADINGS[sub]}")
        for p in group:
            hint = _one_line_description(p)
            line1 = f"    {p.name:<{name_width}}"
            if _unfinished_reason(p):
                line1 += "  (unfinished)"
            if hint:
                line1 += f"  {hint}"
            print(line1.rstrip())
        print()

    print("To copy an office into your own folder:")
    print("  dsl init <office_name> <folder>")
    print()
    print("Or run a packaged office in place by name:")
    print("  dsl run <office_name>")
    return 0


# ── Subcommand: init ──────────────────────────────────────────────────────────

def _office_uses_llm_roles(office_dir: Path) -> bool:
    """Whether an office references any natural-language (LLM-backed) role.

    Natural-language roles come from ``.md`` role files (``nl_role``); ``.py``
    role files are deterministic and need no model backend. A role name
    resolves against the office's own ``roles/`` directory first, then the
    framework's built-in ``dissyslab/roles/`` library, so a local ``.py`` role
    shadowing a built-in ``.md`` counts as deterministic.

    Errs toward ``True`` (assume a key is needed) when the office cannot be
    parsed, so a genuine key requirement is never silently hidden.
    """
    try:
        from dissyslab.office.parser import parse_office_dir
        from dissyslab.office._internals import _builtin_roles_dir
        spec = parse_office_dir(Path(office_dir))
    except Exception:
        return True
    local = Path(office_dir) / "roles"
    builtin = _builtin_roles_dir()
    for ref in spec.agents:
        # A sub-office may hide LLM roles we cannot cheaply inspect here.
        if getattr(ref, "path", None):
            return True
        name = ref.role_name
        if (local / f"{name}.py").exists():
            continue  # deterministic local role
        if (local / f"{name}.md").exists():
            return True  # local natural-language role
        if (builtin / f"{name}.md").exists():
            return True  # built-in natural-language role
    return False


def cmd_init(args: argparse.Namespace) -> int:
    """Copy a gallery office into a new folder the user owns."""
    source = _find_packaged_office(args.office_name)

    if source is None:
        _eprint(f"Error: no office named '{args.office_name}' in the gallery.")
        _eprint("Run `dsl list` to see available offices.")
        return 2

    target = Path(args.target).resolve()
    if target.exists():
        _eprint(f"Error: target folder '{target}' already exists.")
        _eprint("Refusing to overwrite. Choose a different folder name.")
        return 2

    try:
        shutil.copytree(
            source,
            target,
            # Also drop our own working papers. `dsl init mac_speed_suite`
            # was putting PHASE1_DESIGN.md, PHASE2_BUILD_PLAN.md,
            # TESTER_FEEDBACK.md, a draft_workers/ folder and a PDF
            # report into a tester's directory -- notes we wrote to each
            # other, delivered as though they were part of his office.
            # The office is office.md, roles/, and the scripts that
            # operate it.
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "__init__.py",
                "*_DESIGN.md", "*_BUILD_PLAN.md", "*_FEEDBACK.md",
                "draft_*", "paper", "*.pdf",
            ),
        )
    except OSError as exc:
        _eprint(f"Error copying office: {exc}")
        return 1

    print(f"Copied '{args.office_name}' to {target}")
    unfinished = _unfinished_reason(target)
    if unfinished:
        # The last place to say it before they spend an afternoon on it.
        print()
        print("Note: this office is unfinished and is not expected to run:")
        print(f"  {unfinished}")
        print("It is here to read and to copy from.")
    print()
    print("Next steps:")
    print(f"  cd {target}")
    print("  dsl run .")
    if _office_uses_llm_roles(target) and not os.environ.get("ANTHROPIC_API_KEY"):
        print()
        print("Tip: this office needs ANTHROPIC_API_KEY to run.")
        print("     Put it in a .env file in your office folder, or export")
        print("     it in your shell. Get a key at https://console.anthropic.com/")
    return 0


# ── Subcommand: show ─────────────────────────────────────────────────────────


def _resolve_builtin_role_path(name: str) -> Path | None:
    """Locate <name>.md in the framework's built-in roles directory.

    Returns the absolute Path if found, None otherwise. Local roles
    (in an office's roles/ folder) are NOT considered here — Pat can
    open those directly in her own folder. ``dsl show`` is for
    components the framework ships.
    """
    try:
        from importlib.resources import files
        builtin_dir = Path(str(files("dissyslab") / "roles"))
    except Exception:
        return None
    candidate = builtin_dir / f"{name}.md"
    return candidate if candidate.is_file() else None


def _resolve_component_path(entry: dict) -> Path | None:
    """Resolve a COMPONENT_REGISTRY entry's import string to a file path.

    The entry's ``import`` field is a Python import statement like
    ``from dissyslab.components.sources.rss_normalizer import
    RSSNormalizer``. We parse out the module path and ask importlib
    where that module lives on disk. Returns the absolute Path or
    None if resolution fails (e.g. entries with no import field).
    """
    import_stmt = entry.get("import")
    if not import_stmt:
        return None
    import re
    m = re.match(r"^\s*from\s+([\w.]+)\s+import\s+", import_stmt)
    if not m:
        return None
    module_name = m.group(1)
    try:
        import importlib.util
        spec = importlib.util.find_spec(module_name)
        if spec is not None and spec.origin:
            return Path(spec.origin)
    except Exception:
        return None
    return None


def _resolve_python_object_path(obj) -> Path | None:
    """Find the source file of a Python callable or class via inspect."""
    import inspect
    try:
        return Path(inspect.getfile(obj))
    except (TypeError, OSError):
        return None


def cmd_show(args: argparse.Namespace) -> int:
    """Show the implementation of a built-in component or LLM role.

    Asymmetric output, calibrated to medium:

    * For an LLM role (``<name>.md`` in ``dissyslab/roles/``): print
      the file's full contents prefixed with a comment naming the
      file path. The prompt is short and reading it is what Pat
      wants.
    * For a Python implementation (in ``COMPONENT_REGISTRY``,
      ``FN_LIB``, or ``PARAMETERIZED_LIBRARY``): print only the
      absolute file path on a single line. The source is long;
      printing it would overwhelm the terminal. Pat opens the file
      in her editor if she wants to inspect.

    To modify a built-in role, Pat copies the printed content into
    a file in her office's ``roles/`` folder and edits there. The
    framework's name resolution prefers local files over built-ins.

    Resolution order (matches the compiler's own lookup):

    1. ``dissyslab/roles/<name>.md`` (built-in LLM prompt).
    2. ``COMPONENT_REGISTRY[name]`` (Python source/sink/agent class).
    3. ``PARAMETERIZED_LIBRARY[name]`` (parameterized factory like
       ``synchronizer``).
    4. ``dissyslab.fn_lib.FN_LIB[name]`` (Python function entry).
    """
    name = args.name

    # 1. Built-in LLM role (.md file).
    role_path = _resolve_builtin_role_path(name)
    if role_path is not None:
        print(f"# {role_path}")
        print()
        print(role_path.read_text(encoding="utf-8"), end="")
        return 0

    # 2. Python component in COMPONENT_REGISTRY.
    from dissyslab.office.utils import lookup_component
    entry = lookup_component(name)
    if entry is not None:
        py_path = _resolve_component_path(entry)
        if py_path is None:
            _eprint(
                f"Could not resolve file path for component {name!r}. "
                f"The registry entry has no usable import path."
            )
            return 1
        print(py_path)
        return 0

    # 3. PARAMETERIZED_LIBRARY (e.g. `synchronizer` -> synchronizer_role).
    try:
        from dissyslab.office.library import PARAMETERIZED_LIBRARY
        if name in PARAMETERIZED_LIBRARY:
            factory = PARAMETERIZED_LIBRARY[name]
            py_path = _resolve_python_object_path(factory)
            if py_path is not None:
                print(py_path)
                return 0
    except ImportError:
        pass

    # 4. fn_lib (Python function-library entries).
    try:
        from dissyslab.fn_lib import FN_LIB
        if name in FN_LIB:
            fn_entry = FN_LIB[name]
            # FnEntry typically wraps a fn; try common attribute names.
            fn = getattr(fn_entry, "fn", None) or fn_entry
            py_path = _resolve_python_object_path(fn)
            if py_path is not None:
                print(py_path)
                return 0
    except ImportError:
        pass

    # Not found in any surface.
    _eprint(
        f"Unknown component or role {name!r}. Looked in the role "
        f"library (dissyslab/roles/), the component registry, the "
        f"parameterized library, and the function library. None of "
        f"them have an entry named {name!r}."
    )
    return 1


# ── Subcommands: new / edit (chat with Claude) ────────────────────────────────

def cmd_new(args: argparse.Namespace) -> int:
    """Create a new office by chatting with Claude in plain English."""
    from . import cli_chat
    target = Path(args.target).resolve()
    return cli_chat.chat_create(target, model=args.model)


def cmd_edit(args: argparse.Namespace) -> int:
    """Modify an existing office by chatting with Claude in plain English."""
    from . import cli_chat
    office_dir = Path(args.office_dir).resolve()
    return cli_chat.chat_edit(office_dir, model=args.model)


# ── Subcommand: doctor ────────────────────────────────────────────────────────

# Common user mistakes: saving .env in TextEdit (becomes RTF), or pasting
# shell commands into the file instead of KEY=VALUE lines. Detecting these
# saves students a lot of confused troubleshooting.
_SHELL_COMMAND_PREFIXES = (
    "export ", "set ", "unset ", "echo ", "source ",
    "grep ", "setenv ", "cat ", "#!",
)


def _diagnose_env_file() -> tuple[str, str]:
    """
    Inspect ./.env and return (status, detail).

    status is one of:
        "absent"         — no .env file (may still be fine if env var is set)
        "unreadable"     — exists but cannot be read
        "rtf"            — saved as RTF (TextEdit default)
        "shell"          — contains shell commands, not KEY=VALUE lines
        "no_key"         — well-formed but missing ANTHROPIC_API_KEY
        "empty_value"    — ANTHROPIC_API_KEY= with empty value
        "wrong_prefix"   — ANTHROPIC_API_KEY value doesn't start with sk-ant-
        "ok"             — well-formed .env with an Anthropic-shaped key

    detail is a one-line human-readable summary for the OK/FAIL line.
    """
    env_path = Path(".env")
    if not env_path.exists():
        return ("absent", "no .env in current directory")

    try:
        raw = env_path.read_bytes()
    except OSError as exc:
        return ("unreadable", f"exists but cannot be read ({exc.__class__.__name__})")

    # RTF files start with {\rtf (TextEdit's default for "plain" text on macOS
    # if the file was ever saved via rich-text format).
    if raw.startswith(b"{\\rtf"):
        return ("rtf", "saved as RTF (probably via TextEdit)")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ("unreadable", "contains non-UTF-8 bytes")

    # Shell commands as contents — someone pasted their terminal history.
    shell_lines = [
        (i, stripped)
        for i, line in enumerate(text.splitlines(), 1)
        if (stripped := line.strip())
        and any(stripped.startswith(p) for p in _SHELL_COMMAND_PREFIXES)
    ]
    if shell_lines:
        first_line_num, first_line = shell_lines[0]
        preview = first_line[:50] + ("…" if len(first_line) > 50 else "")
        return ("shell", f"contains shell commands (line {first_line_num}: {preview})")

    # Look for ANTHROPIC_API_KEY= line.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ANTHROPIC_API_KEY"):
            if "=" not in stripped:
                return ("no_key", "malformed ANTHROPIC_API_KEY line (no '=')")
            _, _, value = stripped.partition("=")
            value = value.strip().strip('"').strip("'")
            if not value:
                return ("empty_value", "ANTHROPIC_API_KEY is set to empty string")
            if not value.startswith("sk-ant-"):
                return (
                    "wrong_prefix",
                    f"ANTHROPIC_API_KEY value starts with {value[:8]!r}, "
                    f"not 'sk-ant-'",
                )
            return ("ok", f"ANTHROPIC_API_KEY present (prefix {value[:7]}…, len {len(value)})")

    return ("no_key", "no ANTHROPIC_API_KEY line found")


def _env_file_advice(status: str) -> list[str]:
    """Human-readable fix suggestions for each bad .env status."""
    if status == "rtf":
        return [
            "Fix: TextEdit saves as RTF by default. Recreate as plain text:",
            "       rm .env",
            '       echo "ANTHROPIC_API_KEY=<paste-your-key>" > .env',
            "     Or open .env in VS Code / nano — not TextEdit.",
        ]
    if status == "shell":
        return [
            "Fix: .env should contain KEY=VALUE lines, not shell commands.",
            "     Recreate from scratch:",
            "       rm .env",
            '       echo "ANTHROPIC_API_KEY=<paste-your-key>" > .env',
        ]
    if status in ("no_key", "empty_value"):
        return [
            "Fix: add your Anthropic API key to .env:",
            '       echo "ANTHROPIC_API_KEY=<paste-your-key>" > .env',
            "     Get a key at https://console.anthropic.com/",
        ]
    if status == "wrong_prefix":
        return [
            "Fix: Anthropic keys start with 'sk-ant-'. Double-check you",
            "     copied the whole key from https://console.anthropic.com/",
        ]
    if status == "unreadable":
        return [
            "Fix: .env exists but can't be read. Check permissions, or",
            "     delete and recreate it:",
            "       rm .env",
            '       echo "ANTHROPIC_API_KEY=<paste-your-key>" > .env',
        ]
    if status == "absent":
        return [
            "Fix: no .env was found in the current directory. Either",
            "     create one here, or run `dsl doctor` from inside your",
            "     office folder. Quick create:",
            '       echo "ANTHROPIC_API_KEY=<paste-your-key>" > .env',
        ]
    return []


# Expected output of the built-in self-test office. Kept next to the
# helper so that changing one is obviously changing the other.
_SMOKE_EXPECTED = [2, 4, 6]


def _smoke_test_office() -> list:
    """Build and run a tiny three-agent office, in process.

    Source -> Transform -> Sink, with no network access, no
    credentials, and nothing written to disk. This is the cheapest
    end-to-end proof that the *installed package* actually works:
    importing the third-party dependencies says nothing about whether
    DisSysLab itself can build and run a network. A wheel missing its
    packaged role library, for example, imports perfectly well and
    fails here.

    Returns the list collected by the sink, for the caller to compare
    against _SMOKE_EXPECTED.
    """
    import contextlib
    import io as _io

    from dissyslab import network
    from dissyslab.blocks import Sink, Source, Transform

    results: list = []
    pending = [1, 2, 3]

    def emit():
        # A source function returns None to signal "no more data".
        return pending.pop(0) if pending else None

    src = Source(fn=emit, name="selftest_src")
    dbl = Transform(fn=lambda x: x * 2, name="selftest_double")
    out = Sink(fn=results.append, name="selftest_sink")

    # Offices are chatty on stdout; the doctor report should not be.
    with contextlib.redirect_stdout(_io.StringIO()):
        network([(src, dbl), (dbl, out)]).run_network()

    return results


def _doctor_verdict() -> tuple[str, list[str], object]:
    """One sentence saying whether you can build an office, and why not.

    Two things decide it, and nothing else does:

    * the library works -- a three-agent office builds and runs;
    * an assistant has the ``office-builder`` skill, without which it
      improvises its own concurrency and looks like it is working.

    A missing API key is not here on purpose. Offices whose roles are
    all plain Python need no credential, and those are the offices a
    new user runs first; calling that install "not ready" would be the
    false alarm that teaches people to skip the verdict.

    Returns ``(headline, detail_lines, smoke_result)``. The smoke
    result is handed back so the Self-test section below does not run
    the office a second time.
    """
    try:
        smoke_result = _smoke_test_office()
        smoke_ok = smoke_result == _SMOKE_EXPECTED
    except Exception as exc:  # noqa: BLE001
        smoke_result = exc
        smoke_ok = False

    try:
        from dissyslab.skills_installed import is_source_checkout, locate

        found, _roots, _deep = locate()
        have_skill = any(
            s.name == "office-builder" and not is_source_checkout(s.path)
            for s in found
        )
        # Found in a clone is a different fact from found nowhere, and
        # only the first is something doctor knows. Saying "not
        # installed" for the second claims knowledge of what exists on
        # a disk it has only partly read -- the wording mistake this
        # whole section was rewritten to stop making, still living on
        # in the verdict line.
        repo_copy_only = not have_skill and any(
            s.name == "office-builder" and is_source_checkout(s.path)
            for s in found
        )
    except Exception:  # noqa: BLE001 - doctor must always finish
        have_skill = False
        repo_copy_only = False

    if not smoke_ok:
        return (
            "Not ready: dissyslab itself is not working here.",
            ["The three-agent self-test did not produce what it should.",
             "See the Self-test section below; nothing else matters until"
             " that passes."],
            smoke_result,
        )
    if repo_copy_only:
        return (
            "Not ready: office-builder is only in the repository, not installed.",
            ["An assistant loads what was installed, not what is in a",
             "clone. dissyslab itself works. Ask your assistant to",
             "install the office-builder skill from the repository.",
             "See the Skills section below."],
            smoke_result,
        )
    if not have_skill:
        return (
            "Not ready: I could not find the office-builder skill.",
            ["dissyslab itself works. Without the skill an assistant will",
             "improvise its own concurrency instead of assembling tested",
             "parts -- and it will look as though it worked.",
             "The Skills section below lists everywhere I looked."],
            smoke_result,
        )
    return ("Ready. You can build an office.", [], smoke_result)


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check Python, key deps, .env file format, and ANTHROPIC_API_KEY."""
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        mark = "OK" if cond else "FAIL"
        ok = ok and cond
        print(f"  [{mark}] {label}" + (f": {detail}" if detail else ""))

    # The verdict, before the inventory.
    #
    # This used to end with "All required checks passed.", and the skill
    # section was one `[    ]` among nine ticks. An assistant summarising
    # the output for a twelve-year-old read that, classified the missing
    # skill as an optional gap, and told her everything was fine -- while
    # the paragraph explaining that without it an assistant improvises
    # its own concurrency sat four lines above.
    #
    # A report whose most important line can be reclassified has no most
    # important line. So the conclusion comes first, in one sentence
    # anything downstream can carry, and the detail follows for whoever
    # wants it.
    verdict, verdict_detail, smoke_result = _doctor_verdict()
    print(verdict)
    for line in verdict_detail:
        print(f"  {line}")
    print()

    # The inventory is captured rather than printed, because most of
    # the time nobody should see it.
    #
    # A first-time user who asked "did it work?" was told about nine
    # dependencies, two optional gaps and a three-agent self-test.
    # Every line true; none of it answerable by someone who does not
    # yet know what a sink is. Instructing an assistant to summarise
    # it does not work either -- it relayed the ticks, because they
    # were on its screen and looked like the answer.
    #
    # So when the verdict is Ready and nobody asked for detail, the
    # detail is not produced. When anything is wrong, or --full is
    # given, all of it prints exactly as before: quiet when healthy,
    # complete when not.
    _inventory = io.StringIO()
    with contextlib.redirect_stdout(_inventory):
        print(f"dissyslab version: {_package_version()}")
        print(f"Python:            {sys.version.split()[0]}  ({sys.executable})")
        print()
        print("Dependencies:")
        for mod in ("anthropic", "dotenv", "feedparser", "requests",
                    "websocket", "bs4", "PIL", "numpy", "scipy"):
            try:
                importlib.import_module(mod)
                check(mod, True)
            except Exception as exc:  # noqa: BLE001
                check(mod, False, f"not importable ({exc.__class__.__name__})")

        # The test suite lives in the [dev] extra, so a plain `pip install`
        # leaves pytest absent. That is correct packaging but surprising, so
        # answer the question here rather than making people find the docs.
        # Never a failure: running offices does not require pytest.
        # Market extras. Vikram met this as `No module named 'openpyxl'`
        # after following an instruction that said `pip install dissyslab`.
        # The extra is mentioned once, deep in the README, and the person
        # who needs it is the one least likely to be reading that far.
        print()
        print("Market data tools (optional, the [market] extra):")
        market_missing = []
        for mod, why in (("yfinance", "downloading your own price history"),
                         ("openpyxl", "writing a strategy's working as a spreadsheet")):
            try:
                importlib.import_module(mod)
                print(f"  [OK] {mod}")
            except ImportError:
                market_missing.append(mod)
                print(f"  [    ] {mod}: not installed — needed for {why}")
        if market_missing:
            print('         pip install "dissyslab[market]"')

        print()
        print("Test tools (optional):")
        try:
            importlib.import_module("pytest")
            print("  [SET ] pytest: available \u2014 run `pytest tests/` "
                  "from a source checkout")
        except ImportError:
            print("  [    ] pytest: not installed")
            print("         The test tools live in the [dev] extra. From a source")
            print("         checkout:  pip install -e \".[dev]\"")

        # Skills. Asked of the filesystem, not of the assistant.
        #
        # The setup script used to end by telling the user to ask their
        # assistant which version of the skill it had -- which asks the
        # possibly-unreliable thing whether it is reliable. An assistant
        # that never loaded the skill answers anyway, and answers
        # plausibly, and then improvises its own concurrency. Where a skill
        # lives is a filesystem question.
        print()
        from dissyslab.skills_installed import print_report as _skill_report
        _skill_report()

        print()
        print("Local .env:")
        env_status, env_detail = _diagnose_env_file()
        env_ok = env_status in ("ok", "absent")
        check(".env format", env_ok, env_detail)
        # "absent" is not a hard failure *if* the key is in the environment;
        # we detect that below with the ANTHROPIC_API_KEY check.
        env_advice = _env_file_advice(env_status) if env_status not in ("ok", "absent") else []

        print()
        print("Backend:")
        active = os.environ.get("DSL_BACKEND", "anthropic")
        bmod   = os.environ.get("DSL_BACKEND_MODULE")
        print(f"  active: {active}"
              + ("  (default)" if active == "anthropic" and not bmod else ""))
        if bmod:
            print(f"  DSL_BACKEND_MODULE: {bmod}")

        print()
        print("Credentials:")
        # Which credential matters depends on the backend selected above --
        # checking ANTHROPIC_API_KEY unconditionally reported a FAIL on
        # perfectly healthy Ollama and OpenRouter installs.
        #
        # A missing key is reported as information, never as a failure. An
        # office whose roles are all plain Python needs no credential at all,
        # and that includes the offices the README tells a new user to run
        # first, so failing here called a working install broken.
        required_key = {
            "anthropic":  "ANTHROPIC_API_KEY",
            "claude":     "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "ollama":     None,          # local model, no credential needed
        }.get(active, "ANTHROPIC_API_KEY")

        if required_key is None:
            print(f"  [    ] no credential needed for backend '{active}'")
        else:
            key = os.environ.get(required_key, "")
            if key:
                # Never print the key itself; a length + prefix is enough.
                print(f"  [SET ] {required_key}: set "
                      f"(prefix {key[:7]}…, len {len(key)})")
            else:
                print(f"  [    ] {required_key}: not set")
                print(f"         Needed only by offices with LLM roles on "
                      f"backend '{active}'.")
                print("         Key-free offices (periodic_brief, recovery_demo)")
                print("         run without it.")
                # Only nudge about .env when a key is actually wanted.
                if env_status == "absent":
                    env_advice = _env_file_advice("absent")

        # Print fix suggestions after the table, so the check list stays scannable.
        if env_advice:
            print()
            for line in env_advice:
                print(f"  {line}")

        # Optional integration credentials. These are not required for `dsl
        # run` to work in general — they're only needed by specific
        # sources/sinks (gmail_source, slack_sink, webhook_sink). We print
        # them so a student running `dsl doctor` can see at a glance which
        # integrations are wired up. Never a failure, just an "info" line.
        print()
        print("Optional integrations (only needed by specific sinks/sources):")
        optional_creds: list[tuple[str, str]] = [
            ("GMAIL_USER",          "gmail_source: email address to read from"),
            ("GMAIL_APP_PASSWORD",  "gmail_source / gmail_sink: 16-char app password"),
            ("SLACK_WEBHOOK_URL",   "slack_sink: Incoming Webhook URL"),
            ("WEBHOOK_URL",         "webhook_sink: outbound POST target"),
        ]
        for name, what in optional_creds:
            val = os.environ.get(name, "")
            if val:
                # For URL-shaped secrets, show only the host so we never
                # leak the secret token in the path.
                if val.startswith(("http://", "https://")):
                    from urllib.parse import urlparse
                    host = urlparse(val).hostname or "(unparseable)"
                    detail = f"set ({host})"
                else:
                    detail = f"set (len {len(val)})"
                print(f"  [SET ] {name}: {detail}")
            else:
                print(f"  [    ] {name}: not set — {what}")

        # Everything above checks the environment around DisSysLab. This
        # checks DisSysLab. It is a real failure if it does not pass.
        print()
        print("Self-test:")
        # Already run, at the top, to decide the verdict. Running it again
        # would double the cost of the one command people use when
        # something is already wrong.
        if isinstance(smoke_result, Exception):
            check(
                "build and run a 3-agent office",
                False,
                f"{smoke_result.__class__.__name__}: {smoke_result}",
            )
        else:
            passed = smoke_result == _SMOKE_EXPECTED
            check(
                "build and run a 3-agent office",
                passed,
                "source -> transform -> sink" if passed
                else f"produced {smoke_result!r}, expected {_SMOKE_EXPECTED!r}",
            )

    _show_all = getattr(args, "full", False) or not ok or not verdict.startswith("Ready")
    if _show_all:
        print(_inventory.getvalue(), end="")
    else:
        # The three facts anyone actually carries away, and the two an
        # assistant is told to report: what package, and what skill.
        print(f"dissyslab {_package_version()}   Python "
              f"{sys.version.split()[0]}")
        try:
            from dissyslab.skills_installed import (
                is_source_checkout,
                locate,
                stale_message,
            )

            found, _roots, _deep = locate()
            installed = [s for s in found if not is_source_checkout(s.path)]

            # Two copies of one skill is a finding, not a repetition:
            # an assistant loads one of them and which one is not the
            # user's to choose. The long form said so and the short
            # form printed the same name twice with no comment, which
            # reads as a display glitch rather than as the problem it is.
            copies: dict[str, int] = {}
            for s in installed:
                copies[s.name] = copies.get(s.name, 0) + 1

            for s in installed:
                # `or` and not a bare print: a skill whose SKILL.md has
                # no version line has ``version is None``, and printing
                # it raw put the word `None` in front of a beginner.
                print(f"{s.name} {s.version or 'no version string'}")
                # A skill that is not the one this release expects
                # survives the short form. It is the one thing here that
                # changes what the user should do next.
                for line in stale_message(s.name, s.version):
                    print(f"  {line}")

            for name, count in sorted(copies.items()):
                if count > 1:
                    print(f"  {count} copies of {name} are installed. An "
                          "assistant loads one of")
                    print("  them and which one is not yours to choose; "
                          "`dsl doctor --full`")
                    print("  gives the folder of each.")
        except Exception:  # noqa: BLE001 - doctor must always finish
            pass
        print()
        print("`dsl doctor --full` for the rest: dependencies, extras,")
        print("skills, .env, backend, credentials and the self-test.")

    if _show_all:
        print()
        if ok:
            # Repeat the verdict rather than reaching a second one. Two
            # conclusions in one report is how "Not ready" at the top
            # became "everything is fine" by the time it was summarised.
            # Only worth repeating when there is a report to get lost
            # in; in the short form the first line is still on screen.
            print(verdict)
            for line in verdict_detail:
                print(f"  {line}")
    if ok:
        return 0
    print("One or more required checks failed. See above.")
    return 1


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dsl",
        description=(
            "Build continuous offices of specialist agents in plain English."
        ),
        epilog=(
            "Common workflow:\n"
            "  dsl init my_first_office briefing    # copy a gallery office\n"
            "  cd briefing\n"
            "  dsl run .                            # run it; Ctrl-C to stop\n"
            "\n"
            "Build with Claude (plain English):\n"
            "  dsl new briefing                     # Claude writes a new office\n"
            "  dsl edit briefing                    # Claude rewrites in place\n"
            "\n"
            "Other commands:\n"
            "  list      Show every office that ships with dissyslab\n"
            "  doctor    Check your setup if something breaks\n"
            "\n"
            "Docs: https://github.com/kmchandy/DisSysLab"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"dissyslab {_package_version()}",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    p_list = sub.add_parser(
        "list",
        help="list offices that ship with dissyslab",
        description=(
            "List every office that ships with DisSysLab, with a one-line "
            "summary of each. Pair with `dsl init <name> <folder>` to copy "
            "one into a folder you own."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_list.set_defaults(handler=cmd_list)

    p_init = sub.add_parser(
        "init",
        help="copy a gallery office into a new folder",
        description=(
            "Copy a gallery office (see `dsl list`) into a new folder you "
            "own. Use it as a starting point — open the office.md and "
            "roles/*.md in your editor and customize."
        ),
        epilog=(
            "Example:\n"
            "  dsl init my_first_office briefing\n"
            "  cd briefing\n"
            "  dsl run ."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_init.add_argument(
        "office_name", help="name of the office (see `dsl list`)"
    )
    p_init.add_argument(
        "target", help="folder to create (must not exist)"
    )
    p_init.set_defaults(handler=cmd_init)

    p_show = sub.add_parser(
        "show",
        help="show the implementation of a built-in role or component",
        description=(
            "Print the implementation of a built-in role or component. "
            "For LLM-prompt roles (deduplicator, writer, …) prints the "
            "full prompt with its file path. For Python components "
            "(rss, intelligence_display, …) prints only the file path; "
            "open it in your editor to inspect."
        ),
        epilog=(
            "Examples:\n"
            "  dsl show deduplicator       # prints the LLM prompt\n"
            "  dsl show rss                # prints the .py file path\n"
            "\n"
            "To modify a built-in role for your own office: copy the "
            "output into <office>/roles/<name>.md and edit. The "
            "framework prefers local files over built-ins."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_show.add_argument(
        "name",
        help="name of the role or component (e.g. deduplicator, rss)",
    )
    p_show.set_defaults(handler=cmd_show)

    # `dsl new` — describe an office in plain English; Claude writes the files.
    # `dsl edit` — same, for an existing office. Both stream Claude's response
    # to the terminal and write office.md / roles/*.md automatically.
    p_new = sub.add_parser(
        "new",
        help="create a new office by chatting with Claude",
        description=(
            "Create a new office by chatting with Claude in plain English. "
            "Describe what you want — Claude may ask follow-up questions, "
            "then write the office.md and roles/*.md files for you. The "
            "target folder must not already exist."
        ),
        epilog=(
            "Examples:\n"
            "  dsl new briefing\n"
            "  dsl new sentiment_demo --model claude-opus-4-6\n"
            "\n"
            "Requires ANTHROPIC_API_KEY in your environment or a .env file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_new.add_argument(
        "target", help="folder to create (must not exist)"
    )
    p_new.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Claude model to use (default: claude-sonnet-4-6)",
    )
    p_new.set_defaults(handler=cmd_new)

    p_edit = sub.add_parser(
        "edit",
        help="modify an existing office by chatting with Claude",
        description=(
            "Modify an existing office by chatting with Claude in plain "
            "English. Claude sees the current office.md and roles/*.md, "
            "applies the change you describe, and rewrites the files in "
            "place."
        ),
        epilog=(
            "Examples:\n"
            "  dsl edit briefing\n"
            "  dsl edit . --model claude-opus-4-6\n"
            "\n"
            "Requires ANTHROPIC_API_KEY in your environment or a .env file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_edit.add_argument(
        "office_dir", help="path to an existing office directory"
    )
    p_edit.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Claude model to use (default: claude-sonnet-4-6)",
    )
    p_edit.set_defaults(handler=cmd_edit)

    p_run = sub.add_parser(
        "run",
        help="run a closed office",
        description=(
            "Run an office. The office_dir argument is the folder "
            "containing office.md and roles/*.md. Press Ctrl+C to stop."
        ),
        epilog=(
            "Examples:\n"
            "  dsl run .                  # run the office in the current folder\n"
            "  dsl run path/to/briefing   # run an office elsewhere"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_run.add_argument("office_dir", help="path to an office directory")
    p_run.add_argument(
        "--processes",
        action="store_true",
        help=(
            "Run each agent in its own OS process for true CPU "
            "parallelism (advanced; default is threads, which is "
            "correct for I/O-bound work). Equivalent to setting "
            "DSL_PROCESS_MODE=process. See examples/module_08 for "
            "when this matters."
        ),
    )
    # v1.6: checkpoint-resume opt-in flags.
    p_run.add_argument(
        "--snapshot-interval",
        type=float,
        metavar="SECONDS",
        help=(
            "Enable periodic distributed snapshots every SECONDS "
            "of execution. Snapshots are written under "
            "<office_dir>/snapshots/checkpoints/<N>/. Only "
            "checkpoint-aware sources (those that call _poll_os "
            "from their run loop) participate. See "
            "docs/algorithms/CHECKPOINT_RESUME.md."
        ),
    )
    p_run.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Suppress the per-agent message-count summary printed when "
            "the run finishes."
        ),
    )
    p_run.add_argument(
        "--resume",
        metavar="N|latest",
        help=(
            "Resume execution from snapshot N (an integer) or "
            "from the most recent snapshot ('latest'). Requires "
            "that the office's sources are checkpoint-aware."
        ),
    )
    # v1.7: opt-in per-agent activity-log trace, for the "explain a
    # debug trace to Pat" feature.
    p_run.add_argument(
        "--trace",
        action="store_true",
        help=(
            "Record every message each agent sends and receives to "
            "<office_dir>/trace/<agent_name>.jsonl, ordered by a "
            "physical-time-grounded logical clock. Off by default — "
            "logging has a real cost (a disk write per message). "
            "Stop the run manually (Ctrl-C or natural completion), "
            "then run `dsl explain-trace <office_dir>/trace/` to get "
            "one merged, ordered record. See "
            "docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md."
        ),
    )
    p_run.set_defaults(handler=cmd_run)

    # v1.7: merge a `--trace` run's per-agent JSONL files into one
    # ordered, structured record. This command only merges and sorts --
    # turning the record into English for Pat is Cowork's
    # job (see docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md Part 3).
    p_explain_trace = sub.add_parser(
        "explain-trace",
        help="merge a --trace run's per-agent logs into one ordered record",
        description=(
            "Merge every agent's trace/<agent_name>.jsonl file (written "
            "by `dsl run --trace`) into one sequence of actions, ordered "
            "by (logical timestamp, agent name). Emits JSONL -- this "
            "command does not produce an English explanation itself; "
            "that's done by reading its output."
        ),
        epilog=(
            "Examples:\n"
            "  dsl explain-trace path/to/office/trace\n"
            "  dsl explain-trace path/to/office/trace --output merged.jsonl"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_explain_trace.add_argument(
        "trace_dir", help="path to a trace/ directory produced by `dsl run --trace`"
    )
    p_explain_trace.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="write the merged JSONL record to FILE instead of stdout",
    )
    p_explain_trace.set_defaults(handler=cmd_explain_trace)

    # v1.7: merge one checkpoint's manifest + per-agent/channel state
    # into one human-readable JSON document. Mirrors explain-trace's
    # division of labor -- this command only merges what's already on
    # disk; the English explanation is Claude's job (see
    # docs/algorithms/CHECKPOINT_RESUME.md).
    p_show_checkpoint = sub.add_parser(
        "show-checkpoint",
        help="show one checkpoint's saved state as human-readable JSON",
        description=(
            "Merge one checkpoint's manifest.json, per-agent saved "
            "state, and any in-flight channel messages (written by "
            "`dsl run --snapshot-interval`) into a single JSON "
            "document. Emits JSON -- this command does not produce an "
            "English explanation itself; that's done by reading its "
            "output."
        ),
        epilog=(
            "Examples:\n"
            "  dsl show-checkpoint path/to/office latest\n"
            "  dsl show-checkpoint path/to/office 5 --output checkpoint5.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_show_checkpoint.add_argument(
        "office_dir", help="path to an office directory (or a packaged office name)"
    )
    p_show_checkpoint.add_argument(
        "N", help="checkpoint number, or 'latest' for the most recent"
    )
    p_show_checkpoint.add_argument(
        "--snapshot-dir",
        metavar="DIR",
        help="override the checkpoint directory (default: <office_dir>/snapshots)",
    )
    p_show_checkpoint.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="write the merged JSON to FILE instead of stdout",
    )
    p_show_checkpoint.set_defaults(handler=cmd_show_checkpoint)

    # `dsl build` emits the readable Python artifact at
    # <office_dir>/build/run.py. `dsl run` calls it automatically when
    # the artifact is missing or stale, but students often want to
    # inspect the generated file to see exactly what was wired up.
    p_build = sub.add_parser(
        "build",
        help="generate build/run.py for an office (without running)",
        description=(
            "Generate <office_dir>/build/run.py for an office without "
            "running it. The generated file is plain Python you can read "
            "and run directly with `python <office_dir>/build/run.py`. "
            "`dsl run` calls this automatically when the artifact is "
            "missing or stale."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_build.add_argument("office_dir", help="path to an office directory")
    p_build.set_defaults(handler=cmd_build)

    p_check = sub.add_parser(
        "check",
        help="check an office's wiring without running it",
        description=(
            "Read <office_dir>/office.md and report faults in the network "
            "as a whole: agents nothing can reach, work that reaches no "
            "sink, sinks nothing feeds, roles with no file behind them, and "
            "cycles. Reports every fault it finds, not just the first, and "
            "never runs the office.\n\n"
            "An office with an agent whose job is undecided -- 'Jay is "
            "unassigned.' -- is a draft. Its findings are then reported as "
            "remaining work rather than faults, and the exit status is 0: "
            "an unfinished office is not a broken one. A misspelled "
            "component name stays an error, because it is as wrong now as "
            "it will be later.\n\n"
            "This is a structural check. It cannot see faults that depend "
            "on what actually happens at run time -- a coordinator blocked "
            "on one inbox while another holds a message it will never read "
            "is a deadlock, not a wiring fault, and no static check reaches "
            "it."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_check.add_argument("office_dir", help="path to an office directory")
    p_check.set_defaults(handler=cmd_check)

    p_draw = sub.add_parser(
        "draw",
        help="show an office's network, edge by edge",
        description=(
            "Read <office_dir>/office.md and list the network: every "
            "connection with the outbox it leaves by and the inbox it "
            "arrives at, then a block naming every port that is "
            "connected to nothing.\n\n"
            "That second block is what an office.md cannot tell you. "
            "`Screen is a relevance_filter.` does not say that Screen "
            "has an outbox called `discard`, and an outbox wired to "
            "nothing stops the run the first time it is used.\n\n"
            "--mermaid prints a flowchart instead, fenced so GitHub and "
            "most editors render it.\n\n"
            "Ask for this when the wiring stops being readable as text, "
            "which happens at the first branch or fan-in. It draws an "
            "incomplete office too: a name used in Connections and "
            "declared nowhere gets its own node, marked, because an "
            "office you cannot run is when you most want to look at it.\n\n"
            "The picture shows structure and nothing else. Two offices "
            "that draw identically can behave completely differently, "
            "and a diagram with no fault in it can still deadlock."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_draw.add_argument("office_dir", help="path to an office directory")
    p_draw.add_argument(
        "--out", metavar="FILE",
        help="write to FILE instead of standard output",
    )
    p_draw.add_argument(
        "--mermaid", action="store_true",
        help=(
            "print a Mermaid flowchart instead of the listing, for "
            "pasting somewhere that renders it"
        ),
    )
    p_draw.add_argument(
        "--raw", action="store_true",
        help="with --mermaid, omit the ```mermaid fence",
    )
    p_draw.set_defaults(handler=cmd_draw)

    p_roles = sub.add_parser(
        "roles",
        help="list the built-in roles and what each one adds",
        description=(
            "Print every role that ships with dissyslab, with the field "
            "each one adds to a message.\n\n"
            "The emitted field is the part you need in order to wire "
            "the next agent: something downstream of a "
            "severity_classifier reads `severity`, and knowing only "
            "that the role 'decides how significant an item is' leaves "
            "you guessing.\n\n"
            "`dsl show <name>` prints a role in full. If none of them "
            "fit, describe what you want in a sentence and your "
            "assistant will write the role from your words."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_roles.set_defaults(handler=cmd_roles)

    p_grammar = sub.add_parser(
        "grammar",
        help="print the office reference: how office.md is written",
        description=(
            "Print the reference for the office language, which ships "
            "with the package.\n\n"
            "    dsl grammar            how office.md is written\n"
            "    dsl grammar roles      writing a role, English or Python\n"
            "    dsl grammar sources    the sources and sinks\n"
            "    dsl grammar examples   offices built end to end\n\n"
            "Read this before writing an office. It is here rather than "
            "in a skill so that the language and its description ship "
            "together and cannot disagree about what parses."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_grammar.add_argument(
        "topic", nargs="?",
        help="office (default), roles, sources, or examples",
    )
    p_grammar.set_defaults(handler=cmd_grammar)

    p_checks = sub.add_parser(
        "checks",
        help="say what a check code like W4 or G1 means",
        description=(
            "`dsl check` prints a code beside every finding. This says "
            "what one means.\n\n"
            "    dsl checks        every code, one line each\n"
            "    dsl checks W11    what that one means\n\n"
            "A *problem* means the office is wrong and will not run "
            "correctly. A *note* means read it and decide -- the office "
            "is not wrong, but it is doing something worth knowing "
            "about."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_checks.add_argument(
        "code",
        nargs="?",
        help="a code such as W4, W11 or G1. Omit it to list them all.",
    )
    p_checks.set_defaults(handler=cmd_checks)

    p_skills = sub.add_parser(
        "skills",
        help="list the skills DisSysLab ships and which are installed",
        description=(
            "Print every skill this project ships, whether it is "
            "installed, and the sentence that installs one that is "
            "not.\n\n"
            "A skill is a folder of instructions an assistant loads -- "
            "an open format, the same SKILL.md in Claude Code, Codex "
            "and Gemini CLI. Skills install from the repository rather "
            "than from the wheel, which is why this command names them "
            "rather than finding them all on disk.\n\n"
            "An assistant cannot tell you about a skill it has not "
            "loaded, and will answer anyway. Where a skill lives is a "
            "question about the filesystem, so this asks the "
            "filesystem."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_skills.add_argument(
        "--deep",
        action="store_true",
        help=(
            "search your whole home directory instead of the places "
            "assistants are known to use. Slower, and it needs to know "
            "nothing about anyone's layout -- which is why it keeps "
            "working when one of them moves."
        ),
    )
    p_skills.set_defaults(handler=cmd_skills)

    p_fetch = sub.add_parser(
        "fetch-prices",
        help="download your own daily price history",
        description=(
            "Download daily price history for the tickers you name, or "
            "for the basket an office asks for, into the one directory "
            "every office shares -- $DSL_MARKET_DATA, or "
            "~/.dissyslab/market_data.\n\n"
            "Nothing in this project ships market data. The vendor's "
            "terms do not permit redistributing it, so every user "
            "fetches their own; that is why this exists as a deliberate "
            "act and why yfinance is in the [market] extra rather than a "
            "core dependency.\n\n"
            "Files already present are left alone -- ten years of daily "
            "bars is a slow download, and a backtest that silently "
            "re-downloads is not reproducible. Pass --force to replace "
            "them.\n\n"
            "Examples:\n"
            "  dsl fetch-prices NVDA AMD --years 10\n"
            "  dsl fetch-prices --office my_backtest\n"
            "  dsl fetch-prices            (basket of the office you are in)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_fetch.add_argument("tickers", nargs="*",
                         help="ticker symbols; omit to use an office's basket")
    p_fetch.add_argument("--years", type=int, default=None,
                         help="how much history (default 10)")
    p_fetch.add_argument("--office", metavar="DIR",
                         help="take the basket from DIR/office.md")
    p_fetch.add_argument("--dest", metavar="DIR",
                         help="write here instead of the shared directory. "
                              "Note that an office still searches the shared "
                              "directory too, so a copy there can win")
    p_fetch.add_argument("--force", action="store_true",
                         help="re-download files that are already there")
    p_fetch.set_defaults(handler=cmd_fetch_prices)

    p_doc = sub.add_parser(
        "doctor",
        help="check your setup if something breaks",
        description=(
            "Check your Python version, your dependencies, which DisSysLab "
            "skills are installed and where, the credential your selected "
            "backend actually needs, and any optional integrations (Gmail, "
            "Slack, webhook URLs) you've configured. "
            "Finishes by building and running a small office as a "
            "self-test, so you get a straight answer about whether the "
            "install works. Run this first when something breaks.\n\n"
            "When everything is in order it prints the verdict and little "
            "else; the inventory appears whenever something is wrong, or "
            "on request with --full."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_doc.add_argument(
        "--full",
        action="store_true",
        help=(
            "print the whole inventory even when the install is healthy: "
            "dependencies, market and test extras, skills, .env, backend, "
            "credentials and the self-test."
        ),
    )
    p_doc.set_defaults(handler=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Load .env from the current working directory (or any ancestor) so that
    # students who follow the micro-course and put ANTHROPIC_API_KEY into a
    # .env file in their office folder actually get it picked up by `dsl run`.
    # This has to happen before any subcommand runs, because ai_agent.py and
    # friends read os.environ directly at call time. If no .env is found,
    # load_dotenv() is a no-op.
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Optional backend registration hook. Set DSL_BACKEND_MODULE to an
    # import path (e.g. "my_backends" or "my_app.backends") and we
    # import it before any subcommand runs. The module's import-time
    # side effect can call `register_backend()` to make a custom LLM
    # available, after which `DSL_BACKEND=my-name dsl run ...` works
    # without forking dissyslab. See docs/LANGUAGE_MODELS.md.
    backend_module = os.environ.get("DSL_BACKEND_MODULE")
    if backend_module:
        try:
            importlib.import_module(backend_module)
        except Exception as exc:  # noqa: BLE001
            _eprint(
                f"Warning: DSL_BACKEND_MODULE={backend_module!r} failed to "
                f"import ({exc.__class__.__name__}: {exc}).\n"
                f"  Continuing with the default backend. See "
                f"docs/LANGUAGE_MODELS.md for the registration pattern."
            )

    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
