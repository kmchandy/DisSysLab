"""Copy lab3_runs/ to lab3_runs_public/ with nothing personal in it.

Replaces your home folder, your user name and anything shaped like an API
key in every file, then lists what it replaced so you can check. Only
lab3_runs_public/ should ever be published or sent.

    python scrub.py
"""

from __future__ import annotations

import getpass
import re
import shutil
from pathlib import Path

import common

OUT = common.REPO / "lab3_runs_public"
KEY = re.compile(r"sk-[A-Za-z0-9_\-]{12,}")


def scrub_text(text: str, home: str, user: str) -> tuple[str, int]:
    n = text.count(home) + len(KEY.findall(text))
    text = KEY.sub("sk-REDACTED", text.replace(home, "~"))
    if user and len(user) > 2:
        n += len(re.findall(rf"\b{re.escape(user)}\b", text))
        text = re.sub(rf"\b{re.escape(user)}\b", "user", text)
    return text, n


def main() -> None:
    home, user = str(Path.home()), getpass.getuser()
    if OUT.exists():
        shutil.rmtree(OUT)
    total = 0
    for src in common.RUNS.rglob("*"):
        if not src.is_file():
            continue
        dst = OUT / src.relative_to(common.RUNS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            text, n = scrub_text(src.read_text(encoding="utf-8"), home, user)
        except UnicodeDecodeError:
            continue  # not text: not copied
        dst.write_text(text, encoding="utf-8")
        if n:
            print(f"  {dst.relative_to(OUT)}: {n} replaced")
        total += n
    print(f"Wrote {OUT}: {total} replacements.")


if __name__ == "__main__":
    main()
