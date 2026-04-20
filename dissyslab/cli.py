# dissyslab/cli.py
"""
`dsl` — command-line entry point for DisSysLab.

After `pip install dissyslab`, users get a `dsl` command with
subcommands aimed at first-year undergraduates:

    dsl list                      list offices that ship with dissyslab
    dsl init <office> <folder>    copy a gallery office into <folder>
    dsl run <office_dir>          run a closed office end-to-end
    dsl build <office_dir>        generate app.py for an open office
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


def _one_line_description(office_dir: Path) -> str:
    """Find a short one-line description for an office, or '' if none.

    Prefer README.md over office.md: README.md is meant to be human-facing,
    while office.md starts with the `Sources:` block that the compiler reads.
    """
    for candidate in ("README.md", "office.md"):
        f = office_dir / candidate
        if not f.is_file():
            continue
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s and not s.startswith("#"):
                    return s[:80]
        except OSError:
            continue
    return ""


# ── Subcommand: run ───────────────────────────────────────────────────────────

def cmd_run(args: argparse.Namespace) -> int:
    """Validate and run a closed office in-process via office_compiler."""
    office_dir = _require_dir("office_dir", args.office_dir)

    # Delegate to the existing office_compiler module, preserving its
    # argv contract (argv[1] is the office directory).
    sys.argv = ["dsl run", str(office_dir)]
    try:
        runpy.run_module(
            "dissyslab.office.office_compiler",
            run_name="__main__",
        )
    except SystemExit as e:
        # office_compiler uses sys.exit for clean user-facing errors.
        return int(e.code or 0)
    except Exception as exc:  # noqa: BLE001
        _eprint(f"dsl run failed: {exc}")
        return 1
    return 0


# ── Subcommand: build ─────────────────────────────────────────────────────────

def cmd_build(args: argparse.Namespace) -> int:
    """Generate app.py for an (open or closed) office using make_office."""
    office_dir = _require_dir("office_dir", args.office_dir)

    sys.argv = ["dsl build", str(office_dir)]
    try:
        runpy.run_module(
            "dissyslab.office.make_office",
            run_name="__main__",
        )
    except SystemExit as e:
        return int(e.code or 0)
    except Exception as exc:  # noqa: BLE001
        _eprint(f"dsl build failed: {exc}")
        return 1
    return 0


# ── Subcommand: list ──────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    """List the gallery offices that ship with the installed dissyslab."""
    gallery = _packaged_gallery()
    if not gallery.is_dir():
        _eprint(
            "Could not find the gallery that ships with dissyslab.\n"
            "This is usually a packaging bug — please report it at\n"
            "https://github.com/kmchandy/DisSysLab/issues."
        )
        return 2

    offices = sorted(
        p for p in gallery.iterdir()
        if p.is_dir()
        and not p.name.startswith(".")
        and not p.name.startswith("__")  # skip __pycache__
    )
    if not offices:
        print("(no offices found — this dissyslab install may be incomplete)")
        return 0

    print("Offices shipped with dissyslab:")
    print()
    name_width = max(len(p.name) for p in offices)
    for p in offices:
        hint = _one_line_description(p)
        hint_part = f"  {hint}" if hint else ""
        print(f"  {p.name:<{name_width}}{hint_part}")
    print()
    print("To copy an office into your own folder:")
    print("  dsl init <office_name> <folder>")
    return 0


# ── Subcommand: init ──────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    """Copy a gallery office into a new folder the user owns."""
    gallery = _packaged_gallery()
    source = gallery / args.office_name

    if not source.is_dir():
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


# ── Subcommand: doctor ────────────────────────────────────────────────────────

def cmd_doctor(args: argparse.Namespace) -> int:
    """Check Python, key deps, and whether ANTHROPIC_API_KEY is set."""
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
    print("Credentials:")
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        # Never print the key itself; a length + prefix is enough.
        check("ANTHROPIC_API_KEY", True, f"set (prefix {key[:7]}…, len {len(key)})")
    else:
        check(
            "ANTHROPIC_API_KEY",
            False,
            "not set (put it in .env or export it in your shell)",
        )

    print()
    if ok:
        print("All checks passed.")
        return 0
    print("One or more checks failed. See above.")
    return 1


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dsl",
        description=(
            "DisSysLab — build continuous offices of AI agents in plain English.\n"
            "See https://github.com/kmchandy/DisSysLab for docs."
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
        "list", help="list offices that ship with dissyslab"
    )
    p_list.set_defaults(handler=cmd_list)

    p_init = sub.add_parser(
        "init", help="copy a gallery office into a new folder"
    )
    p_init.add_argument(
        "office_name", help="name of the office (see `dsl list`)"
    )
    p_init.add_argument(
        "target", help="folder to create (must not exist)"
    )
    p_init.set_defaults(handler=cmd_init)

    p_run = sub.add_parser("run", help="run a closed office")
    p_run.add_argument("office_dir", help="path to an office directory")
    p_run.set_defaults(handler=cmd_run)

    p_build = sub.add_parser("build", help="generate app.py for an office")
    p_build.add_argument("office_dir", help="path to an office directory")
    p_build.set_defaults(handler=cmd_build)

    p_doc = sub.add_parser(
        "doctor",
        help="check Python, dependencies, and API key",
    )
    p_doc.set_defaults(handler=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
