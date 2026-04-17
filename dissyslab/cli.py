# dissyslab/cli.py
"""
`dsl` — command-line entry point for DisSysLab.

After `pipx install dissyslab`, users get a `dsl` command with
subcommands aimed at first-year undergraduates:

    dsl run <office_dir>       run a closed office end-to-end
    dsl build <office_dir>     generate app.py for an open office
    dsl gallery                list the offices shipped with the repo
    dsl doctor                 sanity-check Python, deps, and API key
    dsl --version              print the installed dissyslab version

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


# ── Subcommand: gallery ───────────────────────────────────────────────────────

def cmd_gallery(args: argparse.Namespace) -> int:
    """List offices in the gallery/ directory of the current working dir."""
    root = Path(args.root).resolve() if args.root else Path.cwd()
    gallery_dir = root / "gallery"
    if not gallery_dir.is_dir():
        _eprint(
            f"No 'gallery/' directory found under {root}.\n"
            "Tip: run `dsl gallery` from the root of a DisSysLab checkout, "
            "or pass --root <path>."
        )
        return 2

    offices = sorted(
        p for p in gallery_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )
    if not offices:
        print(f"(no offices found under {gallery_dir})")
        return 0

    print(f"Offices in {gallery_dir}:")
    for p in offices:
        # Prefer a one-line description from office.md if present.
        hint = ""
        for candidate in ("office.md", "README.md"):
            f = p / candidate
            if f.is_file():
                try:
                    first = next(
                        (line.strip() for line in f.read_text(encoding="utf-8").splitlines()
                         if line.strip() and not line.strip().startswith("#")),
                        "",
                    )
                    if first:
                        hint = f" — {first[:80]}"
                        break
                except OSError:
                    pass
        print(f"  {p.name}{hint}")
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

    p_run = sub.add_parser("run", help="run a closed office")
    p_run.add_argument("office_dir", help="path to an office directory")
    p_run.set_defaults(handler=cmd_run)

    p_build = sub.add_parser("build", help="generate app.py for an office")
    p_build.add_argument("office_dir", help="path to an office directory")
    p_build.set_defaults(handler=cmd_build)

    p_gal = sub.add_parser("gallery", help="list offices under ./gallery")
    p_gal.add_argument(
        "--root",
        default=None,
        help="repo root containing a gallery/ directory (default: cwd)",
    )
    p_gal.set_defaults(handler=cmd_gallery)

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
