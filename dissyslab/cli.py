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
    dsl doctor                    sanity-check Python, deps, and API key
    dsl --version                 print the installed dissyslab version

This module is intentionally small: it dispatches to the real
implementation elsewhere in the package. New subcommands should be
added as small handler functions below; keep the top-level
argument parsing boring and readable.
"""

from __future__ import annotations

import argparse
import importlib
import os
import runpy
import shutil
import sys
import traceback
from pathlib import Path
from typing import Callable


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
    try:
        from importlib.metadata import version
        return version("dissyslab")
    except Exception:
        # Running from a source checkout without an installed dist.
        return "unknown (source)"


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


def _one_line_description(office_dir: Path) -> str:
    """Find a short one-line description for an office, or '' if none.

    Returns the first non-blank, non-heading line of README.md (or
    office.md as a fallback) that is not the `**Tags:**` line.
    """
    for candidate in ("README.md", "office.md"):
        f = office_dir / candidate
        if not f.is_file():
            continue
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    continue
                if s.startswith("**Tags:**"):
                    continue
                # Strip simple markdown bold markers so the terminal
                # output reads naturally — e.g. `**Foo.**` → `Foo.`.
                cleaned = s.replace("**", "")
                return cleaned[:80]
        except OSError:
            continue
    return ""


def _read_tags(office_dir: Path) -> list[str]:
    """Read the `**Tags:**` line from an office's README.md.

    Convention (see dev/PATH_A_FRICTION_SEQUENCE.md, item #34): every
    gallery office has a single line of the form

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


def cmd_run(args: argparse.Namespace) -> int:
    """Build (if stale) and run a closed office via office."""
    office_dir = _resolve_office_arg(args.office_dir, "office_dir")
    if office_dir is None:
        return 2

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

    from dissyslab.office.cli_helpers import cli_build

    try:
        return cli_build(office_dir)
    except SystemExit as e:
        return int(e.code or 0)
    except Exception as exc:  # noqa: BLE001
        _eprint(_explain_failure("dsl build", exc))
        return 1


# ── Subcommand: list ──────────────────────────────────────────────────────────

_SECTION_HEADINGS = {
    "apps": "Apps (for Pat — ready to run as a daily assistant)",
    "examples": "Examples (for Builders — patterns to crib)",
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
            if hint:
                line1 += f"  {hint}"
            print(line1)
        print()

    print("To copy an office into your own folder:")
    print("  dsl init <office_name> <folder>")
    print()
    print("Or run a packaged office in place by name:")
    print("  dsl run <office_name>")
    return 0


# ── Subcommand: init ──────────────────────────────────────────────────────────

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
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "__init__.py"
            ),
        )
    except OSError as exc:
        _eprint(f"Error copying office: {exc}")
        return 1

    print(f"Copied '{args.office_name}' to {target}")
    print()
    print("Next steps:")
    print(f"  cd {target}")
    print("  dsl run .")
    if not os.environ.get("ANTHROPIC_API_KEY"):
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


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check Python, key deps, .env file format, and ANTHROPIC_API_KEY."""
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        mark = "OK" if cond else "FAIL"
        ok = ok and cond
        print(f"  [{mark}] {label}" + (f": {detail}" if detail else ""))

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
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        # Never print the key itself; a length + prefix is enough.
        check("ANTHROPIC_API_KEY", True, f"set (prefix {key[:7]}…, len {len(key)})")
    else:
        check(
            "ANTHROPIC_API_KEY",
            False,
            "not set in environment (put it in .env or export in your shell)",
        )
        # If there's no key in the env AND no usable .env, nudge the student.
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

    print()
    if ok:
        print("All required checks passed.")
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
        "--resume",
        metavar="N|latest",
        help=(
            "Resume execution from snapshot N (an integer) or "
            "from the most recent snapshot ('latest'). Requires "
            "that the office's sources are checkpoint-aware."
        ),
    )
    p_run.set_defaults(handler=cmd_run)

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

    p_doc = sub.add_parser(
        "doctor",
        help="check your setup if something breaks",
        description=(
            "Check your Python version, your dependencies, your Anthropic "
            "API key, and any optional integrations (Gmail, Slack, webhook "
            "URLs) you've configured. Run this first when something breaks."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
